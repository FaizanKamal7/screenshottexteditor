"""Ground-truth boxes for the 50% variants (V12, V13), measured on downscaled pixels.

PILOT B5 showed that 0.5 × the full-resolution ink box understates where ink lands
after Lanczos downscaling (up to 3.5 px at half resolution). Boxes are therefore
measured with the same definition used at full resolution (METHODOLOGY §4.4,
amendment A2): downscale both the normal and the text-hidden render with the
filter used for V12 (Pillow LANCZOS), take every pixel whose change exceeds
16/255 as ink (INK_THRESHOLD_HALF), and assign it to lines with assign_ink(). V13 is V12 JPEG-compressed, so it shares
V12's boxes (compression is a degradation of the image, not of the geometry,
exactly as V02–V11 share V00's boxes).

Writes into each ground_truth/{base_id}.json:
  lines[*].ink_box_half, lines[*].ink_pixels_half,
  downscaled_0p5 = {filter, pad_px, unowned_ink_pixels, ignore_regions, icon_regions}

    python scripts/downscaled_gt.py --dataset pilot/dataset
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_chromium import assign_ink  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTOR = 0.5
# Source ink lies within the full-res layout box + 2 px (= +1 px at half size); a
# Lanczos-3 kernel at 2× reduction spreads it by at most 3 output px. 1 + 3 = 4.
PAD_HALF = 4
# A pixel is half-res ink when any channel changes by more than 16/255. With "any
# change" (the full-res rule), faint Lanczos ringing (< ~6% amplitude) reached ~3 px
# into line gaps, so adjacent lines' boxes overlapped 21-45% at the smallest text and
# the C5 jitter check failed on 4/312 images. 16/255 is the threshold fixed for the
# original B5 check before its results were seen. See PREREGISTRATION A2.
INK_THRESHOLD_HALF = 16


def half(img: Image.Image) -> np.ndarray:
    w, h = img.size
    return np.asarray(img.convert("RGB").resize((w // 2, h // 2), Image.LANCZOS)).astype(np.int16)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=os.path.join(ROOT, "pilot", "dataset"))
    args = parser.parse_args()
    gt_dir = os.path.join(args.dataset, "ground_truth")
    summary = []
    for name in sorted(os.listdir(gt_dir)):
        path = os.path.join(gt_dir, name)
        with open(path, encoding="utf-8") as f:
            gt = json.load(f)
        bid = gt["base_id"]
        normal = half(Image.open(os.path.join(args.dataset, "renders", f"{bid}.png")))
        hidden = half(Image.open(os.path.join(args.dataset, "internal", f"{bid}_hidden.png")))
        diff = np.abs(normal - hidden).max(axis=2) > INK_THRESHOLD_HALF
        scale = lambda b: [v * FACTOR for v in b]  # noqa: E731
        ignore = [scale(r) for r in gt["ignore_regions"]]
        boxes, counts, unowned = assign_ink(diff, [scale(ln["layout_box"]) for ln in gt["lines"]], ignore, PAD_HALF)
        for ln, box, count in zip(gt["lines"], boxes, counts):
            ln["ink_box_half"] = box
            ln["ink_pixels_half"] = count
        gt["downscaled_0p5"] = {
            "filter": "Pillow LANCZOS", "pad_px": PAD_HALF, "ink_threshold": INK_THRESHOLD_HALF,
            "unowned_ink_pixels": int(unowned.sum()),
            "ignore_regions": [[round(v, 3) for v in r] for r in ignore],
            "icon_regions": [[round(v, 3) for v in scale(r)] for r in gt["icon_regions"]],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(gt, f, indent=1, ensure_ascii=False)
        no_ink = sum(1 for c in counts if c == 0)
        summary.append((bid, int(unowned.sum()), no_ink))
        print(f"{bid}: unowned_half_ink={int(unowned.sum())} lines_without_half_ink={no_ink}", flush=True)
    bad = [s for s in summary if s[1] or s[2]]
    print(f"{len(summary)} bases; bases with unowned ink or ink-less lines: {len(bad)}")


if __name__ == "__main__":
    main()
