"""Scoring (PREREGISTRATION §4–6). Pure functions + a CLI that scores a predictions tree.

Normalization N0/N1/N2/no-whitespace, component matching (τ_c), one-to-one IoU
detection matching, and metrics M1–M9. Edit distance: rapidfuzz (MIT).

Interpretations the preregistration leaves implicit (recorded in the pilot report):
- Stress lines are excluded from headline metrics by treating their ink boxes
  like ignore regions (predictions mostly over them are dropped), so a correct
  reading of a stress line is not scored as an insertion. They are included in
  the RQ9 confusion pass.
- Reading-order rows: a box joins the current row when its vertical centre is
  within half the smaller box height of the row's *first* box.
- A prediction whose box has zero area is kept unless its centre lies inside an
  ignore region.

    python scripts/score.py --pilot pilot --pred-dir predictions --out scores
"""

import argparse
import csv
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict

from rapidfuzz.distance import Levenshtein

# ---------------------------------------------------------------------------
# Normalization (PREREGISTRATION §4)
# ---------------------------------------------------------------------------

_DELETE = dict.fromkeys(map(ord, "​‌‍⁠﻿­"))
_MAP = {}
for ch in "‘’‚‛′":
    _MAP[ord(ch)] = "'"
for ch in "“”„‟″":
    _MAP[ord(ch)] = '"'
for cp in list(range(0x2010, 0x2016)) + [0x2212]:
    _MAP[cp] = "-"
_WS = re.compile(r"\s+")


def n0(s: str) -> str:
    return s


def n1(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_DELETE)
    s = s.translate(_MAP)
    s = "".join(" " if (unicodedata.category(c) == "Zs" or c == "\t") else c for c in s)
    return _WS.sub(" ", s).strip()


def n2(s: str) -> str:
    return n1(s).casefold()


def nows(s: str) -> str:
    return n1(s).replace(" ", "")


def tokens(s_n1: str) -> list[str]:
    return s_n1.split(" ") if s_n1 else []


def is_numeric_token(tok: str) -> bool:
    return any("0" <= c <= "9" for c in tok)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def area(b) -> float:
    return max(0.0, b[2]) * max(0.0, b[3])


def intersection(a, b) -> float:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def iou(a, b) -> float:
    inter = intersection(a, b)
    union = area(a) + area(b) - inter
    return inter / union if union > 0 else 0.0


def overlap_min(a, b) -> float:
    m = min(area(a), area(b))
    return intersection(a, b) / m if m > 0 else 0.0


def union_area_within(box, rects) -> float:
    """Area of box ∩ (∪ rects), by coordinate compression (exact)."""
    clipped = []
    for r in rects:
        x0, y0 = max(box[0], r[0]), max(box[1], r[1])
        x1, y1 = min(box[0] + box[2], r[0] + r[2]), min(box[1] + box[3], r[1] + r[3])
        if x1 > x0 and y1 > y0:
            clipped.append((x0, y0, x1, y1))
    if not clipped:
        return 0.0
    xs = sorted({v for c in clipped for v in (c[0], c[2])})
    ys = sorted({v for c in clipped for v in (c[1], c[3])})
    total = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if any(c[0] <= cx < c[2] and c[1] <= cy < c[3] for c in clipped):
                total += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return total


def fraction_in_regions(box, regions) -> float:
    a = area(box)
    if a == 0:
        cx, cy = box[0] + box[2] / 2, box[1] + box[3] / 2
        return 1.0 if any(r[0] <= cx <= r[0] + r[2] and r[1] <= cy <= r[1] + r[3] for r in regions) else 0.0
    return union_area_within(box, regions) / a


def reading_order(items: list[dict]) -> list[dict]:
    """Sort by vertical centre; a box joins the current row if its centre is within
    half the smaller height of the row's first box; rows ordered by left edge."""
    ordered = sorted(items, key=lambda it: (it["box"][1] + it["box"][3] / 2, it["box"][0]))
    rows: list[list[dict]] = []
    for it in ordered:
        cy, h = it["box"][1] + it["box"][3] / 2, it["box"][3]
        if rows:
            first = rows[-1][0]
            fcy, fh = first["box"][1] + first["box"][3] / 2, first["box"][3]
            if abs(cy - fcy) < 0.5 * min(h, fh):
                rows[-1].append(it)
                continue
        rows.append([it])
    return [it for row in rows for it in sorted(row, key=lambda it: it["box"][0])]


def greedy_iou_match(gt_boxes, pred_boxes, threshold: float) -> list[tuple[int, int, float]]:
    """One-to-one greedy by descending IoU (as services/pipeline/bench `_match_lines`)."""
    pairs = []
    for gi, g in enumerate(gt_boxes):
        for pi, p in enumerate(pred_boxes):
            v = iou(g, p)
            if v >= threshold:
                pairs.append((v, gi, pi))
    pairs.sort(key=lambda t: (-t[0], t[1], t[2]))
    used_g, used_p, out = set(), set(), []
    for v, gi, pi in pairs:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        out.append((gi, pi, v))
    return out


# ---------------------------------------------------------------------------
# Image scoring
# ---------------------------------------------------------------------------


def scale_box(b, s):
    return [b[0] * s, b[1] * s, b[2] * s, b[3] * s]


def geometry_for(gt: dict, downscale: float):
    """(ignore regions, icon regions, line -> ink box) for an image's resolution."""
    if downscale == 1.0:
        return list(gt["ignore_regions"]), list(gt.get("icon_regions", [])), lambda ln: list(ln["ink_box"])
    if downscale == 0.5 and "downscaled_0p5" in gt:
        d = gt["downscaled_0p5"]
        return list(d["ignore_regions"]), list(d["icon_regions"]), lambda ln: list(ln["ink_box_half"])
    raise ValueError(f"no measured ground-truth geometry for downscale={downscale} (run scripts/downscaled_gt.py)")


def score_image(gt: dict, pred_lines: list[dict], downscale: float = 1.0, tau: float = 0.5,
                include_stress: bool = False, det_thresholds=(0.5, 0.3, 0.7)) -> dict:
    """Score one image. Returns units (scoring units), per-GT-line rows and image metrics.

    For 50% variants the ground-truth boxes are the ones measured on the downscaled
    renders (scripts/downscaled_gt.py, PREREGISTRATION amendment A2), not 0.5 × the
    full-resolution boxes."""
    ignore, icons, box_of = geometry_for(gt, downscale)
    gts = []
    for ln in gt["lines"]:
        box = box_of(ln)
        if ln["stress"] and not include_stress:
            ignore.append(box)
            continue
        gts.append({"id": ln["line_id"], "text": ln["text"], "box": box, "line": ln})

    preds = []
    dropped_empty = dropped_ignore = 0
    for i, p in enumerate(pred_lines):
        text = p["text"]
        if not n1(text):
            dropped_empty += 1
            continue
        box = list(p["bbox"])
        if ignore and fraction_in_regions(box, ignore) >= 0.5:
            dropped_ignore += 1
            continue
        preds.append({"idx": i, "text": text, "box": box,
                      "icon": bool(icons) and fraction_in_regions(box, icons) >= 0.5})

    # Components (union-find over GT + predictions).
    n_g = len(gts)
    parent = list(range(n_g + len(preds)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for gi, g in enumerate(gts):
        for pi, p in enumerate(preds):
            if overlap_min(g["box"], p["box"]) >= tau:
                ra, rb = find(gi), find(n_g + pi)
                if ra != rb:
                    parent[rb] = ra
    groups: dict[int, dict] = defaultdict(lambda: {"g": [], "p": []})
    for gi in range(n_g):
        groups[find(gi)]["g"].append(gts[gi])
    for pi in range(len(preds)):
        groups[find(n_g + pi)]["p"].append(preds[pi])

    units = []
    for comp in sorted(groups.values(), key=lambda c: (c["g"][0]["id"] if c["g"] else "~", c["p"][0]["idx"] if c["p"] else -1)):
        g_sorted = reading_order(comp["g"])
        p_sorted = reading_order(comp["p"])
        ref_raw = " ".join(g["text"] for g in g_sorted)
        hyp_raw = " ".join(p["text"] for p in p_sorted)
        kind = "component" if g_sorted and p_sorted else ("deletion" if g_sorted else "insertion")
        units.append(make_unit(kind, [g["id"] for g in g_sorted], [p["idx"] for p in p_sorted], ref_raw, hyp_raw,
                               icon=(kind == "insertion" and all(p["icon"] for p in p_sorted))))

    # Detection (M8), one-to-one IoU.
    det = {}
    for th in det_thresholds:
        m = greedy_iou_match([g["box"] for g in gts], [p["box"] for p in preds], th)
        det[f"{th:.1f}"] = {"matched": len(m), "n_gt": len(gts), "n_pred": len(preds)}
    m50 = {gi: v for gi, _, v in greedy_iou_match([g["box"] for g in gts], [p["box"] for p in preds], 0.5)}
    best_iou = {gi: max((iou(g["box"], p["box"]) for p in preds), default=0.0) for gi, g in enumerate(gts)}

    # Bag of words (M9).
    ref_bag = Counter(t for g in gts for t in tokens(n1(g["text"])))
    hyp_bag = Counter(t for p in preds for t in tokens(n1(p["text"])))
    inter = sum((ref_bag & hyp_bag).values())
    nr, nh = sum(ref_bag.values()), sum(hyp_bag.values())
    if nr == 0 and nh == 0:
        bow_f1 = 1.0
    else:
        prec = inter / nh if nh else 0.0
        rec = inter / nr if nr else 0.0
        bow_f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    # Per-GT-line rows.
    unit_of = {}
    for ui, u in enumerate(units):
        for gid in u["gt_ids"]:
            unit_of[gid] = ui
    line_rows = []
    for gi, g in enumerate(gts):
        u = units[unit_of[g["id"]]]
        line_rows.append({
            "line_id": g["id"], "component_id": unit_of[g["id"]], "component_gt_count": len(u["gt_ids"]),
            "component_pred_count": len(u["pred_idx"]), "detected_iou50": gi in m50,
            "iou": round(best_iou[gi], 6), "ref_text": u["ref_n0"], "hyp_text": u["hyp_n0"],
            "cer_n0": u["cer_n0"], "cer_n1": u["cer_n1"], "cer_n2": u["cer_n2"], "cer_nows": u["cer_nows"],
            "wer": u["wer"], "exact_n1": u["exact_n1"], "numeric_tokens": u["numeric_total"],
            "numeric_correct": u["numeric_correct"], "category": g["line"]["category"],
            "xheight_px": (g["line"]["xheight_px"] or 0) * downscale, "contrast_ratio": g["line"]["contrast_ratio"],
            "stress": g["line"]["stress"],
        })

    return {"units": units, "lines": line_rows, "detection": det, "bow_f1": bow_f1,
            "n_pred_kept": len(preds), "dropped_empty": dropped_empty, "dropped_ignore": dropped_ignore}


def _cer(ed: int, n: int):
    return round(ed / n, 6) if n else None


def make_unit(kind: str, gt_ids: list, pred_idx: list, ref_raw: str, hyp_raw: str, icon: bool = False) -> dict:
    r1, h1 = n1(ref_raw), n1(hyp_raw)
    r2, h2 = r1.casefold(), h1.casefold()
    rw, hw = r1.replace(" ", ""), h1.replace(" ", "")
    rt, ht = tokens(r1), tokens(h1)
    ed0 = Levenshtein.distance(ref_raw, hyp_raw)
    ed1 = Levenshtein.distance(r1, h1)
    ed2 = Levenshtein.distance(r2, h2)
    edw = Levenshtein.distance(rw, hw)
    edt = Levenshtein.distance(rt, ht)
    hyp_bag = Counter(ht)
    num_total = num_correct = 0
    for t in rt:
        if is_numeric_token(t):
            num_total += 1
            if hyp_bag[t] > 0:
                hyp_bag[t] -= 1
                num_correct += 1
    return {
        "kind": kind, "gt_ids": gt_ids, "pred_idx": pred_idx, "n_gt": len(gt_ids), "icon_insertion": icon,
        "ref_n0": ref_raw, "hyp_n0": hyp_raw, "ref_n1": r1, "hyp_n1": h1,
        "ed_n0": ed0, "len_n0": len(ref_raw), "ed_n1": ed1, "len_n1": len(r1), "ed_n2": ed2, "len_n2": len(r2),
        "ed_nows": edw, "len_nows": len(rw), "ed_w": edt, "len_w": len(rt),
        "cer_n0": _cer(ed0, len(ref_raw)), "cer_n1": _cer(ed1, len(r1)), "cer_n2": _cer(ed2, len(r2)),
        "cer_nows": _cer(edw, len(rw)), "wer": _cer(edt, len(rt)),
        "exact_n1": bool(gt_ids) and r1 == h1,
        "numeric_total": num_total, "numeric_correct": num_correct,
    }


def confusions(gt: dict, pred_lines: list[dict], downscale: float = 1.0, tau: float = 0.5) -> Counter:
    """RQ9: substitution pairs from single-GT-line components under N1 (stress included)."""
    res = score_image(gt, pred_lines, downscale, tau, include_stress=True, det_thresholds=())
    out = Counter()
    for u in res["units"]:
        if u["kind"] == "component" and u["n_gt"] == 1:
            for op in Levenshtein.editops(u["ref_n1"], u["hyp_n1"]):
                if op.tag == "replace":
                    out[(u["ref_n1"][op.src_pos], u["hyp_n1"][op.dest_pos])] += 1
    return out


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def aggregate(units: list[dict], images: list[dict]) -> dict:
    """Cell metrics from pooled units (micro) and per-image rows."""
    def ratio(num, den):
        return num / den if den else None

    s = defaultdict(int)
    gt_lines = exact_lines = 0
    for u in units:
        for k in ("ed_n0", "len_n0", "ed_n1", "len_n1", "ed_n2", "len_n2", "ed_nows", "len_nows", "ed_w", "len_w",
                  "numeric_total", "numeric_correct"):
            s[k] += u[k]
        if not u["icon_insertion"]:
            s["ed_n1_noicon"] += u["ed_n1"]
            s["len_n1_noicon"] += u["len_n1"]
        if u["n_gt"]:
            gt_lines += u["n_gt"]
            if u["exact_n1"]:
                exact_lines += u["n_gt"]
    det = defaultdict(lambda: defaultdict(int))
    for im in images:
        for th, d in im["detection"].items():
            for k, v in d.items():
                det[th][k] += v
    det_out = {}
    for th, d in det.items():
        p = ratio(d["matched"], d["n_pred"])
        r = ratio(d["matched"], d["n_gt"])
        f = 2 * p * r / (p + r) if p and r else 0.0
        det_out[th] = {"precision": p, "recall": r, "f1": f}
    return {
        "M1_cer_n1": ratio(s["ed_n1"], s["len_n1"]),
        "M2_cer_n0": ratio(s["ed_n0"], s["len_n0"]),
        "M3_cer_n2": ratio(s["ed_n2"], s["len_n2"]),
        "M4_cer_nows": ratio(s["ed_nows"], s["len_nows"]),
        "M5_wer": ratio(s["ed_w"], s["len_w"]),
        "M6_line_exact": ratio(exact_lines, gt_lines),
        "M7_numeric_acc": ratio(s["numeric_correct"], s["numeric_total"]),
        "M8_detection": det_out,
        "M9_bow_f1": sum(im["bow_f1"] for im in images) / len(images) if images else None,
        "M1_cer_n1_no_icon_insertions": ratio(s["ed_n1_noicon"], s["len_n1_noicon"]),
        "n_images": len(images), "n_units": len(units), "n_gt_lines": gt_lines,
        "ref_chars_n1": s["len_n1"], "edits_n1": s["ed_n1"],
    }


# ---------------------------------------------------------------------------
# CLI: score a predictions tree
# ---------------------------------------------------------------------------

IMAGE_META = ["image_id", "base_id", "template_id", "form_factor", "dpr", "theme", "variant", "format", "quality",
              "downscale", "width", "height", "bytes", "bpp", "source"]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score_tree(pilot: str, pred_dir: str, tau: float = 0.5) -> dict:
    dataset = os.path.join(pilot, "dataset")
    with open(os.path.join(dataset, "manifest.jsonl"), encoding="utf-8") as f:
        manifest = {r["image_id"]: r for r in map(json.loads, f)}
    gts = {}
    unit_rows, line_rows, image_rows, conf_rows, excluded = [], [], [], [], []
    engines = sorted(d for d in os.listdir(pred_dir) if os.path.isdir(os.path.join(pred_dir, d)))
    for engine in engines:
        conf = Counter()
        for name in sorted(os.listdir(os.path.join(pred_dir, engine))):
            pred = load_json(os.path.join(pred_dir, engine, name))
            row = manifest[pred["image_id"]]
            if row["base_id"] not in gts:
                gts[row["base_id"]] = load_json(os.path.join(dataset, "ground_truth", f"{row['base_id']}.json"))
            gt = gts[row["base_id"]]
            meta = {k: row[k] for k in IMAGE_META}
            meta["engine_id"] = engine
            if pred["status"] == "resource_oom":
                # Amendment A3: a Docker-confirmed kill at the declared memory budget is not
                # an accuracy result; it is excluded from scoring and reported separately.
                excluded.append({**meta, "status": pred["status"], "peak_rss_mb": pred.get("peak_rss_mb")})
                continue
            lines = pred["lines"] if pred["status"] == "ok" else []  # §8.3: engine failure = empty prediction
            res = score_image(gt, lines, row["downscale"], tau)
            image_rows.append({**meta, "status": pred["status"], "bow_f1": res["bow_f1"],
                               "detection": res["detection"], "n_pred_kept": res["n_pred_kept"],
                               "dropped_empty": res["dropped_empty"], "dropped_ignore": res["dropped_ignore"],
                               "total_s": pred.get("total_s"),
                               "input_file_sha256_ok": pred.get("input_file_sha256_ok"),
                               "input_pixel_sha256_ok": pred.get("input_pixel_sha256_ok")})
            for ui, u in enumerate(res["units"]):
                unit_rows.append({**meta, "unit_id": ui, **{k: v for k, v in u.items()
                                                             if k not in ("gt_ids", "pred_idx")},
                                  "gt_ids": "|".join(u["gt_ids"]), "pred_idx": "|".join(map(str, u["pred_idx"]))})
            for lr in res["lines"]:
                line_rows.append({**meta, **lr})
            if row["variant"] == "V00" and pred["status"] == "ok":
                conf += confusions(gt, lines, row["downscale"], tau)
        for (a, b), n in conf.most_common(20):
            conf_rows.append({"engine_id": engine, "ref_char": a, "hyp_char": b, "count": n})
    return {"units": unit_rows, "lines": line_rows, "images": image_rows, "confusions": conf_rows,
            "excluded_resource_oom": excluded}


def write_csv(path: str, rows: list[dict]) -> None:
    if not rows:
        open(path, "w").close()
        return
    fields = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v) for k, v in r.items()})


def summarize(result: dict) -> dict:
    """Cells: engine × {overall V00, each variant, theme@V00, dpr@V00, form factor@V00}."""
    by = defaultdict(lambda: {"units": [], "images": []})
    for u in result["units"]:
        e = u["engine_id"]
        by[(e, "variant", u["variant"])]["units"].append(u)
        if u["variant"] == "V00":
            by[(e, "theme@V00", u["theme"])]["units"].append(u)
            by[(e, "dpr@V00", f"{u['form_factor']}:{u['dpr']}")]["units"].append(u)
    for im in result["images"]:
        e = im["engine_id"]
        by[(e, "variant", im["variant"])]["images"].append(im)
        if im["variant"] == "V00":
            by[(e, "theme@V00", im["theme"])]["images"].append(im)
            by[(e, "dpr@V00", f"{im['form_factor']}:{im['dpr']}")]["images"].append(im)
    cells = []
    for (e, dim, level), d in sorted(by.items()):
        agg = aggregate(d["units"], d["images"])
        fails = sum(1 for im in d["images"] if im["status"] != "ok")
        cells.append({"engine_id": e, "dimension": dim, "level": level, **agg, "engine_failures": fails})
    excl = defaultdict(int)
    for x in result.get("excluded_resource_oom", []):
        excl[x["engine_id"]] += 1
    return {"note": "PILOT — engineering validation only. Not a benchmark result; not for publication.",
            "cells": cells, "excluded_resource_oom_by_engine": dict(excl)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", default="pilot")
    parser.add_argument("--pred-dir", default="predictions")
    parser.add_argument("--out", default="scores")
    parser.add_argument("--tau", type=float, default=0.5)
    args = parser.parse_args()
    pred_dir = os.path.join(args.pilot, args.pred_dir)
    out = os.path.join(args.pilot, args.out)
    result = score_tree(args.pilot, pred_dir, args.tau)
    write_outputs(result, out)
    print(f"scored {len(result['images'])} predictions -> {out}")


def write_outputs(result: dict, out: str) -> None:
    os.makedirs(out, exist_ok=True)
    write_csv(os.path.join(out, "units.csv"), result["units"])
    write_csv(os.path.join(out, "line_scores.csv"), result["lines"])
    write_csv(os.path.join(out, "image_scores.csv"), result["images"])
    write_csv(os.path.join(out, "confusions.csv"), result["confusions"])
    write_csv(os.path.join(out, "excluded_resource_oom.csv"), result["excluded_resource_oom"])
    summary = summarize(result)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True)
    flat = [{k: (json.dumps(v, sort_keys=True) if isinstance(v, dict) else v) for k, v in c.items()}
            for c in summary["cells"]]
    write_csv(os.path.join(out, "summary.csv"), flat)
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        for name in ("units", "line_scores"):
            rows = result["units"] if name == "units" else result["lines"]
            if rows:
                table = pa.Table.from_pylist([{k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                                               for k, v in r.items()} for r in rows])
                pq.write_table(table, os.path.join(out, f"{name}.parquet"))
    except ImportError:
        pass


if __name__ == "__main__":
    main()
