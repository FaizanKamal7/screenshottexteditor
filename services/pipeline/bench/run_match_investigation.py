import glob
import json
import os
import time

import numpy as np
from PIL import Image

from match_instrumented import COUNTERS, match_font_traced
from stages.detect import detect
from stages.match import match_font as match_font_production
from stages.separate import separate


def analyze_fixture(path: str) -> list[dict]:
    image = Image.open(path).convert("RGB")
    image_bgr = np.array(image)[:, :, ::-1].copy()
    detect_result = detect(image_bgr)
    fixture_name = os.path.basename(path)

    region_records = []
    for line in detect_result.lines:
        if not line.text.strip():
            continue

        separation = separate(image_bgr, line.bbox)

        # Verification: production's real match_font vs our traced copy must
        # produce bit-identical results, or the trace isn't trustworthy.
        COUNTERS.reset()
        t0 = time.perf_counter()
        real_result = match_font_production(line.text, separation.alpha, separation.alpha.shape, line.bbox[3])
        real_cpu_s = time.perf_counter() - t0

        COUNTERS.reset()
        t0 = time.perf_counter()
        traced_result, traces = match_font_traced(line.text, separation.alpha, separation.alpha.shape, line.bbox[3])
        traced_cpu_s = time.perf_counter() - t0

        identical = (
            real_result.family == traced_result.family
            and real_result.weight == traced_result.weight
            and abs(real_result.size - traced_result.size) < 1e-9
            and abs(real_result.letter_spacing - traced_result.letter_spacing) < 1e-9
            and abs(real_result.baseline_y - traced_result.baseline_y) < 1e-9
            and abs(real_result.x_offset - traced_result.x_offset) < 1e-9
            and abs(real_result.score - traced_result.score) < 1e-9
        )

        # Simulate "restart #1 only" (zero extra evaluations — pure
        # re-aggregation of data already computed above).
        restart1_only_scores = [(t.family, t.weight, t.restart_scores[0], t.restart_results[0]) for t in traces]
        restart1_winner = max(restart1_only_scores, key=lambda r: r[2])
        both_restarts_winner = (traced_result.family, traced_result.weight, traced_result.score)

        restart2_ever_better = any(len(t.restart_scores) > 1 and t.restart_scores[1] > t.restart_scores[0] for t in traces)
        restart2_changes_this_candidate_winner = [
            t.chosen_restart_index == 1 for t in traces
        ]
        restart2_changes_overall_winner = (restart1_winner[0], restart1_winner[1]) != (
            both_restarts_winner[0], both_restarts_winner[1]
        )
        # Does restart #1-only reproduce the EXACT final params (not just family/weight)?
        restart1_winner_params = restart1_winner[3]
        restart1_reproduces_exact = (
            not restart2_changes_overall_winner
            and abs(restart1_winner_params[0] - traced_result.size) < 1e-9
            and abs(restart1_winner_params[1] - traced_result.letter_spacing) < 1e-9
            and abs(restart1_winner_params[2] - traced_result.baseline_y) < 1e-9
            and abs(restart1_winner_params[3] - traced_result.x_offset) < 1e-9
        )

        # Coarse-grid ranking vs final ranking: would the coarse score alone
        # (restart 1's step-1 result, before any refine) pick the same winner?
        coarse_only = [(t.family, t.weight, t.coarse_best_scores[0]) for t in traces]
        coarse_winner = max(coarse_only, key=lambda r: r[2])
        coarse_predicts_final_winner = (coarse_winner[0], coarse_winner[1]) == (
            traced_result.family, traced_result.weight
        )

        region_records.append(
            {
                "fixture": fixture_name,
                "text": line.text,
                "region_h": line.bbox[3],
                "candidate_count": len(traces),
                "restart_count": len(traces[0].restart_scores) if traces else 0,
                "render_calls": COUNTERS.render_calls,
                "score_calls": COUNTERS.score_calls,
                "cache_hits": COUNTERS.cache_hits,
                "cache_misses": COUNTERS.cache_misses,
                "real_cpu_s": real_cpu_s,
                "traced_cpu_s": traced_cpu_s,
                "identical_to_production": identical,
                "final_family": traced_result.family,
                "final_weight": traced_result.weight,
                "final_score": traced_result.score,
                "restart2_ever_beats_restart1_for_some_candidate": restart2_ever_better,
                "restart2_changes_any_candidates_own_winner": any(restart2_changes_this_candidate_winner),
                "count_candidates_where_restart2_won": sum(restart2_changes_this_candidate_winner),
                "restart2_changes_overall_family_weight_winner": restart2_changes_overall_winner,
                "restart1_only_reproduces_exact_matchresult": restart1_reproduces_exact,
                "coarse_grid_predicts_final_winner": coarse_predicts_final_winner,
                "all_candidate_scores_both_restarts": [
                    {"family": t.family, "weight": t.weight, "restart_scores": t.restart_scores, "coarse_scores": t.coarse_best_scores}
                    for t in traces
                ],
            }
        )
    return region_records


def main():
    real_image = "/fixtures/real_18region.jpg"
    local_fixtures_dir = "/fixtures/local"
    patterns = ("*.png", "*.jpg", "*.jpeg")
    local_paths = sorted(p for pattern in patterns for p in glob.glob(os.path.join(local_fixtures_dir, pattern)))

    all_records = []
    print(f"=== real production image: {real_image} ===", flush=True)
    real_records = analyze_fixture(real_image)
    all_records.extend(real_records)
    for r in real_records:
        print(
            f"  {r['text']!r:40s} render={r['render_calls']:4d} score={r['score_calls']:4d} "
            f"hits={r['cache_hits']:3d} cpu={r['real_cpu_s']:.3f}s identical={r['identical_to_production']} "
            f"restart2_changes_overall={r['restart2_changes_overall_family_weight_winner']} "
            f"restart1_exact={r['restart1_only_reproduces_exact_matchresult']} "
            f"coarse_predicts={r['coarse_grid_predicts_final_winner']}"
        )

    print(f"\n=== local fixtures ({len(local_paths)}) ===", flush=True)
    for path in local_paths:
        recs = analyze_fixture(path)
        all_records.extend(recs)
        for r in recs:
            print(
                f"  {r['fixture']:24s} {r['text']!r:30s} render={r['render_calls']:4d} "
                f"identical={r['identical_to_production']} restart2_changes_overall={r['restart2_changes_overall_family_weight_winner']} "
                f"restart1_exact={r['restart1_only_reproduces_exact_matchresult']} coarse_predicts={r['coarse_grid_predicts_final_winner']}"
            )

    with open("/bench/match_investigation_results.json", "w", encoding="utf-8") as f:
        json.dump(all_records, f, indent=2)
    print(f"\nwrote {len(all_records)} region records to /bench/match_investigation_results.json")


if __name__ == "__main__":
    main()
