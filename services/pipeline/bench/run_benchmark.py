"""OCR engine bake-off: Paddle vs RapidOCR(ONNXRuntime) vs RapidOCR(OpenVINO) vs Tesseract 5.

Speed: interleaved warm reps across all (fixture, engine) pairs, so no
engine's numbers are biased by session-level drift (CPU frequency scaling,
container warmup) concentrated in one time window.

Accuracy: every alternative engine's per-line output is greedily IoU-matched
against Paddle's own output on the same fixture (Paddle is the reference,
per spec) — matched pairs get a text/CER/IoU comparison, unmatched Paddle
lines are "missed", unmatched alternative lines are "extra".

Run inside the bench container (needs paddleocr/rapidocr/pytesseract):
    python run_benchmark.py [--reps 5] [--fixtures-dir /fixtures] [--out /bench/results.json]
"""

import argparse
import glob
import json
import os
import statistics
import time

import numpy as np
from rapidfuzz.distance import Levenshtein
from PIL import Image

from engines import BenchLine, make_engines


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, aw, ah = a
    ax1, ay1 = ax0 + aw, ay0 + ah
    bx0, by0, bw, bh = b
    bx1, by1 = bx0 + bw, by0 + bh

    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0.0, ix1 - ix0), max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _match_lines(reference: list[BenchLine], candidate: list[BenchLine], iou_threshold: float = 0.3) -> dict:
    """Greedy best-IoU matching, reference (Paddle) vs candidate (alt engine)."""
    pairs = []
    for ri, r in enumerate(reference):
        for ci, c in enumerate(candidate):
            iou = _iou(r.bbox, c.bbox)
            if iou >= iou_threshold:
                pairs.append((iou, ri, ci))
    pairs.sort(reverse=True)

    matched_ref: set[int] = set()
    matched_cand: set[int] = set()
    matches = []
    for iou, ri, ci in pairs:
        if ri in matched_ref or ci in matched_cand:
            continue
        matched_ref.add(ri)
        matched_cand.add(ci)
        matches.append((ri, ci, iou))

    missed = [ri for ri in range(len(reference)) if ri not in matched_ref]
    extra = [ci for ci in range(len(candidate)) if ci not in matched_cand]
    return {"matches": matches, "missed": missed, "extra": extra}


def _cer(ref: str, hyp: str) -> float:
    if not ref:
        return 0.0 if not hyp else 1.0
    return Levenshtein.distance(ref, hyp) / len(ref)


def load_fixtures(fixtures_dir: str) -> list[str]:
    patterns = ("*.png", "*.jpg", "*.jpeg")
    paths = [p for pattern in patterns for p in glob.glob(os.path.join(fixtures_dir, pattern))]
    return sorted(paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--fixtures-dir", default="/fixtures")
    parser.add_argument("--out", default="/bench/results.json")
    args = parser.parse_args()

    fixture_paths = load_fixtures(args.fixtures_dir)
    if not fixture_paths:
        raise SystemExit(f"no fixtures found in {args.fixtures_dir}")

    images: dict[str, np.ndarray] = {}
    for path in fixture_paths:
        image = Image.open(path).convert("RGB")
        images[path] = np.array(image)[:, :, ::-1].copy()

    engines = make_engines()

    print("=== construct + warm up ===", flush=True)
    init_times: dict[str, float] = {}
    for engine in engines:
        init_s = engine.construct()
        init_times[engine.name] = init_s
        # one untimed warmup call so any lazy session/graph compilation
        # (ONNX Runtime, OpenVINO) doesn't land inside rep 0's timing
        engine.run(images[fixture_paths[0]])
        print(f"{engine.name}: init_s={init_s:.3f}", flush=True)

    print("=== interleaved warm reps ===", flush=True)
    # rep-major, then fixture, then engine: every engine sees the same
    # spread of wall-clock time across the whole run, not clustered in one
    # window — guards against the session-level drift already observed on
    # Cloud Run (see docs/pipeline-tuning.md / project memory).
    raw_runs: dict[str, dict[str, list[dict]]] = {e.name: {p: [] for p in fixture_paths} for e in engines}
    for rep in range(args.reps):
        for path in fixture_paths:
            image_bgr = images[path]
            for engine in engines:
                result = engine.run(image_bgr)
                raw_runs[engine.name][path].append(
                    {
                        "total_s": result.total_s,
                        "detect_s": result.detect_s,
                        "recognize_s": result.recognize_s,
                        "region_count": len(result.lines),
                        "lines": [
                            {"bbox": ln.bbox, "text": ln.text, "confidence": ln.confidence} for ln in result.lines
                        ],
                    }
                )
                print(
                    f"rep={rep} fixture={os.path.basename(path)} engine={engine.name} "
                    f"total_s={result.total_s:.4f} regions={len(result.lines)}",
                    flush=True,
                )

    print("=== accuracy vs paddle (rep 0 lines) ===", flush=True)
    accuracy: dict[str, dict] = {}
    paddle_name = "paddle_ppocrv5_mobile"
    for engine in engines:
        if engine.name == paddle_name:
            continue
        per_fixture = {}
        for path in fixture_paths:
            ref_lines = [BenchLine(**ln) for ln in raw_runs[paddle_name][path][0]["lines"]]
            cand_lines = [BenchLine(**ln) for ln in raw_runs[engine.name][path][0]["lines"]]
            match_result = _match_lines(ref_lines, cand_lines)
            matched_detail = []
            for ri, ci, iou in match_result["matches"]:
                r, c = ref_lines[ri], cand_lines[ci]
                matched_detail.append(
                    {
                        "ref_text": r.text,
                        "cand_text": c.text,
                        "iou": iou,
                        "cer": _cer(r.text, c.text),
                        "text_exact_match": r.text == c.text,
                    }
                )
            per_fixture[os.path.basename(path)] = {
                "ref_region_count": len(ref_lines),
                "cand_region_count": len(cand_lines),
                "matched": len(match_result["matches"]),
                "missed": [ref_lines[ri].text for ri in match_result["missed"]],
                "extra": [cand_lines[ci].text for ci in match_result["extra"]],
                "matched_detail": matched_detail,
            }
        accuracy[engine.name] = per_fixture

    output = {
        "reps": args.reps,
        "fixtures": [os.path.basename(p) for p in fixture_paths],
        "init_times_s": init_times,
        "raw_runs": raw_runs,
        "accuracy_vs_paddle": accuracy,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"=== wrote {args.out} ===", flush=True)

    print("\n=== SUMMARY (median total_s across reps, all fixtures) ===", flush=True)
    for engine in engines:
        all_totals = [run["total_s"] for path in fixture_paths for run in raw_runs[engine.name][path]]
        all_detects = [
            run["detect_s"] for path in fixture_paths for run in raw_runs[engine.name][path] if run["detect_s"] is not None
        ]
        all_recs = [
            run["recognize_s"]
            for path in fixture_paths
            for run in raw_runs[engine.name][path]
            if run["recognize_s"] is not None
        ]
        med_total = statistics.median(all_totals)
        med_det = statistics.median(all_detects) if all_detects else None
        med_rec = statistics.median(all_recs) if all_recs else None
        print(
            f"{engine.name}: init={init_times[engine.name]:.3f}s median_total={med_total:.4f}s "
            f"median_detect={med_det} median_recognize={med_rec}",
            flush=True,
        )


if __name__ == "__main__":
    main()
