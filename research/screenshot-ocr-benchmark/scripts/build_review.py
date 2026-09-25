"""Build the human-review package for PILOT checks A3, A4, A5, B4 and E2.

Writes pilot/review/:
  index.html        local review page (open in a browser; nothing is uploaded)
  items.json        every review item (also embedded in index.html)
  crops/            one crop per A4 line (4 full sheets + >=10% random sample)
  gt_overlays/, variant_overlays/, engine_overlays/  (from validate_pilot.review_material)
  REVIEW_GUIDE.md   what to check and the pass criteria

Reviewer answers are exported from the page as CSV and ingested with
scripts/ingest_review.py. Run after validate_pilot.py (which draws the overlays).

    python scripts/build_review.py
"""

import json
import math
import os

import numpy as np
from PIL import Image

import bootstrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.join(ROOT, "pilot")
DATASET = os.path.join(PILOT, "dataset")
REVIEW = os.path.join(PILOT, "review")
FULL_SHEET_BASES = ["m01-settings_dpr3_light", "m05-chat_dpr3_dark", "d01-dashboard_dpr2_light",
                    "d06-code-editor_dpr2_dark"]
ENGINE_OVERLAY_IMAGES = ["m01-settings_dpr1_light_V00", "m05-chat_dpr3_dark_V00", "d01-dashboard_dpr1p5_light_V00",
                         "d06-code-editor_dpr2_dark_V00"]
ENGINES = ["tesseract5", "paddle_v5_mobile", "paddle_v5_server", "easyocr", "doctr", "windows_ocr"]


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def crop_line(src: Image.Image, box, out_path: str) -> None:
    x, y, w, h = box
    pad = max(4, int(h * 0.4))
    c = src.crop((max(0, x - pad), max(0, y - pad), min(src.width, x + w + pad), min(src.height, y + h + pad)))
    if c.height < 40:  # upscale tiny 1x text so a reviewer can read it (nearest: no invented detail)
        k = math.ceil(40 / max(1, c.height))
        c = c.resize((c.width * k, c.height * k), Image.NEAREST)
    c.save(out_path)


def main() -> None:
    gts = {n[:-5]: load_json(os.path.join(DATASET, "ground_truth", n))
           for n in sorted(os.listdir(os.path.join(DATASET, "ground_truth")))}
    os.makedirs(os.path.join(REVIEW, "crops"), exist_ok=True)
    items = []

    # A3 + A5 + B4 on base overlays (one judgement per question per base).
    for bid in gts:
        img = f"gt_overlays/{bid}.png"
        items.append({"id": f"A3:{bid}", "check": "A3", "image": img,
                      "question": "Every piece of visible text has a green ink box, and no box sits on something "
                                  "that is not text (icons excluded: orange)."})
        if any(ln["category"] == "paragraph" for ln in gts[bid]["lines"]):
            items.append({"id": f"A5:{bid}", "check": "A5", "image": img,
                          "question": "Each wrapped paragraph has exactly one box per visible line, and the boxes "
                                      "follow the line breaks you see."})
        items.append({"id": f"B4:{bid}", "check": "B4", "image": img,
                      "question": "Green (ink) boxes hug the letters with no visible offset or scale error; blue "
                                  "(layout) boxes contain them; any red box covers only clipped text."})
    for name in sorted(os.listdir(os.path.join(REVIEW, "variant_overlays"))):
        items.append({"id": f"B4:variant:{name[:-4]}", "check": "B4", "image": f"variant_overlays/{name}",
                      "question": "Green boxes sit on the text in this compressed/downscaled variant (50% variants "
                                  "use boxes measured on their own pixels)."})

    # A4: every line of 4 full sheets + a >=10% seeded random sample of all other lines.
    rng = np.random.default_rng(bootstrap.SEED)
    others = [(bid, ln) for bid, gt in gts.items() if bid not in FULL_SHEET_BASES for ln in gt["lines"]]
    sample_idx = sorted(rng.choice(len(others), size=math.ceil(0.10 * len(others)), replace=False))
    a4 = [(bid, ln, "full") for bid in FULL_SHEET_BASES for ln in gts[bid]["lines"]] + \
         [(others[i][0], others[i][1], "sample") for i in sample_idx]
    sources = {}
    for bid, ln, kind in a4:
        if bid not in sources:
            sources[bid] = Image.open(os.path.join(DATASET, "renders", f"{bid}.png")).convert("RGB")
        rel = f"crops/{bid}__{ln['line_id']}.png"
        crop_line(sources[bid], ln["ink_box"], os.path.join(REVIEW, rel))
        items.append({"id": f"A4:{bid}:{ln['line_id']}", "check": "A4", "image": rel, "gt_text": ln["text"],
                      "set": kind, "stress": ln["stress"],
                      "question": "The ground-truth text below matches the rendered text exactly "
                                  "(every character, spacing collapsed to single spaces)."})

    # E2: engine prediction overlays.
    for e in ENGINES:
        for image_id in ENGINE_OVERLAY_IMAGES:
            rel = f"engine_overlays/{e}__{image_id}.png"
            if os.path.exists(os.path.join(REVIEW, rel)):
                items.append({"id": f"E2:{e}:{image_id}", "check": "E2", "image": rel,
                              "question": f"{e}: magenta boxes sit on the text they cover (loose or tight is fine; "
                                          "a systematic shift or scale error is not)."})

    with open(os.path.join(REVIEW, "items.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, indent=1, ensure_ascii=False)
    with open(os.path.join(REVIEW, "index.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")))
    counts = {}
    for it in items:
        counts[it["check"]] = counts.get(it["check"], 0) + 1
    print(f"review items: {counts} (total {len(items)}) -> pilot/review/index.html")


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Pilot human review</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#fafafa;--card:#fff;--ink:#1a1a1a;--mute:#666;--line:#ddd;--ok:#16794a;--bad:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#121212;--card:#1d1d1d;--ink:#eee;--mute:#aaa;--line:#333}}
body{margin:0;font:15px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center;z-index:2}
main{max-width:1200px;margin:0 auto;padding:16px}
.item{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:0 0 14px}
.item.done{border-left:4px solid var(--ok)} .item.flag{border-left:4px solid var(--bad)}
.item img{max-width:100%;height:auto;border:1px solid var(--line);background:#fff}
.gt{font:15px/1.4 ui-monospace,monospace;background:var(--bg);padding:6px 8px;border-radius:4px;white-space:pre-wrap;word-break:break-word}
.q{color:var(--mute);margin:6px 0} .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button{font:inherit;padding:6px 12px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.sel-agree{background:var(--ok);color:#fff} button.sel-disagree{background:var(--bad);color:#fff}
input[type=text]{flex:1;min-width:200px;font:inherit;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
select{font:inherit;padding:4px}
</style></head><body>
<header>
 <strong>Pilot human review</strong>
 <label>Reviewer <input id="who" type="text" placeholder="your name" style="min-width:140px;flex:0"></label>
 <label>Show <select id="filter"><option value="">all</option><option>A3</option><option>A4</option><option>A5</option><option>B4</option><option>E2</option><option value="todo">unanswered</option><option value="flag">disagreements</option></select></label>
 <span id="progress"></span>
 <button id="export">Export CSV</button>
</header>
<main id="list"></main>
<script>
const ITEMS = __ITEMS__;
const KEY = "ocrb-pilot-review-v1";
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { state = {}; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} render(); }
function esc(s){ return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function render(){
  const f = document.getElementById("filter").value;
  const list = document.getElementById("list");
  let answered = 0;
  const html = [];
  for (const it of ITEMS) {
    const s = state[it.id] || {};
    if (s.verdict) answered++;
    if (f === "todo" && s.verdict) continue;
    if (f === "flag" && s.verdict !== "disagree") continue;
    if (f && f !== "todo" && f !== "flag" && it.check !== f) continue;
    html.push(`<div class="item ${s.verdict==="agree"?"done":s.verdict==="disagree"?"flag":""}" data-id="${esc(it.id)}">
      <div class="row"><strong>${esc(it.check)}</strong><span class="q">${esc(it.id)}${it.set?" · "+esc(it.set):""}${it.stress?" · stress line":""}</span></div>
      <p class="q">${esc(it.question)}</p>
      ${it.gt_text!==undefined?`<div class="gt">${esc(it.gt_text)}</div>`:""}
      <p><img loading="lazy" src="${esc(it.image)}" alt="${esc(it.id)}"></p>
      <div class="row">
        <button class="${s.verdict==="agree"?"sel-agree":""}" data-v="agree">Agree</button>
        <button class="${s.verdict==="disagree"?"sel-disagree":""}" data-v="disagree">Disagree</button>
        <input type="text" placeholder="note (required when disagreeing)" value="${esc(s.note||"")}">
      </div></div>`);
  }
  list.innerHTML = html.join("");
  document.getElementById("progress").textContent = `${answered} / ${ITEMS.length} answered`;
}
document.getElementById("list").addEventListener("click", e => {
  const b = e.target.closest("button[data-v]"); if (!b) return;
  const id = b.closest(".item").dataset.id;
  state[id] = Object.assign(state[id] || {}, {verdict: b.dataset.v, at: new Date().toISOString()});
  save();
});
document.getElementById("list").addEventListener("change", e => {
  if (e.target.type !== "text") return;
  const id = e.target.closest(".item").dataset.id;
  state[id] = Object.assign(state[id] || {}, {note: e.target.value});
  save();
});
document.getElementById("filter").addEventListener("change", render);
document.getElementById("export").addEventListener("click", () => {
  const who = document.getElementById("who").value.trim();
  if (!who) { alert("Enter your name first."); return; }
  const rows = [["item_id","check","verdict","note","reviewer","answered_at"]];
  for (const it of ITEMS) { const s = state[it.id] || {}; rows.push([it.id, it.check, s.verdict||"", s.note||"", who, s.at||""]); }
  const csv = rows.map(r => r.map(v => '"' + String(v).replace(/"/g,'""') + '"').join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"}));
  a.download = "review_" + who.replace(/\W+/g,"_") + ".csv";
  a.click();
});
render();
</script></body></html>
"""

if __name__ == "__main__":
    main()
