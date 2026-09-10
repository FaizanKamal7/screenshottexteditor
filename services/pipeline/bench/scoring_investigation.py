"""Phase 2 of the font-matching accuracy investigation (see docs/pipeline-tuning.md's
"Investigated, not fixed: font-identity recovery rate..." section, and this
script's own SYNTHETIC_GROUND_TRUTH source, run_match_investigation.py).

That investigation found the true candidate wins outright only 39.4% of the
time on ground-truth fixtures, and specifically that Inter/600 is a
disproportionate attractor. This script asks: is that a search problem or a
*scoring objective* problem — would re-ranking candidates by a different
signal (at the SAME already-converged geometry the production search already
finds) pick the true font more often?

Deliberately NOT changed here: stages/match.py's production scoring/search.
Every alternative signal below is computed against each candidate's already-
converged production geometry (found via match_instrumented.py's verified
bit-exact copy of the real search) — this answers "would re-ranking already-
found candidates by an alternative signal improve top-1 accuracy," not
"would optimizing FOR that signal during search converge differently" (a
separate, more expensive question, only worth asking if this one shows
promise).

Run inside the pipeline container:
    docker exec -e PYTHONPATH=/app:/app/bench <container> python bench/scoring_investigation.py
(needs both /app and /app/bench on PYTHONPATH: this script imports sibling
bench/ modules as well as the main pipeline packages — see the PYTHONPATH
note in docs/pipeline-tuning.md's font-matching investigation section.)
"""

import json
import os
import re
import statistics
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

from fonts.registry import FONT_REGISTRY
from renderer import render_text
from stages.detect import detect
from stages.separate import separate
from match_instrumented import _search_candidate_traced, iou as _iou, _fast_ssim
from run_match_investigation import SYNTHETIC_GROUND_TRUTH, TESTS_FIXTURES_DIR

RESTART_CONFIGS = [(0.8, 0.0), (0.72, 0.5)]
IOU_WEIGHT = 0.7
SSIM_WEIGHT = 0.3

OUT_PATH = os.path.join(os.path.dirname(__file__), "scoring_investigation_results.json")


# ---------------------------------------------------------------------------
# Alternative signal computation — each takes (rendered_alpha, target_alpha),
# both already at the candidate's converged geometry, same shape. All are
# cheap (single-pass numpy ops), no new renders beyond the one used to
# produce `rendered_alpha` itself.
# ---------------------------------------------------------------------------


def _ink_bbox(alpha: np.ndarray, threshold: float = 0.5) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(alpha > threshold)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def aspect_ratio_error(rendered: np.ndarray, target: np.ndarray) -> float | None:
    """Relative error between rendered and target ink bounding-box aspect ratio (w/h)."""
    rb, tb = _ink_bbox(rendered), _ink_bbox(target)
    if rb is None or tb is None:
        return None
    rw, rh = rb[2] - rb[0], rb[3] - rb[1]
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    if rh == 0 or th == 0 or tw == 0:
        return None
    r_ar, t_ar = rw / rh, tw / th
    return abs(r_ar - t_ar) / t_ar


def ink_bbox_dims(alpha: np.ndarray) -> tuple[int, int] | None:
    b = _ink_bbox(alpha)
    if b is None:
        return None
    return (b[2] - b[0], b[3] - b[1])


def stroke_width_median(alpha: np.ndarray, threshold: float = 0.5) -> float | None:
    """Median horizontal run-length of 'on' pixels per row — a cheap proxy
    for stroke thickness (thicker fonts produce longer average runs across
    vertical stems, though this also picks up serifs/counters/whitespace
    between letters, so it's a rough proxy, not a true stroke-width measure).
    """
    binary = (alpha > threshold).astype(np.int8)
    widths: list[int] = []
    for row in binary:
        padded = np.concatenate(([0], row, [0]))
        edges = np.flatnonzero(np.diff(padded))
        widths.extend(int(edges[i + 1] - edges[i]) for i in range(0, len(edges), 2))
    if not widths:
        return None
    return float(np.median(widths))


def projection_profile_corr(rendered: np.ndarray, target: np.ndarray, axis: int) -> float | None:
    """axis=0 -> horizontal projection (density per column, i.e. left-right
    ink distribution). axis=1 -> vertical projection (density per row,
    top-bottom distribution — the same profile _fit_baseline already
    correlates for baseline fitting, reused here as a scoring signal)."""
    r_profile = rendered.sum(axis=axis)
    t_profile = target.sum(axis=axis)
    if r_profile.std() == 0 or t_profile.std() == 0:
        return None
    corr = float(np.corrcoef(r_profile, t_profile)[0, 1])
    return None if np.isnan(corr) else corr


def cap_x_band_ratio(alpha: np.ndarray, threshold: float = 0.5) -> float | None:
    """Density-band proxy for x-height / full-ink-height ratio: the
    fraction of the ink's vertical extent covered by rows whose density is
    at least half the row with the most ink (roughly the x-height band,
    where most lowercase strokes concentrate, vs. the full cap-height/
    ascender/descender extent). Not a literal font-metric cap-height/
    x-height measurement (that needs per-glyph knowledge this alpha mask
    doesn't carry) — a cheap, comparable-across-renders substitute for it.
    """
    binary = alpha > threshold
    row_density = binary.sum(axis=1).astype(float)
    if row_density.max() == 0:
        return None
    b = _ink_bbox(alpha, threshold)
    if b is None:
        return None
    total_h = b[3] - b[1]
    if total_h <= 0:
        return None
    core_thresh = row_density.max() * 0.5
    core_rows = np.flatnonzero(row_density >= core_thresh)
    if len(core_rows) == 0:
        return None
    core_h = core_rows.max() - core_rows.min() + 1
    return core_h / total_h


# ---------------------------------------------------------------------------
# Text metadata classification
# ---------------------------------------------------------------------------


def classify_case(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "no_letters"
    if all(c.isupper() for c in letters):
        return "upper"
    if all(c.islower() for c in letters):
        return "lower"
    if all(w[:1].isupper() and w[1:].islower() for w in re.findall(r"[A-Za-z]+", text)):
        return "title"
    return "mixed"


DESCENDERS = set("gjpqy")
ASCENDERS = set("bdfhklt")


def glyph_flags(text: str) -> dict[str, bool]:
    lower = text.lower()
    return {
        "has_digit": any(c.isdigit() for c in text),
        "has_descender": any(c in DESCENDERS for c in lower),
        "has_ascender": any(c in ASCENDERS for c in lower),
        "has_capital": any(c.isupper() for c in text),
        "has_punctuation": bool(re.search(r"[^\w\s]", text)),
    }


# ---------------------------------------------------------------------------
# Core: run the (verified, unmodified) production search for one candidate,
# then re-render once at the converged geometry to get its alpha mask.
# ---------------------------------------------------------------------------


def _best_restart_result(text, font_path, canvas_size, region_h, target_alpha):
    best = None
    for baseline_ratio, size_grid_phase in RESTART_CONFIGS:
        attempt, _ = _search_candidate_traced(
            text, font_path, canvas_size, region_h, target_alpha, baseline_ratio, size_grid_phase
        )
        if best is None or attempt[-1] > best[-1]:
            best = attempt
    return best  # (size, letter_spacing, baseline_y, x_offset, score)


def analyze_region(fixture: str, text: str, image_bgr: np.ndarray, bbox: tuple[float, float, float, float]) -> dict | None:
    true_family, true_weight = SYNTHETIC_GROUND_TRUTH[(fixture, text)]
    separation = separate(image_bgr, bbox)
    target_alpha = separation.alpha
    canvas_size = (target_alpha.shape[1], target_alpha.shape[0])
    region_h = bbox[3]

    candidates_out = []
    for c in FONT_REGISTRY:
        size, letter_spacing, baseline_y, x_offset, blended_score = _best_restart_result(
            text, c.file_path, canvas_size, region_h, target_alpha
        )
        rendered = render_text(text, c.file_path, size, letter_spacing, (x_offset, baseline_y), canvas_size)

        iou_score = _iou(rendered > 0.5, target_alpha > 0.5)
        ssim_score = _fast_ssim(rendered, target_alpha) if rendered.size >= 49 else iou_score

        candidates_out.append(
            {
                "family": c.family,
                "weight": c.weight,
                "size": size,
                "iou": iou_score,
                "ssim": ssim_score,
                "current_score": blended_score,
                "aspect_ratio_error": aspect_ratio_error(rendered, target_alpha),
                "stroke_width_delta_rel": _rel_stroke_delta(rendered, target_alpha),
                "horiz_proj_corr": projection_profile_corr(rendered, target_alpha, axis=0),
                "vert_proj_corr": projection_profile_corr(rendered, target_alpha, axis=1),
                "cap_x_band_delta": _capx_delta(rendered, target_alpha),
            }
        )

    return {
        "fixture": fixture,
        "text": text,
        "text_len": len(text),
        "region_h": region_h,
        "case": classify_case(text),
        **glyph_flags(text),
        "true_family": true_family,
        "true_weight": true_weight,
        "candidates": candidates_out,
    }


def _rel_stroke_delta(rendered, target) -> float | None:
    r = stroke_width_median(rendered)
    t = stroke_width_median(target)
    if r is None or t is None or t == 0:
        return None
    return abs(r - t) / t


def _capx_delta(rendered, target) -> float | None:
    r = cap_x_band_ratio(rendered)
    t = cap_x_band_ratio(target)
    if r is None or t is None:
        return None
    return abs(r - t)


# ---------------------------------------------------------------------------
# Ranking formulas — each maps a candidate record to a "higher is better"
# score. `current` is the production formula (control). Rest combine it with
# one alternative signal, rescaled to a comparable ~[0,1] range, so a formula
# can be directly compared to the control without unit mismatches dominating
# the result.
# ---------------------------------------------------------------------------


def _safe(value, default=0.5):
    return default if value is None else value


def _inv(delta, default=0.5):
    return default if delta is None else 1.0 / (1.0 + delta)


def _corr01(corr, default=0.5):
    return default if corr is None else (corr + 1.0) / 2.0


RANKING_FORMULAS = {
    "current (0.7*IoU+0.3*SSIM)": lambda c: c["current_score"],
    "iou_only": lambda c: c["iou"],
    "ssim_only": lambda c: c["ssim"],
    "current + aspect_ratio": lambda c: 0.6 * c["current_score"] + 0.4 * _inv(c["aspect_ratio_error"]),
    "current + stroke_width": lambda c: 0.6 * c["current_score"] + 0.4 * _inv(c["stroke_width_delta_rel"]),
    "current + vert_projection": lambda c: 0.6 * c["current_score"] + 0.4 * _corr01(c["vert_proj_corr"]),
    "current + horiz_projection": lambda c: 0.6 * c["current_score"] + 0.4 * _corr01(c["horiz_proj_corr"]),
    "current + cap_x_band": lambda c: 0.6 * c["current_score"] + 0.4 * _inv(c["cap_x_band_delta"]),
    "vert_projection_only": lambda c: _corr01(c["vert_proj_corr"]),
    "stroke_width_only": lambda c: _inv(c["stroke_width_delta_rel"]),
    "kitchen_sink (equal-weight avg)": lambda c: statistics.mean(
        [
            c["current_score"],
            _inv(c["aspect_ratio_error"]),
            _inv(c["stroke_width_delta_rel"]),
            _corr01(c["vert_proj_corr"]),
            _inv(c["cap_x_band_delta"]),
        ]
    ),
}


def evaluate_formulas(records: list[dict]) -> dict[str, dict]:
    results = {}
    for name, fn in RANKING_FORMULAS.items():
        correct = 0
        total = 0
        for r in records:
            scored = [(fn(c), c["family"], c["weight"]) for c in r["candidates"]]
            scored.sort(key=lambda t: t[0], reverse=True)
            winner_family, winner_weight = scored[0][1], scored[0][2]
            total += 1
            if winner_family == r["true_family"] and winner_weight == r["true_weight"]:
                correct += 1
        results[name] = {"correct": correct, "total": total, "accuracy": correct / total if total else 0.0}
    return results


# ---------------------------------------------------------------------------
# Confusion matrix + breakdowns (all against the CURRENT production formula)
# ---------------------------------------------------------------------------


def build_confusion_rows(records: list[dict]) -> list[dict]:
    rows = []
    for r in records:
        scored = sorted(r["candidates"], key=lambda c: c["current_score"], reverse=True)
        winner = scored[0]
        true_candidate = next(
            (c for c in r["candidates"] if c["family"] == r["true_family"] and c["weight"] == r["true_weight"]), None
        )
        rows.append(
            {
                "fixture": r["fixture"],
                "text": r["text"],
                "text_len": r["text_len"],
                "region_h": r["region_h"],
                "case": r["case"],
                "has_digit": r["has_digit"],
                "has_descender": r["has_descender"],
                "has_ascender": r["has_ascender"],
                "has_capital": r["has_capital"],
                "has_punctuation": r["has_punctuation"],
                "true": f"{r['true_family']}/{r['true_weight']}",
                "predicted": f"{winner['family']}/{winner['weight']}",
                "true_score": true_candidate["current_score"] if true_candidate else None,
                "winning_score": winner["current_score"],
                "margin": (winner["current_score"] - true_candidate["current_score"]) if true_candidate else None,
                "correct": true_candidate is not None and winner is true_candidate,
            }
        )
    return rows


def print_breakdown(rows: list[dict], key: str, label: str) -> None:
    buckets: dict = defaultdict(lambda: [0, 0])
    for row in rows:
        k = row[key]
        buckets[k][1] += 1
        if row["correct"]:
            buckets[k][0] += 1
    print(f"\n-- accuracy by {label} --")
    for k, (correct, total) in sorted(buckets.items(), key=lambda kv: str(kv[0])):
        print(f"  {str(k):20s} {correct:3d}/{total:3d} = {correct/total:.1%}")


def print_length_breakdown(rows: list[dict]) -> None:
    bins = [(0, 8), (8, 14), (14, 22), (22, 999)]
    buckets = {b: [0, 0] for b in bins}
    for row in rows:
        for lo, hi in bins:
            if lo <= row["text_len"] < hi:
                buckets[(lo, hi)][1] += 1
                if row["correct"]:
                    buckets[(lo, hi)][0] += 1
                break
    print("\n-- accuracy by text length --")
    for (lo, hi), (correct, total) in buckets.items():
        if total == 0:
            continue
        label = f"{lo}-{hi if hi < 999 else '+'}"
        print(f"  chars {label:8s} {correct:3d}/{total:3d} = {correct/total:.1%}")


def print_size_breakdown(rows: list[dict]) -> None:
    bins = [(0, 20), (20, 30), (30, 45), (45, 999)]
    buckets = {b: [0, 0] for b in bins}
    for row in rows:
        for lo, hi in bins:
            if lo <= row["region_h"] < hi:
                buckets[(lo, hi)][1] += 1
                if row["correct"]:
                    buckets[(lo, hi)][0] += 1
                break
    print("\n-- accuracy by region_h (font-size proxy, px) --")
    for (lo, hi), (correct, total) in buckets.items():
        if total == 0:
            continue
        label = f"{lo}-{hi if hi < 999 else '+'}"
        print(f"  region_h {label:9s} {correct:3d}/{total:3d} = {correct/total:.1%}")


def print_inter_400_600_deep_dive(records: list[dict]) -> None:
    print("\n=== Inter/400 vs Inter/600 deep dive ===")
    print("(regions where true=Inter/400 or true=Inter/600 — compare both candidates directly)")
    header = (
        f"{'text':30s} {'true':12s} {'400_iou':>8s} {'400_ssim':>9s} {'400_size':>9s} "
        f"{'600_iou':>8s} {'600_ssim':>9s} {'600_size':>9s} {'winner':>10s}"
    )
    print(header)
    for r in records:
        if r["true_family"] != "Inter" or r["true_weight"] not in (400, 600):
            continue
        c400 = next((c for c in r["candidates"] if c["family"] == "Inter" and c["weight"] == 400), None)
        c600 = next((c for c in r["candidates"] if c["family"] == "Inter" and c["weight"] == 600), None)
        if not c400 or not c600:
            continue
        winner = max(r["candidates"], key=lambda c: c["current_score"])
        print(
            f"{r['text'][:29]:30s} Inter/{r['true_weight']:<6d} "
            f"{c400['iou']:8.3f} {c400['ssim']:9.3f} {c400['size']:9.2f} "
            f"{c600['iou']:8.3f} {c600['ssim']:9.3f} {c600['size']:9.2f} "
            f"{winner['family']+'/'+str(winner['weight']):>10s}"
        )


def main() -> None:
    fixtures = sorted(set(f for f, _ in SYNTHETIC_GROUND_TRUTH))
    records: list[dict] = []

    for fixture in fixtures:
        path = os.path.join(TESTS_FIXTURES_DIR, fixture)
        image = Image.open(path).convert("RGB")
        image_bgr = np.array(image)[:, :, ::-1].copy()
        detect_result = detect(image_bgr)
        for line in detect_result.lines:
            key = (fixture, line.text)
            if key not in SYNTHETIC_GROUND_TRUTH:
                continue
            print(f"analyzing {fixture} / {line.text!r} ...", flush=True)
            record = analyze_region(fixture, line.text, image_bgr, line.bbox)
            if record:
                records.append(record)

    print(f"\n{len(records)} ground-truth-matched regions analyzed across {len(fixtures)} fixtures.")
    print(f"registry size: {len(FONT_REGISTRY)}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"wrote {OUT_PATH}")

    rows = build_confusion_rows(records)

    print("\n=== CONFUSION MATRIX (production 0.7*IoU+0.3*SSIM ranking) ===")
    print(f"{'text':32s} {'true':16s} {'predicted':16s} {'true_score':>10s} {'win_score':>10s} {'margin':>8s}")
    for row in rows:
        flag = "" if row["correct"] else "  <-- WRONG"
        ts = f"{row['true_score']:.3f}" if row["true_score"] is not None else "n/a"
        print(f"{row['text'][:31]:32s} {row['true']:16s} {row['predicted']:16s} {ts:>10s} {row['winning_score']:10.3f} {row['margin'] or 0:8.3f}{flag}")

    correct_count = sum(1 for r in rows if r["correct"])
    print(f"\nproduction-formula top-1 accuracy: {correct_count}/{len(rows)} = {correct_count/len(rows):.1%}")

    print_breakdown(rows, "true", "true family/weight (as string)")
    print_length_breakdown(rows)
    print_size_breakdown(rows)
    print_breakdown(rows, "case", "case (upper/lower/mixed/title)")
    for flag in ("has_digit", "has_descender", "has_ascender", "has_capital", "has_punctuation"):
        print_breakdown(rows, flag, flag)

    print("\n=== RANKING FORMULA COMPARISON (same converged geometry, re-ranked) ===")
    formula_results = evaluate_formulas(records)
    for name, res in sorted(formula_results.items(), key=lambda kv: -kv[1]["accuracy"]):
        marker = " <-- production" if name.startswith("current (") else ""
        print(f"  {name:35s} {res['correct']:3d}/{res['total']:3d} = {res['accuracy']:.1%}{marker}")

    print_inter_400_600_deep_dive(records)


if __name__ == "__main__":
    main()
