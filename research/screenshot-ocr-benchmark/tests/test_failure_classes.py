"""Amendment A3: engine errors are scored as empty predictions; Docker-confirmed
memory-budget kills (status resource_oom) are excluded from scoring and listed."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import score as S  # noqa: E402

META = {"base_id": "b", "template_id": "t", "form_factor": "mobile", "dpr": 1, "theme": "light", "variant": "V00",
        "format": "png", "quality": None, "downscale": 1.0, "width": 100, "height": 100, "bytes": 1, "bpp": 1.0,
        "source": "chromium", "ocr": True}


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def test_error_scored_empty_and_resource_oom_excluded(tmp_path):
    pilot = tmp_path / "pilot"
    ds = pilot / "dataset"
    rows = [{**META, "image_id": f"img{i}", "file": f"images/img{i}.png"} for i in range(3)]
    os.makedirs(ds, exist_ok=True)
    with open(ds / "manifest.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    _write(ds / "ground_truth" / "b.json", {
        "lines": [{"line_id": "L0001", "text": "Settings", "ink_box": [10, 10, 80, 20], "stress": False,
                   "category": "label", "xheight_px": 8.0, "contrast_ratio": 10.0}],
        "ignore_regions": [], "icon_regions": []})
    ok_line = [{"bbox": [10, 10, 80, 20], "text": "Settings", "confidence": None}]
    _write(pilot / "predictions" / "eng" / "img0.json", {"image_id": "img0", "status": "ok", "lines": ok_line})
    _write(pilot / "predictions" / "eng" / "img1.json", {"image_id": "img1", "status": "error", "lines": []})
    _write(pilot / "predictions" / "eng" / "img2.json",
           {"image_id": "img2", "status": "resource_oom", "lines": [], "peak_rss_mb": 24000.0})

    res = S.score_tree(str(pilot), str(pilot / "predictions"))
    scored = {im["image_id"]: im["status"] for im in res["images"]}
    assert scored == {"img0": "ok", "img1": "error"}          # resource_oom not scored
    assert [x["image_id"] for x in res["excluded_resource_oom"]] == ["img2"]
    agg = S.aggregate(res["units"], res["images"])
    assert agg["M1_cer_n1"] == 8 / 16                          # img0: 0/8, img1 (error -> empty): 8/8
