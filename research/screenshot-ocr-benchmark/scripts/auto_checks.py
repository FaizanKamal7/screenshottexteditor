"""Automated replacements for the former human-review checks (AUTOMATED_VALIDATION.md).

Pure functions over the renderer's validation records, ground truth, masks,
manifest and predictions. Each returns {"pass": bool, ...evidence}. validate_pilot.py
turns them into A3/A4/A5/B4/E2 statuses; tests/test_automated_checks.py
mutation-tests each one against a known defect.
"""

import math
import os
import statistics
from collections import defaultdict

import numpy as np
from PIL import Image

import score
from render_chromium import INK_PAD, assign_ink

# Acceptance thresholds (AUTOMATED_VALIDATION.md; fixed before evaluation).
REGISTRATION_MAX_SHIFT_PX = 0.5
E2_MIN_MEDIAN_IOU = 0.30
E2_MATCH_IOU = 0.30
E2_MAX_MEDIAN_OFFSET_H = 0.25        # median centre offset / line height, each axis
E2_MEDIAN_SLOPE = (0.98, 1.02)
E2_IMAGE_SLOPE = (0.95, 1.05)
E2_MIN_MATCHES_FOR_SLOPE = 8


# ---------------------------------------------------------------------------
# A3 completeness
# ---------------------------------------------------------------------------

def a3_completeness(val: dict, gt: dict, mask: np.ndarray) -> dict:
    fs = val["forbidden_sources"]
    icon_ink = 0
    h, w = mask.shape
    for x, y, bw, bh in gt.get("icon_regions", []):
        x0, y0 = max(0, int(math.floor(x))), max(0, int(math.floor(y)))
        x1, y1 = min(w, int(math.ceil(x + bw))), min(h, int(math.ceil(y + bh)))
        icon_ink += int(mask[y0:y1, x0:x1].sum())
    occluded = sum(e["occluded_chars"] for e in val["elements"] if not e["clipped"])
    parts = {
        "A3.1_token_reconciliation": val["token_reconciliation"]["ok"],
        "A3.2_no_untagged_or_nested": not val["untagged_visible_text"] and val["nested_tagged_elements"] == 0,
        "A3.3_no_non_dom_text_sources": not fs["tags"] and not fs["background_images"] and not fs["generated_content"],
        "A3.4_pixel_accounting": val["unowned_ink_pixels"] == 0 and icon_ink == 0,
        "A3.5_glyph_count_equals_rendered_chars": not val["glyph_count_mismatches"],
        "A3.6_no_occlusion": occluded == 0,
    }
    return {"pass": all(parts.values()), "parts": parts, "icon_ink_pixels": icon_ink, "occluded_chars": occluded,
            "forbidden_sources": fs, "glyph_count_mismatches": val["glyph_count_mismatches"][:5]}


# ---------------------------------------------------------------------------
# A4 line text correctness
# ---------------------------------------------------------------------------

def a4_text_fidelity(val: dict) -> dict:
    order = sum(e["order_violations"] for e in val["elements"] if not e["clipped"])
    parts = {
        "A4.1_canonical_render_identical": val["canonical_render_diff_pixels"] == 0,
        "A4.2_pinned_fonts_only": val["font_fallback_nodes"] == 0 and not val["font_load_errors"],
        "A4.3_visual_order_equals_logical": order == 0,
        "style_guard_no_violations": not val["style_violations"],
    }
    return {"pass": all(parts.values()), "parts": parts,
            "canonical_render_diff_pixels": val["canonical_render_diff_pixels"], "order_violations": order}


def a4_cross_scale_text(gts: dict) -> dict:
    """A4.4: line texts identical across the scale factors of each template/theme."""
    groups = defaultdict(dict)
    for gt in gts.values():
        groups[(gt["template_id"], gt["theme"])][gt["dpr"]] = [ln["text"] for ln in gt["lines"]]
    bad = [f"{t}/{th}" for (t, th), by in groups.items() if len({tuple(v) for v in by.values()}) != 1]
    return {"pass": not bad, "groups": len(groups), "mismatched": bad}


# ---------------------------------------------------------------------------
# A5 wrapping
# ---------------------------------------------------------------------------

def a5_wrapping(val: dict) -> dict:
    count_bad, lossless_bad, order_bad = [], [], []
    for e in val["elements"]:
        if e["clipped"]:
            continue
        n = len(e["gt_lines"])
        if e["range_line_count"] != n:
            count_bad.append({"idx": e["idx"], "gt_lines": n, "range_lines": e["range_line_count"]})
        if score.n1(" ".join(e["gt_lines"])) != score.n1(e["inner_text"]):
            lossless_bad.append({"idx": e["idx"], "gt": " | ".join(e["gt_lines"])[:80], "inner": e["inner_text"][:80]})
        rects = e["gt_line_rects_css"]
        for a, b in zip(rects, rects[1:]):
            if not (a[1] + a[3] / 2 < b[1] + b[3] / 2 and a[1] + a[3] <= b[1] + 0.5):
                order_bad.append({"idx": e["idx"], "rects": [a, b]})
                break
    parts = {"A5.1_independent_line_count": not count_bad, "A5.2_lossless_split": not lossless_bad,
             "A5.3_geometric_order": not order_bad}
    return {"pass": all(parts.values()), "parts": parts, "count_mismatch": count_bad[:5],
            "lossless_mismatch": lossless_bad[:5], "order_violations": order_bad[:5],
            "multi_line_elements": sum(1 for e in val["elements"] if len(e["gt_lines"]) > 1)}


# ---------------------------------------------------------------------------
# B4 box placement
# ---------------------------------------------------------------------------

def b4_boxes(gt: dict, mask: np.ndarray) -> dict:
    """B4.1 reproducible boxes from the saved mask; B4.2 tight boxes; B4.4 ignore regions."""
    boxes, _, _ = assign_ink(mask, [ln["layout_box"] for ln in gt["lines"]], gt["ignore_regions"], INK_PAD)
    irreproducible = [ln["line_id"] for ln, b in zip(gt["lines"], boxes) if b != ln["ink_box"]]
    # ownership map to test tightness on each line's own pixels
    loose = []
    for ln, b in zip(gt["lines"], boxes):
        if b is None:
            continue
        x, y, w, h = b
        sub = mask[y:y + h, x:x + w]
        if not (sub[0, :].any() and sub[-1, :].any() and sub[:, 0].any() and sub[:, -1].any()):
            loose.append(ln["line_id"])
    ignore_bad = []
    for r in gt["ignore_regions"]:
        x0, y0 = int(math.floor(r[0])), int(math.floor(r[1]))
        x1, y1 = int(math.ceil(r[0] + r[2])), int(math.ceil(r[1] + r[3]))
        has_ink = mask[max(0, y0):y1, max(0, x0):x1].any()
        hits = [ln["line_id"] for ln in gt["lines"] if score.intersection(r, ln["ink_box"]) > 0]
        if not has_ink or hits:
            ignore_bad.append({"region": r, "has_ink": bool(has_ink), "intersects": hits})
    parts = {"B4.1_reproducible_from_mask": not irreproducible, "B4.2_tight": not loose,
             "B4.4_ignore_regions_valid": not ignore_bad}
    return {"pass": all(parts.values()), "parts": parts, "irreproducible": irreproducible[:5], "loose": loose[:5],
            "ignore_bad": ignore_bad}


def phase_shift(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Global translation of b relative to a (px), by phase correlation with a
    parabolic sub-pixel refinement of the correlation peak."""
    fa = np.fft.fft2(a - a.mean())
    fb = np.fft.fft2(b - b.mean())
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-12
    c = np.fft.ifft2(r).real
    py, px = np.unravel_index(np.argmax(c), c.shape)
    h, w = c.shape

    def refine(cm, cp, c0):
        den = cm - 2 * c0 + cp
        return 0.0 if den == 0 else 0.5 * (cm - cp) / den

    dy = py + refine(c[(py - 1) % h, px], c[(py + 1) % h, px], c[py, px])
    dx = px + refine(c[py, (px - 1) % w], c[py, (px + 1) % w], c[py, px])
    if dy > h / 2:
        dy -= h
    if dx > w / 2:
        dx -= w
    return float(dx), float(dy)


def gray(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L"), dtype=np.float64)


def b4_registration(dataset: str, rows: list) -> dict:
    """B4.3: every variant is exactly the expected size and globally registered to its
    reference within REGISTRATION_MAX_SHIFT_PX."""
    refs = {}
    bad, worst = [], 0.0
    for r in rows:
        bid = r["base_id"]
        if bid not in refs:
            src = Image.open(os.path.join(dataset, "renders", f"{bid}.png")).convert("RGB")
            w, h = src.size
            refs[bid] = {1.0: gray(src), 0.5: gray(src.resize((w // 2, h // 2), Image.LANCZOS)), "size": (w, h)}
        ref = refs[bid][r["downscale"]]
        w, h = refs[bid]["size"]
        exp = (w, h) if r["downscale"] == 1.0 else (w // 2, h // 2)
        img = Image.open(os.path.join(dataset, r["file"]))
        if img.size != exp:
            bad.append({"image_id": r["image_id"], "size": img.size, "expected": exp})
            continue
        dx, dy = phase_shift(ref, gray(img))
        worst = max(worst, abs(dx), abs(dy))
        if abs(dx) > REGISTRATION_MAX_SHIFT_PX or abs(dy) > REGISTRATION_MAX_SHIFT_PX:
            bad.append({"image_id": r["image_id"], "shift": [round(dx, 3), round(dy, 3)]})
    return {"pass": not bad, "files": len(rows), "worst_abs_shift_px": round(worst, 4), "failures": bad[:10]}


# ---------------------------------------------------------------------------
# E2 engine coordinate sanity
# ---------------------------------------------------------------------------

def _center(b):
    return b[0] + b[2] / 2, b[1] + b[3] / 2


def _slope(xs, ys):
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if len(xs) < 2 or np.ptp(xs) == 0:
        return None
    return float(np.polyfit(xs, ys, 1)[0])


def e2_coordinates(images: list[tuple[dict, list[dict], float]]) -> dict:
    """images: (ground truth, prediction lines, downscale) for one engine."""
    best_ious, dxs, dys, sx, sy = [], [], [], [], []
    for gt, preds, downscale in images:
        ignore, _, box_of = score.geometry_for(gt, downscale)
        gboxes = [box_of(ln) for ln in gt["lines"] if not ln["stress"]]
        pboxes = [list(p["bbox"]) for p in preds if score.n1(p["text"])]
        for g in gboxes:
            ious = [score.iou(g, p) for p in pboxes]
            if ious and max(ious) > 0:
                best_ious.append(max(ious))
        matches = score.greedy_iou_match(gboxes, pboxes, E2_MATCH_IOU)
        gx, gy, px, py = [], [], [], []
        for gi, pi, _ in matches:
            (cgx, cgy), (cpx, cpy) = _center(gboxes[gi]), _center(pboxes[pi])
            h = gboxes[gi][3]
            dxs.append((cpx - cgx) / h)
            dys.append((cpy - cgy) / h)
            gx.append(cgx); gy.append(cgy); px.append(cpx); py.append(cpy)
        if len(matches) >= E2_MIN_MATCHES_FOR_SLOPE:
            a, b = _slope(gx, px), _slope(gy, py)
            if a is not None:
                sx.append(a)
            if b is not None:
                sy.append(b)
    med = lambda v: statistics.median(v) if v else None  # noqa: E731
    out = {
        "median_best_iou": med(best_ious), "median_offset_x_h": med(dxs), "median_offset_y_h": med(dys),
        "median_slope_x": med(sx), "median_slope_y": med(sy),
        "slope_range_x": [min(sx), max(sx)] if sx else None, "slope_range_y": [min(sy), max(sy)] if sy else None,
        "matched_lines": len(dxs), "images_with_slope": len(sx),
    }
    lo, hi = E2_MEDIAN_SLOPE
    ilo, ihi = E2_IMAGE_SLOPE
    parts = {
        "E2.1_median_iou": out["median_best_iou"] is not None and out["median_best_iou"] >= E2_MIN_MEDIAN_IOU,
        "E2.2_no_systematic_offset": out["median_offset_x_h"] is not None
        and abs(out["median_offset_x_h"]) <= E2_MAX_MEDIAN_OFFSET_H and abs(out["median_offset_y_h"]) <= E2_MAX_MEDIAN_OFFSET_H,
        "E2.3_no_scale_error": bool(sx) and bool(sy) and lo <= out["median_slope_x"] <= hi and lo <= out["median_slope_y"] <= hi
        and ilo <= min(sx) and max(sx) <= ihi and ilo <= min(sy) and max(sy) <= ihi,
    }
    out["parts"] = parts
    out["pass"] = all(parts.values())
    return out
