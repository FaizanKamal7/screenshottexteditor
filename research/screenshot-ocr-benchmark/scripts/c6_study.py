"""PILOT C6 remediation: coverage of candidate interval methods on synthetic populations
with known truth, then apply bootstrap.SELECTION_RULE (fixed before this ran).

    python scripts/c6_study.py            # 20 templates/stratum (the decision)
    python scripts/c6_study.py --n 40     # sensitivity only
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bootstrap as B  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--sims", type=int, default=2000)
    parser.add_argument("--round2", action="store_true")
    args = parser.parse_args()
    t0 = time.time()
    if args.round2:
        study = B.coverage_study_r2(n_per_stratum=args.n, sims=args.sims)
        study["elapsed_s"] = round(time.time() - t0, 1)
        out = os.path.join(ROOT, "pilot", "validation", f"c6_study_round2_n{args.n}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(study, f, indent=1)
        for name, r in study["results"].items():
            cells = "  ".join(f"{k}={v:.3f}" for k, v in r.items() if isinstance(v, float))
            print(f"{'[held-out] ' if r['held_out'] else ''}{name}: {cells}  undefined_rel={r['undefined_relative']}")
        print("passes all 8 scenarios:", json.dumps(study["passes_all_scenarios"]))
        print(f"elapsed {study['elapsed_s']} s -> {out}")
        return
    study = B.coverage_study(n_per_stratum=args.n, sims=args.sims)
    study["decision"] = B.choose_method(study)
    study["elapsed_s"] = round(time.time() - t0, 1)
    out = os.path.join(ROOT, "pilot", "validation", f"c6_study_n{args.n}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(study, f, indent=1)
    for name, r in study["results"].items():
        cells = "  ".join(f"{k}={v['coverage']:.3f}" for k, v in r.items() if isinstance(v, dict))
        print(f"{name}: {cells}")
    print("decision:", json.dumps(study["decision"], indent=1))
    print(f"elapsed {study['elapsed_s']} s -> {out}")


if __name__ == "__main__":
    main()
