"""Downstream round-trip validation for a promising alternative OCR engine.

Reuses the exact same stages (separate -> match_font -> estimate_color ->
compose_region) and the exact same accuracy gate (MEAN_DELTA_THRESHOLD=2.0)
as services/pipeline/tests/test_round_trip.py, substituting only the OCR
engine that produces the initial detected lines. Must run with
services/pipeline on PYTHONPATH (mounted read-only at /pipeline_src) since
it imports stages/fonts/models from there — same code path production
uses, not a reimplementation.

Usage (inside the bench container):
    PYTHONPATH=/pipeline_src python roundtrip_check.py --engine rapidocr_onnxruntime --fixtures-dir /fixtures
"""

import argparse
import glob
import os

import numpy as np
from PIL import Image

from engines import PaddleEngine, RapidEngine, TesseractEngine

MEAN_DELTA_THRESHOLD = 2.0
LOW_CONFIDENCE_THRESHOLD = 0.85

# The real, measured-today baseline (confirmed by running
# test_round_trip.py against unmodified production Paddle in this same
# investigation) — not the stale KNOWN_OPEN_GAPS dict in the test file.
BASELINE_FAILURES = {
    ("android_2x_profile.jpg", "Jordan Rivera"),
    ("ios_3x_login.png", "Email address"),
    ("web_3x_dashboard.jpg", "$482,910"),
    ("web_3x_dashboard.jpg", "Active Users"),
    ("windows_1x_dialog.png", "System Settings"),
    ("windows_1x_dialog.png", "Choose how updates are installed"),
}


def make_engine(name: str):
    if name == "paddle":
        return PaddleEngine()
    if name == "rapidocr_onnxruntime":
        return RapidEngine("onnxruntime")
    if name == "rapidocr_openvino":
        return RapidEngine("openvino")
    if name == "tesseract":
        return TesseractEngine()
    raise ValueError(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", required=True)
    parser.add_argument("--fixtures-dir", default="/fixtures")
    args = parser.parse_args()

    from fonts.registry import find_font_path
    from stages.detect import group_into_blocks
    from stages.match import estimate_color, match_font
    from stages.render_stage import compose_region
    from stages.separate import separate

    engine = make_engine(args.engine)
    engine.construct()

    patterns = ("*.png", "*.jpg", "*.jpeg")
    fixture_paths = sorted(p for pattern in patterns for p in glob.glob(os.path.join(args.fixtures_dir, pattern)))

    total_regions = 0
    passing = 0
    unflagged_failures = []
    baseline_hits = []

    for path in fixture_paths:
        fixture_name = os.path.basename(path)
        image = Image.open(path).convert("RGB")
        image_bgr = np.array(image)[:, :, ::-1].copy()

        result = engine.run(image_bgr)
        boxed = [{"text": ln.text, "bbox": ln.bbox, "confidence": ln.confidence} for ln in result.lines]
        lines = group_into_blocks(boxed)

        for line in lines:
            if not line.text.strip():
                continue
            total_regions += 1

            separation = separate(image_bgr, line.bbox)
            match = match_font(line.text, separation.alpha, separation.alpha.shape, line.bbox[3])
            color = estimate_color(image_bgr, separation.alpha, separation.crop_bbox, separation.bg_variance)
            font_path = find_font_path(match.family, match.weight)

            render_result = compose_region(
                image_bgr,
                separation.crop_bbox,
                separation.alpha,
                color.background,
                line.text,
                font_path,
                match.size,
                match.letter_spacing,
                match.baseline_y,
                color.text_color,
                alignment="left",
                base_x_offset=match.x_offset,
            )

            x0, y0, x1, y1 = separation.crop_bbox
            original_patch = image_bgr[y0:y1, x0:x1].astype(np.float64)
            rendered_patch = render_result.image_bgr[y0:y1, x0:x1].astype(np.float64)
            confidence = min(line.confidence, match.score)
            mean_delta = float(np.abs(original_patch - rendered_patch).mean()) if original_patch.size else 0.0

            if mean_delta < MEAN_DELTA_THRESHOLD:
                passing += 1
                continue

            key = (fixture_name, line.text)
            if key in BASELINE_FAILURES:
                baseline_hits.append(f"{key}: mean_delta={mean_delta:.4f} score={confidence:.4f} (pre-existing)")
            elif confidence >= LOW_CONFIDENCE_THRESHOLD:
                unflagged_failures.append((fixture_name, line.text, mean_delta, confidence))
            else:
                print(f"  (low-confidence, correctly flagged) {key}: mean_delta={mean_delta:.4f} score={confidence:.4f}")

    print(f"\nengine={args.engine} total_regions={total_regions} passing={passing} "
          f"pass_rate={passing/total_regions:.3f}" if total_regions else "no regions")
    print(f"\nbaseline (pre-existing, expected) failures still present ({len(baseline_hits)}/6):")
    for h in baseline_hits:
        print(f"  - {h}")
    print(f"\nNEW unflagged failures beyond the 6-region baseline ({len(unflagged_failures)}):")
    for f in unflagged_failures:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
