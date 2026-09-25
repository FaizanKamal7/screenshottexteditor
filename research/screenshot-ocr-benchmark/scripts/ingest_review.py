"""Turn exported reviewer CSV(s) into PILOT check results for A3, A4, A5, B4, E2.

    python scripts/ingest_review.py pilot/review/completed/review_*.csv

Rules (PILOT_PLAN §3; pass criteria are unchanged, this only records them):
- An item passes when every reviewer who answered it chose "agree".
- A check passes when every one of its items has at least one answer and all pass.
- Any "disagree" without a note is rejected: the reviewer must say what is wrong.
- A4 is zero tolerance: one disagreement fails A4 and is a generator bug to fix.
Writes pilot/validation/human_review.json (read by validate_pilot.py).
"""

import csv
import json
import os
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.join(ROOT, "pilot")


def main(paths: list[str]) -> None:
    with open(os.path.join(PILOT, "review", "items.json"), encoding="utf-8") as f:
        items = {it["id"]: it for it in json.load(f)}
    answers = defaultdict(list)
    reviewers = set()
    problems = []
    for path in paths:
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["item_id"] not in items:
                    problems.append(f"unknown item {row['item_id']} in {path}")
                    continue
                if not row["verdict"]:
                    continue
                if row["verdict"] == "disagree" and not row["note"].strip():
                    problems.append(f"disagree without note: {row['item_id']} ({row['reviewer']})")
                answers[row["item_id"]].append(row)
                reviewers.add(row["reviewer"])
    per_check = defaultdict(lambda: {"items": 0, "answered": 0, "disagreements": []})
    for item_id, it in items.items():
        c = per_check[it["check"]]
        c["items"] += 1
        rows = answers.get(item_id, [])
        if rows:
            c["answered"] += 1
        for r in rows:
            if r["verdict"] == "disagree":
                c["disagreements"].append({"item": item_id, "reviewer": r["reviewer"], "note": r["note"]})
    result = {}
    for check, c in sorted(per_check.items()):
        if c["answered"] < c["items"]:
            status = f"INCOMPLETE ({c['answered']}/{c['items']} answered)"
        elif c["disagreements"]:
            status = "FAIL"
        else:
            status = "PASS"
        result[check] = {"status": status, **c}
    out = {"reviewers": sorted(reviewers), "files": paths, "input_problems": problems, "checks": result}
    with open(os.path.join(PILOT, "validation", "human_review.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    for check, r in result.items():
        print(f"{check}: {r['status']}  ({len(r['disagreements'])} disagreements)")
    for p in problems:
        print("PROBLEM:", p)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python scripts/ingest_review.py <review_*.csv> [...]")
    main(sys.argv[1:])
