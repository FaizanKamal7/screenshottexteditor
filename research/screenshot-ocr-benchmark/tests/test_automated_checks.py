"""Mutation tests for the automated checks that replaced human review
(AUTOMATED_VALIDATION.md). Each criterion must pass on clean input and catch its
known defect; a check that cannot catch its defect is broken.

Chromium cases run the real renderer (render_chromium.render_base) on
templates/_fixtures/glyphs, one element at a time (?only=<id>).
"""

import json
import os
import sys

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import auto_checks as AC  # noqa: E402

playwright = pytest.importorskip("playwright.sync_api")
import render_chromium as rc  # noqa: E402

GOOD = ["plain", "mono-nolig", "two-lines", "nested"]   # "nested": syntax-highlight spans (true negative)


@pytest.fixture(scope="module")
def fixture_results():
    server, port = rc.start_server()
    out = {}
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        for only in GOOD + ["mono-lig", "transform", "pseudo", "fallback", "reordered", "occluded", "forbidden"]:
            url = f"http://127.0.0.1:{port}/templates/_fixtures/glyphs/index.html?only={only}&theme=light"
            _, gt, diff, val = rc.render_base(browser, url, only, "fixture", "desktop", 1, "light")
            out[only] = {"a3": AC.a3_completeness(val, gt, diff), "a4": AC.a4_text_fidelity(val),
                         "a5": AC.a5_wrapping(val), "val": val}
        browser.close()
    server.shutdown()
    return out


# --- clean controls: every automated check passes -----------------------------

@pytest.mark.parametrize("only", GOOD)
def test_clean_elements_pass_all_checks(fixture_results, only):
    r = fixture_results[only]
    assert r["a3"]["pass"], r["a3"]["parts"]
    assert r["a4"]["pass"], r["a4"]["parts"]
    assert r["a5"]["pass"], r["a5"]["parts"]


def test_wrapped_paragraph_has_two_lines(fixture_results):
    el = fixture_results["two-lines"]["val"]["elements"][0]
    assert el["gt_lines"] == ["alpha", "beta"] and el["range_line_count"] == 2


# --- A4: glyph fidelity defects ---------------------------------------------------

def test_ligature_caught_by_canonical_render(fixture_results):
    r = fixture_results["mono-lig"]["a4"]
    assert not r["parts"]["A4.1_canonical_render_identical"] and r["canonical_render_diff_pixels"] > 0


def test_text_transform_caught(fixture_results):
    r = fixture_results["transform"]["a4"]
    assert not r["parts"]["A4.1_canonical_render_identical"]
    assert not r["parts"]["style_guard_no_violations"]


def test_generated_content_caught(fixture_results):
    r = fixture_results["pseudo"]
    assert not r["a4"]["parts"]["A4.1_canonical_render_identical"]
    assert not r["a3"]["parts"]["A3.5_glyph_count_equals_rendered_chars"]   # glyphs 9 vs 5 rendered chars
    assert not r["a3"]["parts"]["A3.3_no_non_dom_text_sources"]


def test_fallback_font_caught(fixture_results):
    assert not fixture_results["fallback"]["a4"]["parts"]["A4.2_pinned_fonts_only"]


def test_reordered_text_caught(fixture_results):
    r = fixture_results["reordered"]["a4"]
    assert not r["parts"]["A4.3_visual_order_equals_logical"] and r["order_violations"] > 0


# --- A3: completeness defects -------------------------------------------------------

def test_occluded_text_caught(fixture_results):
    r = fixture_results["occluded"]["a3"]
    assert not r["parts"]["A3.6_no_occlusion"] and r["occluded_chars"] > 0


def test_non_dom_text_sources_caught(fixture_results):
    r = fixture_results["forbidden"]["a3"]
    assert not r["parts"]["A3.3_no_non_dom_text_sources"]
    assert {"canvas", "text"} <= set(r["forbidden_sources"]["tags"])


# --- A5: wrapping defects (constructed evidence) ------------------------------------

def _val_with(elements):
    return {"elements": elements}


def _el(lines, rects, range_count, inner):
    return {"idx": 0, "category": "paragraph", "clipped": False, "gt_lines": lines, "gt_line_rects_css": rects,
            "range_line_count": range_count, "inner_text": inner, "occluded_chars": 0, "hit_tested_chars": 1,
            "order_violations": 0}


GOOD_RECTS = [[0, 0, 50, 18], [0, 22, 40, 18]]


def test_a5_clean():
    assert AC.a5_wrapping(_val_with([_el(["alpha", "beta"], GOOD_RECTS, 2, "alpha beta")]))["pass"]


def test_a5_line_count_mismatch_caught():
    r = AC.a5_wrapping(_val_with([_el(["alpha", "beta"], GOOD_RECTS, 3, "alpha beta")]))
    assert not r["parts"]["A5.1_independent_line_count"]


def test_a5_lost_character_caught():
    r = AC.a5_wrapping(_val_with([_el(["alpha", "bet"], GOOD_RECTS, 2, "alpha beta")]))
    assert not r["parts"]["A5.2_lossless_split"]


def test_a5_misordered_lines_caught():
    r = AC.a5_wrapping(_val_with([_el(["alpha", "beta"], [[0, 22, 50, 18], [0, 0, 40, 18]], 2, "alpha beta")]))
    assert not r["parts"]["A5.3_geometric_order"]


# --- B4: box placement defects -------------------------------------------------------

def _gt_and_mask():
    mask = np.zeros((60, 200), dtype=bool)
    mask[10:20, 10:90] = True          # line 1 ink
    mask[35:47, 10:120] = True         # line 2 ink
    gt = {"lines": [
        {"line_id": "L0001", "layout_box": [8, 8, 84, 14], "ink_box": [10, 10, 80, 10]},
        {"line_id": "L0002", "layout_box": [8, 33, 114, 16], "ink_box": [10, 35, 110, 12]}],
        "ignore_regions": [], "icon_regions": []}
    return gt, mask


def test_b4_boxes_clean():
    gt, mask = _gt_and_mask()
    assert AC.b4_boxes(gt, mask)["pass"]


def test_b4_tampered_box_caught():
    gt, mask = _gt_and_mask()
    gt["lines"][0]["ink_box"] = [11, 10, 80, 10]      # off by one pixel
    assert not AC.b4_boxes(gt, mask)["parts"]["B4.1_reproducible_from_mask"]


def test_b4_bad_ignore_region_caught():
    gt, mask = _gt_and_mask()
    gt["ignore_regions"] = [[150, 50, 20, 5]]          # contains no ink
    assert not AC.b4_boxes(gt, mask)["parts"]["B4.4_ignore_regions_valid"]


def _write(path, arr):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(arr).save(path)


def test_b4_registration_detects_one_pixel_shift(tmp_path):
    rng = np.random.default_rng(0)
    base = (rng.random((120, 160)) > 0.8).astype(np.uint8) * 255
    base = np.stack([base] * 3, axis=2)
    ds = str(tmp_path)
    _write(os.path.join(ds, "renders", "b.png"), base)
    _write(os.path.join(ds, "images", "b_V00.png"), base)
    _write(os.path.join(ds, "images", "b_Vshift.png"), np.roll(base, 1, axis=1))
    rows = [{"image_id": "b_V00", "base_id": "b", "file": "images/b_V00.png", "downscale": 1.0}]
    assert AC.b4_registration(ds, rows)["pass"]
    rows = [{"image_id": "b_Vshift", "base_id": "b", "file": "images/b_Vshift.png", "downscale": 1.0}]
    r = AC.b4_registration(ds, rows)
    assert not r["pass"] and abs(r["failures"][0]["shift"][0]) == pytest.approx(1.0, abs=0.1)


def test_b4_registration_detects_wrong_size(tmp_path):
    base = np.zeros((40, 60, 3), dtype=np.uint8)
    ds = str(tmp_path)
    _write(os.path.join(ds, "renders", "b.png"), base)
    _write(os.path.join(ds, "images", "b_V12.png"), np.zeros((20, 31, 3), dtype=np.uint8))   # should be 20x30
    rows = [{"image_id": "b_V12", "base_id": "b", "file": "images/b_V12.png", "downscale": 0.5}]
    assert not AC.b4_registration(ds, rows)["pass"]


# --- E2: engine coordinate defects ------------------------------------------------------

def _gt_grid(width=1000, height=400, row_step=60):
    lines = []
    for i in range(12):
        x, y = 20 + (i % 3) * 300, 30 + (i // 3) * row_step
        lines.append({"line_id": f"L{i:04d}", "text": f"line {i}", "ink_box": [x, y, 150 + 10 * (i % 4), 20],
                      "stress": False})
    return {"lines": lines, "ignore_regions": [], "icon_regions": [], "width": width, "height": height}


def _preds(gt, scale=1.0, dy=0.0):
    return [{"bbox": [ln["ink_box"][0] * scale, ln["ink_box"][1] * scale + dy, ln["ink_box"][2] * scale,
                      ln["ink_box"][3] * scale], "text": ln["text"]} for ln in gt["lines"]]


def test_e2_oracle_passes():
    gt = _gt_grid()
    r = AC.e2_coordinates([(gt, _preds(gt), 1.0)])
    assert r["pass"], r["parts"]
    assert r["median_slope_x"] == pytest.approx(1.0) and r["median_offset_y_h"] == pytest.approx(0.0)


def test_e2_scale_error_caught():
    gt = _gt_grid()
    r = AC.e2_coordinates([(gt, _preds(gt, scale=1.1), 1.0)])
    assert not r["parts"]["E2.3_no_scale_error"]


def _with_merged_outliers(gt, preds, k):
    """Replace k predictions with a wide merged box sharing the line's left edge
    (as when an engine joins a label and its value on one row). Still matched at IoU >= 0.3."""
    out = [dict(p) for p in preds]
    for i in range(k):
        x, y, w, h = out[i]["bbox"]
        out[i]["bbox"] = [x, y, w * 3.0, h]
    return out


def test_e2_segmentation_outliers_are_not_a_coordinate_error():
    gt = _gt_grid()
    preds = _with_merged_outliers(gt, _preds(gt), 3)          # 3 of 12 = 25% merged boxes
    r = AC.e2_coordinates([(gt, preds, 1.0)])
    assert r["pass"], r["parts"]


def test_e2_scale_error_caught_despite_outliers():
    gt = _gt_grid()
    preds = _with_merged_outliers(gt, _preds(gt, scale=1.04), 3)   # real 4% resize bug + 25% outliers
    r = AC.e2_coordinates([(gt, preds, 1.0)])
    assert not r["parts"]["E2.3_no_scale_error"]


# --- E2.3 pooled per image size (approved 2026-09-25) + E2.4 --------------------------

def test_e2_bug_confined_to_one_image_size_caught():
    """Regression test for the pooling amendment: a resize bug that affects only one image
    size (e.g. an engine that downsamples inputs above some width) must still fail E2.3,
    even though every other size is correct and the engine-wide median slope stays ~1."""
    small = [(_gt_grid(1000, 400, 25), None) for _ in range(3)]
    big = [(_gt_grid(2000, 800, 25), None) for _ in range(2)]
    images = [(g, _preds(g), 1.0) for g, _ in small] + [(g, _preds(g, scale=1.08), 1.0) for g, _ in big]
    r = AC.e2_coordinates(images)
    assert r["pooled_slopes"]["2000x800"][0] == pytest.approx(1.08, abs=0.005)
    assert r["pooled_slopes"]["1000x400"][0] == pytest.approx(1.0, abs=0.005)
    assert not r["parts"]["E2.3_no_scale_error"]


def test_e2_severe_size_bug_caught_by_overlap_check():
    """Coordinates left at half scale for one size: no matches there, so no slope. E2.4 must fail."""
    small = _gt_grid(1000, 400, 25)
    big = _gt_grid(2000, 800, 25)
    images = [(small, _preds(small), 1.0), (big, _preds(big, scale=0.5), 1.0)]
    r = AC.e2_coordinates(images)
    assert "2000x800" not in r["pooled_slopes"]
    assert not r["parts"]["E2.4_every_size_overlaps"]


def test_e2_one_missegmented_image_among_clean_same_size_passes():
    """The pilot's failure mode: one image with ~40% merged boxes, among correct images of
    the same size. Correct coordinates, so E2 must pass."""
    gts = [_gt_grid(1000, 400) for _ in range(4)]
    images = [(g, _preds(g), 1.0) for g in gts[:3]]
    images.append((gts[3], _with_merged_outliers(gts[3], _preds(gts[3]), 5), 1.0))   # 5 of 12 = 42%
    r = AC.e2_coordinates(images)
    assert r["pass"], r["parts"]


def test_e2_systematic_offset_caught():
    gt = _gt_grid()
    r = AC.e2_coordinates([(gt, _preds(gt, dy=8.0), 1.0)])     # 8 px = 0.4 line height
    assert not r["parts"]["E2.2_no_systematic_offset"]
