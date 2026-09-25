"""PILOT C1: scorer unit tests. Every expected value is hand-computed in the
comment next to it (not produced by the code under test)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import score as S  # noqa: E402


def gt_of(lines, ignore=(), icons=()):
    out = []
    for i, spec in enumerate(lines):
        text, box = spec[0], spec[1]
        stress = spec[2] if len(spec) > 2 else False
        out.append({"line_id": f"L{i + 1:04d}", "text": text, "ink_box": list(box), "stress": stress,
                    "category": "stress" if stress else "label", "xheight_px": 8.0, "contrast_ratio": 10.0})
    return {"lines": out, "ignore_regions": [list(r) for r in ignore], "icon_regions": [list(r) for r in icons]}


def P(text, box):
    return {"text": text, "bbox": list(box), "confidence": None}


def m1(res):
    return S.aggregate(res["units"], [res])["M1_cer_n1"]


BOX = (10, 10, 80, 20)


# --- the ten requested cases -------------------------------------------------

def test_exact_match():
    res = S.score_image(gt_of([("Settings", BOX)]), [P("Settings", BOX)])
    agg = S.aggregate(res["units"], [res])
    assert agg["M1_cer_n1"] == 0.0            # 0 edits / 8 chars
    assert agg["M6_line_exact"] == 1.0
    assert agg["M8_detection"]["0.5"]["f1"] == 1.0


def test_character_error_substitution():
    res = S.score_image(gt_of([("Settings", BOX)]), [P("Settlngs", BOX)])
    assert m1(res) == pytest.approx(1 / 8)    # i->l: 1 substitution / 8
    assert S.aggregate(res["units"], [res])["M6_line_exact"] == 0.0


def test_missing_character():
    res = S.score_image(gt_of([("Settings", BOX)]), [P("Setings", BOX)])
    assert m1(res) == pytest.approx(1 / 8)    # 1 deletion / 8


def test_extra_character():
    res = S.score_image(gt_of([("Settings", BOX)]), [P("Setttings", BOX)])
    assert m1(res) == pytest.approx(1 / 8)    # 1 insertion / 8


def test_line_split_is_one_component_without_penalty():
    gt = gt_of([("Monthly Revenue", (0, 0, 150, 20))])
    preds = [P("Monthly", (0, 0, 70, 20)), P("Revenue", (80, 0, 70, 20))]
    res = S.score_image(gt, preds)
    assert len(res["units"]) == 1 and res["units"][0]["kind"] == "component"
    assert res["units"][0]["hyp_n1"] == "Monthly Revenue"   # joined in reading order with one space
    assert m1(res) == 0.0
    # Strict one-to-one detection: IoU = 1400 / 3000 = 0.4667 for each piece.
    det = res["detection"]
    assert det["0.5"]["matched"] == 0
    assert det["0.3"]["matched"] == 1


def test_line_merge_is_one_component_without_penalty():
    gt = gt_of([("Storage", (0, 0, 60, 20)), ("12.4 GB", (200, 0, 60, 20))])
    res = S.score_image(gt, [P("Storage 12.4 GB", (0, 0, 260, 20))])
    assert len(res["units"]) == 1
    u = res["units"][0]
    assert u["n_gt"] == 2 and u["ref_n1"] == "Storage 12.4 GB"
    agg = S.aggregate(res["units"], [res])
    assert agg["M1_cer_n1"] == 0.0
    assert agg["M6_line_exact"] == 1.0         # 2 of 2 GT lines, via the component
    assert agg["M7_numeric_acc"] == 1.0        # "12.4" is the only numeric token


def test_overlapping_boxes_small_overlap_stay_separate():
    # Boxes overlap by 5 px: overlap_min = (100*5) / 2000 = 0.25 < 0.5 -> no cross edges.
    gt = gt_of([("alpha", (0, 0, 100, 20)), ("beta", (0, 15, 100, 20))])
    res = S.score_image(gt, [P("alpha", (0, 0, 100, 20)), P("beta", (0, 15, 100, 20))])
    assert [u["n_gt"] for u in res["units"]] == [1, 1]
    assert m1(res) == 0.0


def test_overlapping_boxes_large_overlap_merge_consistently():
    # Overlap 12 px: overlap_min = 1200 / 2000 = 0.6 >= 0.5 -> one component with 2 GT + 2 preds.
    gt = gt_of([("alpha", (0, 0, 100, 20)), ("beta", (0, 8, 100, 20))])
    res = S.score_image(gt, [P("alpha", (0, 0, 100, 20)), P("beta", (0, 8, 100, 20))])
    assert len(res["units"]) == 1 and res["units"][0]["n_gt"] == 2
    assert res["units"][0]["ref_n1"] == res["units"][0]["hyp_n1"] == "alpha beta"
    assert m1(res) == 0.0


def test_no_detection_counts_every_line_as_deleted():
    gt = gt_of([("Settings", BOX), ("About", (10, 50, 50, 20))])
    res = S.score_image(gt, [])
    agg = S.aggregate(res["units"], [res])
    assert agg["M1_cer_n1"] == 1.0             # (8 + 5) / (8 + 5)
    assert agg["M8_detection"]["0.5"]["recall"] == 0.0
    assert agg["M6_line_exact"] == 0.0


def test_numeric_mismatch():
    res = S.score_image(gt_of([("$482,910", BOX)]), [P("$482,970", BOX)])
    agg = S.aggregate(res["units"], [res])
    assert agg["M1_cer_n1"] == pytest.approx(1 / 8)
    assert agg["M7_numeric_acc"] == 0.0        # 1 numeric token, 0 exact


def test_whitespace_and_normalization_handling():
    cases = [
        # (gt, pred, expected cer_n0, expected cer_n1)
        ("Hello world", "Hello   world", 2 / 11, 0.0),        # 2 extra spaces in N0; collapsed in N1
        ("Hello world", "Hello world", 1 / 11, 0.0),     # NBSP -> space (NFKC) in N1
        ("Don't", "Don’t", 1 / 5, 0.0),                   # right single quote -> '
        ("-0.8%", "−0.8%", 1 / 5, 0.0),                   # minus sign -> hyphen-minus
        ("Loading...", "Loading…", 3 / 10, 0.0),          # ellipsis -> "..." (NFKC); N0: 1 sub + 2 del
        ("abc", "ab​c", 1 / 3, 0.0),                      # zero-width space deleted
        ("Tab here", "Tab\there", 1 / 8, 0.0),                 # tab -> space
    ]
    for g, p, e0, e1 in cases:
        res = S.score_image(gt_of([(g, BOX)]), [P(p, BOX)])
        u = res["units"][0]
        assert u["cer_n0"] == pytest.approx(e0), (g, p)
        assert u["cer_n1"] == pytest.approx(e1), (g, p)


# --- additional cases from PILOT_PLAN C1 ------------------------------------

def test_n1_rules_individually():
    assert S.n1("‘a’ ‚b‛ ′") == "'a' 'b' '"
    assert S.n1("“q” „q‟") == '"q" "q"'
    assert S.n1("".join(chr(c) for c in range(0x2010, 0x2016)) + "−") == "-------"
    assert S.n1("a​‌‍⁠﻿­b") == "ab"
    assert S.n1("a b c\td") == "a b c d"            # em space, narrow NBSP, tab
    assert S.n1("  a \n\n b  ") == "a b"
    assert S.n1("ﬁle") == "file"                           # ﬁ ligature via NFKC
    assert S.n1("Case") == "Case"                               # case preserved
    # NFKC runs first and decomposes U+2033 (double prime) into two U+2032, which
    # rule 3 then maps to two apostrophes; the explicit U+2033 -> '"' mapping in
    # PREREGISTRATION §4 is therefore unreachable. Pinned here, flagged in the report.
    assert S.n1("″") == "''"


def test_casefold_n2():
    res = S.score_image(gt_of([("SUPPORT", BOX)]), [P("Support", BOX)])
    u = res["units"][0]
    assert u["cer_n1"] == pytest.approx(6 / 7)  # U,P,P,O,R,T -> lowercase: 6 substitutions
    assert u["cer_n2"] == 0.0


def test_wer():
    res = S.score_image(gt_of([("Send Feedback", BOX)]), [P("Send Fedback", BOX)])
    assert S.aggregate(res["units"], [res])["M5_wer"] == pytest.approx(1 / 2)


def test_missing_line():
    gt = gt_of([("Settings", BOX), ("About", (10, 50, 50, 20))])
    res = S.score_image(gt, [P("Settings", BOX)])
    kinds = sorted(u["kind"] for u in res["units"])
    assert kinds == ["component", "deletion"]
    assert m1(res) == pytest.approx(5 / 13)    # "About" fully deleted: 5 / (8 + 5)


def test_extra_line_is_an_insertion():
    gt = gt_of([("Settings", BOX)])
    res = S.score_image(gt, [P("Settings", BOX), P("XYZ", (300, 300, 40, 20))])
    assert sorted(u["kind"] for u in res["units"]) == ["component", "insertion"]
    assert m1(res) == pytest.approx(3 / 8)     # 3 inserted chars / 8 reference chars


def test_ignore_region_drop_threshold():
    gt = gt_of([("Settings", BOX)], ignore=[(200, 200, 100, 20)])
    inside = S.score_image(gt, [P("Settings", BOX), P("Call me", (200, 200, 60, 20))])
    assert inside["dropped_ignore"] == 1 and m1(inside) == 0.0
    # Box x 140..240 vs ignore x 200..300: 40 of 100 px wide -> 40% inside (< 50%) -> kept as an insertion.
    partial = S.score_image(gt, [P("Settings", BOX), P("Call", (140, 200, 100, 20))])
    assert partial["dropped_ignore"] == 0
    assert m1(partial) == pytest.approx(4 / 8)


def test_empty_text_prediction_dropped_before_matching():
    res = S.score_image(gt_of([("Settings", BOX)]), [P("Settings", BOX), P(" ​ ", (300, 300, 40, 20))])
    assert res["dropped_empty"] == 1
    assert m1(res) == 0.0


def test_reading_order_rows_then_left_edge():
    items = [
        {"box": [200, 0, 60, 20], "t": "value"},
        {"box": [0, 2, 60, 20], "t": "label"},      # same row (centres 10 vs 12, |2| < 10)
        {"box": [0, 40, 60, 20], "t": "next"},
    ]
    assert [it["t"] for it in S.reading_order(items)] == ["label", "value", "next"]


def test_stress_lines_excluded_from_headline_but_in_confusion_pass():
    gt = gt_of([("Settings", BOX), ("Il1 O0o", (10, 60, 80, 20), True)])
    preds = [P("Settings", BOX), P("I11 O0o", (10, 60, 80, 20))]
    res = S.score_image(gt, preds)
    assert m1(res) == 0.0                      # stress GT removed; its prediction dropped, not an insertion
    assert res["dropped_ignore"] == 1
    conf = S.confusions(gt, preds)
    assert conf[("l", "1")] == 1               # the stress line is used for RQ9


def test_icon_insertion_flag_and_sensitivity_metric():
    gt = gt_of([("Settings", BOX)], icons=[(300, 10, 20, 20)])
    res = S.score_image(gt, [P("Settings", BOX), P("Q", (300, 10, 20, 20))])
    agg = S.aggregate(res["units"], [res])
    assert agg["M1_cer_n1"] == pytest.approx(1 / 8)
    assert agg["M1_cer_n1_no_icon_insertions"] == 0.0


def test_micro_average_pools_characters():
    a = S.score_image(gt_of([("ab", BOX)]), [P("xb", BOX)])          # 1 / 2
    b = S.score_image(gt_of([("abcdefgh", BOX)]), [P("abcdefgh", BOX)])  # 0 / 8
    agg = S.aggregate(a["units"] + b["units"], [a, b])
    assert agg["M1_cer_n1"] == pytest.approx(1 / 10)  # pooled, not mean of 0.5 and 0


def test_bag_of_words_f1():
    res = S.score_image(gt_of([("a b c", BOX)]), [P("a b d e", BOX)])
    # intersection 2; precision 2/4, recall 2/3 -> F1 = 2*(0.5*0.6667)/(1.1667) = 0.5714
    assert res["bow_f1"] == pytest.approx(4 / 7)


def test_downscaled_variant_uses_measured_half_resolution_boxes():
    # Full-res ink (20,20,160,40); 0.5x would be (10,10,80,20). The measured half-res
    # box is wider, (7,8,86,24), as Lanczos spreads ink. A prediction on the measured
    # box must match it exactly (IoU 1), proving the measured box is used.
    gt = gt_of([("Settings", (20, 20, 160, 40))])
    gt["lines"][0]["ink_box_half"] = [7, 8, 86, 24]
    gt["downscaled_0p5"] = {"ignore_regions": [], "icon_regions": []}
    res = S.score_image(gt, [P("Settings", (7, 8, 86, 24))], downscale=0.5)
    assert res["lines"][0]["iou"] == 1.0
    # IoU of the naive 0.5x box with the measured one: 1600 / 2064 = 0.7752
    naive = S.score_image(gt, [P("Settings", (10, 10, 80, 20))], downscale=0.5)
    assert naive["lines"][0]["iou"] == pytest.approx(1600 / 2064)


def test_downscaled_variant_without_measured_geometry_is_an_error():
    with pytest.raises(ValueError):
        S.score_image(gt_of([("Settings", BOX)]), [], downscale=0.5)
