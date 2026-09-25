"""Run the whole pilot unattended, end to end (host-side, stdlib only).

    python scripts/run_pilot.py                 # everything except the timing pass
    python scripts/run_pilot.py --timing        # also (re)measure runtime (M10; slow)
    python scripts/run_pilot.py --from score    # resume from a stage

Stages: fonts -> render -> variants -> downscaled_gt -> invalidate -> ocr -> serial_check
-> rerun -> [timing] -> lock -> environment -> tests -> pseudo -> score -> validate.

There is no human step anywhere (AUTOMATED_VALIDATION.md). Stale OCR outputs are
removed automatically: any prediction whose recorded input pixel hash differs from
the current manifest is deleted before OCR runs, so re-rendering can never leave
outdated predictions in the scores. OCR stages are resumable. Exit code 1 if the
tests or any validation check fail.
"""

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.join(ROOT, "pilot")
ENGINES = ["tesseract5", "windows_ocr", "doctr", "paddle_v5_mobile", "easyocr", "paddle_v5_server"]
STAGES = ["fonts", "render", "variants", "downscaled_gt", "invalidate", "ocr", "serial_check", "rerun", "timing",
          "lock", "environment", "tests", "pseudo", "score", "validate"]
TOOLS = ["docker", "run", "--rm", "--ipc=host", "-v", f"{ROOT}:/bench", "-w", "/bench", "ocrbench-tools:pilot"]


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}"
    print(line, flush=True)
    os.makedirs(os.path.join(PILOT, "logs"), exist_ok=True)
    with open(os.path.join(PILOT, "logs", "run_pilot.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(cmd: list[str], stage: str) -> None:
    log(f"stage {stage}: {' '.join(cmd[-4:])}")
    t0 = time.time()
    code = subprocess.call(cmd, cwd=ROOT)
    log(f"stage {stage}: exit {code} after {time.time() - t0:.0f} s")
    if code != 0:
        raise SystemExit(f"stage {stage} failed (exit {code})")


def tools(*args: str) -> list[str]:
    return TOOLS + ["python", *args]


def invalidate_stale() -> None:
    with open(os.path.join(PILOT, "dataset", "manifest.jsonl"), encoding="utf-8") as f:
        pixel = {r["image_id"]: r["pixel_sha256"] for r in map(json.loads, f)}
    removed = 0
    for tree in ("predictions", "predictions_rerun"):
        root = os.path.join(PILOT, tree)
        if not os.path.isdir(root):
            continue
        for engine in os.listdir(root):
            d = os.path.join(root, engine)
            for name in os.listdir(d):
                path = os.path.join(d, name)
                with open(path, encoding="utf-8") as f:
                    p = json.load(f)
                recorded = p.get("input_pixel_sha256")
                # A prediction is valid only for the exact pixels it was made on. Failed calls
                # carry no hash and are re-run too, so they can't hide a stale input.
                if p["image_id"] not in pixel or recorded != pixel[p["image_id"]]:
                    os.remove(path)
                    removed += 1
    log(f"stage invalidate: removed {removed} stale or unverifiable predictions")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start", choices=STAGES, default=STAGES[0])
    parser.add_argument("--timing", action="store_true", help="run the (slow) timing pass")
    args = parser.parse_args()
    todo = STAGES[STAGES.index(args.start):]
    log(f"run_pilot start: stages {todo}")
    py = sys.executable
    for stage in todo:
        if stage == "fonts":
            run([py, "scripts/fetch_fonts.py", "--verify"], stage)
        elif stage == "render":
            run(tools("scripts/render_chromium.py"), stage)
        elif stage == "variants":
            run(tools("scripts/derive_variants.py"), stage)
        elif stage == "downscaled_gt":
            run(tools("scripts/downscaled_gt.py"), stage)
        elif stage == "invalidate":
            invalidate_stale()
        elif stage == "ocr":
            for e in ENGINES:  # one engine at a time: parallel engines oversubscribe the CPU
                run([py, "scripts/run_ocr.py", "accuracy", "--engines", e], f"ocr:{e}")
        elif stage == "serial_check":
            run([py, "scripts/run_ocr.py", "serial-check"], stage)
        elif stage == "rerun":
            for e in ENGINES:
                run([py, "scripts/run_ocr.py", "rerun", "--engines", e], f"rerun:{e}")
        elif stage == "timing":
            if args.timing:
                run([py, "scripts/run_ocr.py", "timing"], stage)
            else:
                log("stage timing: skipped (pass --timing to re-measure runtime)")
        elif stage == "lock":
            run([py, "scripts/run_ocr.py", "lock"], stage)
        elif stage == "environment":
            run([py, "scripts/run_ocr.py", "environment"], stage)
        elif stage == "tests":
            run(tools("scripts/run_tests.py"), stage)
        elif stage == "pseudo":
            run(tools("scripts/pseudo_engines.py"), stage)
        elif stage == "score":
            run(tools("scripts/score.py"), stage)
        elif stage == "validate":
            run(tools("scripts/validate_pilot.py"), stage)
    log("run_pilot finished: all stages passed")


if __name__ == "__main__":
    main()
