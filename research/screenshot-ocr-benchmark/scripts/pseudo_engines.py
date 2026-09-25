"""Pseudo-engines for scorer validation (PILOT_PLAN C2–C5). Written to pilot/pseudo/{name}/.

oracle     returns every ground-truth line (text + ink box, scaled for downscaled variants)
perturbed  oracle text with a seeded, known number of edits per line (C3)
empty      returns nothing (C4)
jitter     oracle with every box shifted by ±10% of its height in x and y (C5)

Perturbation design guarantees the injected count equals the true edit distance:
one edit type per image (all lines), applied to the N1 form of the text, never
touching or creating whitespace:
  substitute  k distinct non-space positions -> a symbol absent from every GT line
              of the image (each absent symbol needs its own edit: distance >= k)
  delete      k distinct non-space chars whose neighbours are both non-space
              (length drops by k: distance >= k)
  insert      k symbols into gaps between two non-space chars (distance >= k)
and each is achievable in k edits, so distance == k exactly.
"""

import hashlib
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import geometry_for, n1  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOLS = "#@%&*+=<>~^"
SEED = 20260924


def _rng(image_id: str, salt: str) -> random.Random:
    h = hashlib.sha256(f"{SEED}:{salt}:{image_id}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def perturb(text: str, kind: str, k: int, rng: random.Random, symbols: str) -> tuple[str, int]:
    s = list(text)
    if kind == "substitute":
        pos = [i for i, c in enumerate(s) if c != " "]
        pick = rng.sample(pos, min(k, len(pos)))
        for i in pick:
            s[i] = rng.choice(symbols)
        return "".join(s), len(pick)
    if kind == "delete":
        pos = [i for i in range(1, len(s) - 1) if s[i] != " " and s[i - 1] != " " and s[i + 1] != " "]
        pick = set(rng.sample(pos, min(k, len(pos))))
        return "".join(c for i, c in enumerate(s) if i not in pick), len(pick)
    if kind == "insert":
        gaps = [i for i in range(1, len(s)) if s[i - 1] != " " and s[i] != " "]
        pick = sorted(rng.sample(gaps, min(k, len(gaps))), reverse=True)
        for i in pick:
            s.insert(i, rng.choice(symbols))
        return "".join(s), len(pick)
    raise ValueError(kind)


def main() -> None:
    pilot = os.path.join(ROOT, "pilot")
    dataset = os.path.join(pilot, "dataset")
    with open(os.path.join(dataset, "manifest.jsonl"), encoding="utf-8") as f:
        rows = [r for r in map(json.loads, f) if r["ocr"]]
    gts = {}
    for name in ("oracle", "perturbed", "empty", "jitter"):
        os.makedirs(os.path.join(pilot, "pseudo", name), exist_ok=True)
    for row in rows:
        if row["base_id"] not in gts:
            with open(os.path.join(dataset, "ground_truth", f"{row['base_id']}.json"), encoding="utf-8") as f:
                gts[row["base_id"]] = json.load(f)
        gt = gts[row["base_id"]]
        _, _, box_of = geometry_for(gt, row["downscale"])
        oracle = [{"bbox": box_of(ln), "text": ln["text"], "confidence": None} for ln in gt["lines"]]

        rng = _rng(row["image_id"], "perturb")
        kind = rng.choice(["substitute", "delete", "insert"])
        present = set("".join(n1(ln["text"]) for ln in gt["lines"]))
        symbols = "".join(c for c in SYMBOLS if c not in present)
        assert symbols, "no absent symbol available"
        perturbed, injected = [], []
        for ln, o in zip(gt["lines"], oracle):
            if ln["stress"]:
                perturbed.append(o)
                continue
            k_target = rng.randint(0, 3)
            text, k = perturb(n1(ln["text"]), kind, k_target, rng, symbols)
            perturbed.append({**o, "text": text})
            injected.append({"line_id": ln["line_id"], "k": k})

        jrng = _rng(row["image_id"], "jitter")
        jitter = []
        for o in oracle:
            x, y, w, h = o["bbox"]
            dx = 0.10 * h * jrng.choice([-1, 1])
            dy = 0.10 * h * jrng.choice([-1, 1])
            jitter.append({**o, "bbox": [x + dx, y + dy, w, h]})

        for name, lines, extra in (("oracle", oracle, {}), ("perturbed", perturbed,
                                   {"perturbation": {"kind": kind, "injected": injected}}),
                                   ("empty", [], {}), ("jitter", jitter, {})):
            rec = {"engine_id": name, "image_id": row["image_id"], "status": "ok", "error": None, "total_s": None,
                   "lines": lines, **extra}
            with open(os.path.join(pilot, "pseudo", name, f"{row['image_id']}.json"), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False)
    print(f"pseudo predictions written for {len(rows)} images")


if __name__ == "__main__":
    main()
