"""Render templates in headless Chromium and build exact ground truth (METHODOLOGY §4).

For each (template, device scale factor, theme):
  1. render A (fresh browser context) -> screenshot + DOM geometry (extract.js)
  2. CDP CSS.getPlatformFontsForNode on every element owning text -> fallback check
  3. text-hidden render in the same page (color: transparent) -> ink = A != hidden
  4. render B (second fresh context) -> determinism check (pixels + geometry)
  5. ground_truth/{base_id}.json, renders/{base_id}.png, masks/{base_id}.png,
     internal/{base_id}_hidden.png, validation/render_{base_id}.json

Run inside the tools image:
    python scripts/render_chromium.py --out pilot/dataset
"""

import argparse
import functools
import hashlib
import http.server
import io
import json
import math
import os
import sys
import threading
from collections import Counter

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEMPLATES = {
    "m01-settings": "mobile",
    "m05-chat": "mobile",
    "d01-dashboard": "desktop",
    "d06-code-editor": "desktop",
}
VIEWPORT = {"mobile": (390, 844), "desktop": (1280, 800)}
DPRS = {"mobile": [1, 2, 3], "desktop": [1, 1.5, 2]}
THEMES = ["light", "dark"]
INK_PAD = 2  # image px (METHODOLOGY §4.4)
# Fonts whose default contextual/programming ligatures change glyph identity
# (e.g. "=>" drawn as one arrow). Elements using them must set
# font-variant-ligatures: none, or rendered text would differ from DOM text.
LIGATURE_FONTS = {"JetBrains Mono"}

MARK_TEXT_OWNERS_JS = """
() => {
  const owners = [];
  const seen = new Set();
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    if (!n.data.trim()) continue;
    const el = n.parentElement;
    if (!el || seen.has(el)) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    if (!Array.from(r.getClientRects()).some((x) => x.width > 0 && x.height > 0)) continue;
    seen.add(el);
  }
  const all = Array.from(document.querySelectorAll("*")).filter((el) => seen.has(el));
  all.forEach((el, i) => {
    el.setAttribute("data-ocrb-owner", String(i));
    const cs = getComputedStyle(el);
    owners.push({ i, family: cs.fontFamily.split(",")[0].trim().replace(/^["']|["']$/g, ""),
                  weight: parseInt(cs.fontWeight, 10), style: cs.fontStyle, text: el.textContent.trim().slice(0, 40) });
  });
  return owners;
}
"""


def dpr_label(dpr: float) -> str:
    return str(dpr).replace(".", "p").removesuffix("p0")


def base_id(template: str, dpr: float, theme: str) -> str:
    return f"{template}_dpr{dpr_label(dpr)}_{theme}"


@functools.lru_cache(maxsize=None)
def font_table() -> dict:
    """(family, weight) -> {file, postscript, xheight_ratio, capheight_ratio}."""
    with open(os.path.join(ROOT, "fonts", "fonts.lock.json"), encoding="utf-8") as f:
        lock = json.load(f)
    table = {}
    for entry in lock["fonts"]:
        tt = TTFont(os.path.join(ROOT, "fonts", entry["file"]))
        upm = tt["head"].unitsPerEm
        os2 = tt["OS/2"]
        table[(entry["family"], entry["weight"])] = {
            "file": entry["file"],
            "postscript": tt["name"].getDebugName(6),
            "xheight_ratio": os2.sxHeight / upm,
            "capheight_ratio": os2.sCapHeight / upm,
        }
    return table


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D401 - silence per-request logging
        pass


def start_server() -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(_QuietHandler, directory=ROOT)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def _settle(page) -> list:
    page.evaluate("() => document.fonts.ready.then(() => true)")
    errors = page.evaluate("() => Array.from(document.fonts).filter(f => f.status === 'error').map(f => f.family)")
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    return errors


def _new_page(browser, form_factor: str, dpr: float, theme: str):
    w, h = VIEWPORT[form_factor]
    context = browser.new_context(
        viewport={"width": w, "height": h},
        device_scale_factor=dpr,
        color_scheme=theme,
        locale="en-US",
        timezone_id="UTC",
        reduced_motion="reduce",
    )
    return context, context.new_page()


def _png_array(png: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(png)) as im:
        return np.asarray(im.convert("RGB")).copy()


def font_check(context, page) -> dict:
    owners = page.evaluate(MARK_TEXT_OWNERS_JS)
    cdp = context.new_cdp_session(page)
    cdp.send("DOM.enable")
    cdp.send("CSS.enable")
    doc = cdp.send("DOM.getDocument", {"depth": -1})
    node_ids = cdp.send("DOM.querySelectorAll", {"nodeId": doc["root"]["nodeId"], "selector": "[data-ocrb-owner]"})[
        "nodeIds"
    ]
    table = font_table()
    failures = []
    checked = 0
    for owner, node_id in zip(owners, node_ids):
        fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": node_id})["fonts"]
        checked += 1
        expected = table.get((owner["family"], owner["weight"]))
        problems = []
        if expected is None:
            problems.append(f"no pinned font file for {owner['family']} {owner['weight']}")
        if owner["style"] != "normal":
            problems.append(f"font-style {owner['style']}")
        for f in fonts:
            if not f.get("isCustomFont"):
                problems.append(f"system font used: {f.get('familyName')} ({f.get('glyphCount')} glyphs)")
            elif expected and f.get("postScriptName") != expected["postscript"]:
                problems.append(f"unexpected face {f.get('postScriptName')} (expected {expected['postscript']})")
        if not fonts:
            problems.append("no platform fonts reported")
        if problems:
            failures.append({"owner": owner, "fonts": fonts, "problems": problems})
    cdp.detach()
    return {"checked_nodes": checked, "fallback_nodes": len(failures), "failures": failures}


def render_once(browser, url: str, form_factor: str, dpr: float, theme: str, full: bool) -> dict:
    context, page = _new_page(browser, form_factor, dpr, theme)
    try:
        page.goto(url, wait_until="load")
        font_errors = _settle(page)
        png = page.screenshot(type="png", animations="disabled", caret="hide", scale="device")
        with open(os.path.join(ROOT, "scripts", "extract.js"), encoding="utf-8") as f:
            geometry = page.evaluate(f.read())
        out = {"png": png, "geometry": geometry, "font_load_errors": font_errors}
        if full:
            out["fonts"] = font_check(context, page)
        out["browser_version"] = browser.version
        return out
    finally:
        context.close()


def render_hidden(browser, url: str, form_factor: str, dpr: float, theme: str) -> tuple[bytes, dict]:
    """Text-hidden render as its own fresh first paint (?hidetext=1, applied before
    first paint by theme.js + base.css). Injecting a style into an already-painted
    page re-rasterized some anti-aliased edges differently, which leaked non-text
    pixels into the ink mask; a fresh paint doesn't. Geometry is returned so the
    caller can confirm the layout is identical to the normal render."""
    context, page = _new_page(browser, form_factor, dpr, theme)
    try:
        page.goto(url + "&hidetext=1", wait_until="load")
        _settle(page)
        png = page.screenshot(type="png", animations="disabled", caret="hide", scale="device")
        with open(os.path.join(ROOT, "scripts", "extract.js"), encoding="utf-8") as f:
            geometry = page.evaluate(f.read())
        return png, geometry
    finally:
        context.close()


def _px_box(rect_css, dpr):
    x, y, w, h = rect_css
    return [x * dpr, y * dpr, w * dpr, h * dpr]


def _int_region(box, pad, width, height):
    x, y, w, h = box
    return (
        max(0, int(math.floor(x)) - pad),
        max(0, int(math.floor(y)) - pad),
        min(width, int(math.ceil(x + w)) + pad),
        min(height, int(math.ceil(y + h)) + pad),
    )


def assign_ink(diff: np.ndarray, layout_boxes: list, ignore_regions: list, pad: int):
    """Ink ownership (METHODOLOGY §4.4): a changed pixel belongs to the line whose
    padded layout box contains it; overlaps go to the line whose unpadded box
    contains it. Returns (ink boxes, ink pixel counts, mask of changed pixels owned
    by no line and outside padded ignore regions). Used at full resolution
    (pad = INK_PAD) and, for the 50% variants, on the downscaled renders."""
    height, width = diff.shape
    owner = np.full((height, width), -1, dtype=np.int32)
    for i, box in enumerate(layout_boxes):
        x0, y0, x1, y1 = _int_region(box, pad, width, height)
        ux0, uy0, ux1, uy1 = _int_region(box, 0, width, height)
        sub = owner[y0:y1, x0:x1]
        in_unpadded = np.zeros(sub.shape, dtype=bool)
        in_unpadded[uy0 - y0 : uy1 - y0, ux0 - x0 : ux1 - x0] = True
        sub[(sub == -1) | in_unpadded] = i
    boxes, counts = [], []
    for i in range(len(layout_boxes)):
        ys, xs = np.nonzero(diff & (owner == i))
        counts.append(int(len(xs)))
        boxes.append([int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
                     if len(xs) else None)
    ignore_mask = np.zeros((height, width), dtype=bool)
    for region in ignore_regions:
        x0, y0, x1, y1 = _int_region(region, pad, width, height)
        ignore_mask[y0:y1, x0:x1] = True
    return boxes, counts, diff & (owner == -1) & ~ignore_mask


def _luminance(rgb):
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def contrast_ratio(fg, bg) -> float:
    a = fg[3]
    comp = [fg[i] * a + bg[i] * (1 - a) for i in range(3)]
    l1, l2 = sorted([_luminance(comp), _luminance(bg[:3])], reverse=True)
    return round((l1 + 0.05) / (l2 + 0.05), 3)


def _layout_only(geometry: dict) -> list:
    """Geometry minus colours (the hidden render differs only in text colour)."""
    return [(el["idx"], [(ln["text"], ln["rect"]) for ln in el["lines"]], el["clipped"]) for el in geometry["elements"]]


def tokens(text: str) -> Counter:
    return Counter(text.split())


def build_ground_truth(bid, template, form_factor, dpr, theme, a, b) -> tuple[dict, np.ndarray, dict]:
    img = _png_array(a["png"])
    hidden = _png_array(a["hidden_png"])
    height, width = img.shape[:2]
    diff = np.any(img != hidden, axis=2)
    table = font_table()
    geom = a["geometry"]

    gt_lines = []
    ignore_regions = []
    for el in geom["elements"]:
        if el["clipped"]:
            if el["visible_region"]:
                ignore_regions.append([round(v, 3) for v in _px_box(el["visible_region"], dpr)])
            continue
        meta = table.get((el["font_family"], el["font_weight"]))
        for line in el["lines"]:
            if not line["text"]:
                continue
            gt_lines.append(
                {
                    "text": line["text"],
                    "layout_box": [round(v, 3) for v in _px_box(line["rect"], dpr)],
                    "font_family": el["font_family"],
                    "font_weight": el["font_weight"],
                    "css_px": el["css_px"],
                    "xheight_px": round(meta["xheight_ratio"] * el["css_px"] * dpr, 3) if meta else None,
                    "capheight_px": round(meta["capheight_ratio"] * el["css_px"] * dpr, 3) if meta else None,
                    "fg_rgba": el["color"],
                    "bg_rgba": el["background"],
                    "contrast_ratio": contrast_ratio(el["color"], el["background"]),
                    "category": el["category"],
                    "stress": el["category"] == "stress",
                    "element_idx": el["idx"],
                }
            )

    boxes, counts, unowned = assign_ink(diff, [ln["layout_box"] for ln in gt_lines], ignore_regions, INK_PAD)
    for line, box, count in zip(gt_lines, boxes, counts):
        line["ink_box"] = box
        line["ink_pixels"] = count
    uy, ux = np.nonzero(unowned)

    for n, line in enumerate(gt_lines):
        line["line_id"] = f"L{n + 1:04d}"

    # Token reconciliation vs innerText (A3): tagged text (incl. clipped) must equal rendered text.
    tagged_tokens = Counter()
    for el in geom["elements"]:
        tagged_tokens += tokens(el["full_text"])
    inner_tokens = tokens(geom["inner_text"])
    style_violations = [
        {"element_idx": el["idx"], "style": el["style"]}
        for el in geom["elements"]
        if el["style"]["textTransform"] != "none"
        or el["style"]["textOverflow"] == "ellipsis"
        or el["style"]["fontVariantCaps"] != "normal"
        or el["style"]["transform"] != "none"
        or el["style"]["writingMode"] != "horizontal-tb"
        or (el["font_family"] in LIGATURE_FONTS and el["style"]["fontVariantLigatures"] != "none")
    ]

    img_b = _png_array(b["png"])
    deterministic_pixels = bool(img.shape == img_b.shape and np.array_equal(img, img_b))
    deterministic_geometry = a["geometry"] == b["geometry"]

    validation = {
        "font_fallback_nodes": a["fonts"]["fallback_nodes"],
        "font_checked_nodes": a["fonts"]["checked_nodes"],
        "font_failures": a["fonts"]["failures"],
        "font_load_errors": a["font_load_errors"],
        "render_deterministic_pixels": deterministic_pixels,
        "render_deterministic_geometry": deterministic_geometry,
        "hidden_render_same_layout": _layout_only(a["geometry"]) == _layout_only(a["hidden_geometry"]),
        "unowned_ink_pixels": int(len(ux)),
        "unowned_ink_bbox": [int(ux.min()), int(uy.min()), int(ux.max()), int(uy.max())] if len(ux) else None,
        "lines_without_ink": [ln["line_id"] for ln in gt_lines if ln["ink_pixels"] == 0],
        "untagged_visible_text": geom["untagged_text"],
        "nested_tagged_elements": geom["nested_tagged"],
        "invisible_non_space_chars": sum(el["invisible_non_space_chars"] for el in geom["elements"]),
        "style_violations": style_violations,
        "token_reconciliation": {
            "ok": tagged_tokens == inner_tokens,
            "missing_from_tagged": dict(inner_tokens - tagged_tokens),
            "extra_in_tagged": dict(tagged_tokens - inner_tokens),
        },
        "clipped_elements": [el["idx"] for el in geom["elements"] if el["clipped"]],
        "viewport_css": geom["viewport"],
        "reported_dpr": geom["dpr"],
    }

    gt = {
        "base_id": bid,
        "template_id": template,
        "form_factor": form_factor,
        "dpr": dpr,
        "theme": theme,
        "width": width,
        "height": height,
        "browser": f"chromium {a['browser_version']}",
        "lines": gt_lines,
        "ignore_regions": ignore_regions,
        "icon_regions": [[round(v, 3) for v in _px_box(r, dpr)] for r in geom["icons"]],
    }
    return gt, diff, validation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(ROOT, "pilot", "dataset"))
    parser.add_argument("--templates", nargs="*", default=list(TEMPLATES))
    args = parser.parse_args()

    for sub in ("renders", "internal", "masks", "ground_truth", "validation"):
        os.makedirs(os.path.join(args.out, sub), exist_ok=True)

    server, port = start_server()
    summary = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for template in args.templates:
            form_factor = TEMPLATES[template]
            for dpr in DPRS[form_factor]:
                for theme in THEMES:
                    bid = base_id(template, dpr, theme)
                    url = f"http://127.0.0.1:{port}/templates/{template}/index.html?theme={theme}"
                    a = render_once(browser, url, form_factor, dpr, theme, full=True)
                    a["hidden_png"], a["hidden_geometry"] = render_hidden(browser, url, form_factor, dpr, theme)
                    b = render_once(browser, url, form_factor, dpr, theme, full=False)
                    gt, diff, validation = build_ground_truth(bid, template, form_factor, dpr, theme, a, b)

                    with open(os.path.join(args.out, "renders", f"{bid}.png"), "wb") as f:
                        f.write(a["png"])
                    with open(os.path.join(args.out, "internal", f"{bid}_hidden.png"), "wb") as f:
                        f.write(a["hidden_png"])
                    Image.fromarray(diff).convert("1").save(os.path.join(args.out, "masks", f"{bid}.png"))
                    with open(os.path.join(args.out, "ground_truth", f"{bid}.json"), "w", encoding="utf-8") as f:
                        json.dump(gt, f, indent=1, ensure_ascii=False)
                    with open(os.path.join(args.out, "validation", f"render_{bid}.json"), "w", encoding="utf-8") as f:
                        json.dump(validation, f, indent=1, ensure_ascii=False)

                    summary.append((bid, len(gt["lines"]), validation))
                    print(
                        f"{bid}: {gt['width']}x{gt['height']} lines={len(gt['lines'])} "
                        f"fallback={validation['font_fallback_nodes']} det={validation['render_deterministic_pixels']} "
                        f"hidden_layout={validation['hidden_render_same_layout']} "
                        f"unowned_ink={validation['unowned_ink_pixels']} no_ink={len(validation['lines_without_ink'])} "
                        f"tokens_ok={validation['token_reconciliation']['ok']} untagged={len(validation['untagged_visible_text'])} "
                        f"clipped={validation['clipped_elements']}",
                        flush=True,
                    )
        browser.close()
    server.shutdown()


if __name__ == "__main__":
    main()
