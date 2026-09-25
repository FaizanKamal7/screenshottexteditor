"""Engine worker: one engine per process, JSON-lines protocol over stdin/stdout.

Requests (one JSON object per line):
    {"cmd": "info"}
    {"cmd": "run", "path": "<image path>"}
    {"cmd": "quit"}
Every response is one JSON line. Library logging is redirected to stderr so it
can never corrupt the protocol stream (PaddleOCR prints to stdout).

The worker decodes the file with Pillow (RGB) before timing, and reports the
SHA-256 of both the file bytes and the decoded pixels so the orchestrator can
confirm every environment saw identical input (PILOT_PLAN E5/E6).
"""

import argparse
import hashlib
import json
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROTO = os.fdopen(os.dup(1), "w", encoding="utf-8")
os.dup2(2, 1)
sys.stdout = sys.stderr


def make_engine(engine_id: str):
    if engine_id in ("paddle_v5_mobile", "paddle_v5_server"):
        from paddle_engine import PaddleEngine

        return PaddleEngine(engine_id)
    if engine_id == "easyocr":
        from torch_engines import EasyOcrEngine

        return EasyOcrEngine()
    if engine_id == "doctr":
        from torch_engines import DoctrEngine

        return DoctrEngine()
    if engine_id == "tesseract5":
        from tesseract_engine import TesseractEngine

        return TesseractEngine()
    if engine_id == "windows_ocr":
        from windows_engine import WindowsOcrEngine

        return WindowsOcrEngine()
    raise SystemExit(f"unknown engine {engine_id}")


def decode(path: str):
    import numpy as np
    from PIL import Image

    with open(path, "rb") as f:
        raw = f.read()
    from io import BytesIO

    with Image.open(BytesIO(raw)) as im:
        rgb = np.ascontiguousarray(np.asarray(im.convert("RGB")))
    pixel_hash = hashlib.sha256(repr(rgb.shape).encode() + rgb.tobytes()).hexdigest()
    return rgb, hashlib.sha256(raw).hexdigest(), pixel_hash


def reset_peak_memory() -> bool:
    """Linux: reset this process's resident-set high-water mark (VmHWM) so the next
    reading is a per-image peak. Returns False where that isn't possible."""
    try:
        with open("/proc/self/clear_refs", "w") as f:
            f.write("5")
        return True
    except OSError:
        return False


def peak_memory_mb(per_image: bool) -> tuple[float | None, str]:
    """(peak resident memory in MB, scope). Linux: VmHWM (per-image if reset worked).
    Windows: PeakWorkingSetSize, which is the process-lifetime peak."""
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmHWM:"):
                    return int(line.split()[1]) / 1024.0, "per-image" if per_image else "process-lifetime"
    except OSError:
        pass
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
            return pmc.PeakWorkingSetSize / (1024.0 * 1024.0), "process-lifetime"
    return None, "unavailable"


def send(obj: dict) -> None:
    PROTO.write(json.dumps(obj, ensure_ascii=False) + "\n")
    PROTO.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    args = parser.parse_args()

    engine = make_engine(args.engine)
    try:
        init_s = engine.construct()
        send({"ok": True, "ready": True, "init_s": init_s})
    except Exception as exc:  # construction failure is reported, not hidden
        send({"ok": False, "ready": False, "error": repr(exc), "traceback": traceback.format_exc()})
        return

    for raw_line in sys.stdin:
        raw_line = raw_line.strip().lstrip("﻿")
        if not raw_line:
            continue
        req = json.loads(raw_line)
        cmd = req.get("cmd")
        if cmd == "quit":
            send({"ok": True, "bye": True})
            return
        if cmd == "info":
            try:
                send({"ok": True, "info": engine.info()})
            except Exception as exc:
                send({"ok": False, "error": repr(exc), "traceback": traceback.format_exc()})
            continue
        if cmd == "run":
            try:
                rgb, file_sha, pixel_sha = decode(req["path"])
                per_image = reset_peak_memory()
                wall0 = time.perf_counter()
                result = engine.run(rgb)
                wall_s = time.perf_counter() - wall0
                peak_mb, peak_scope = peak_memory_mb(per_image)
                send(
                    {
                        "ok": True,
                        "file_sha256": file_sha,
                        "pixel_sha256": pixel_sha,
                        "total_s": result.total_s,
                        "detect_s": result.detect_s,
                        "recognize_s": result.recognize_s,
                        "adapter_wall_s": wall_s,
                        "peak_rss_mb": round(peak_mb, 1) if peak_mb is not None else None,
                        "peak_rss_scope": peak_scope,
                        "lines": [
                            {"bbox": list(ln.bbox), "text": ln.text, "confidence": ln.confidence}
                            for ln in result.lines
                        ],
                    }
                )
            except Exception as exc:
                send({"ok": False, "error": repr(exc), "traceback": traceback.format_exc()})
            continue
        send({"ok": False, "error": f"unknown cmd {cmd!r}"})


if __name__ == "__main__":
    main()
