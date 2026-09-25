// In-page ground-truth extraction (METHODOLOGY §4.3, §4.6). Evaluated by
// render_chromium.py via page.evaluate(). Returns CSS-px geometry; the caller
// converts to image px. Pure DOM reads — no layout-affecting writes.
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const isSpace = (ch) => /\s/.test(ch);  // includes U+00A0

  function rgba(str) {
    const m = str.match(/rgba?\(([^)]+)\)/);
    if (!m) return [0, 0, 0, 0];
    const p = m[1].split(",").map((s) => parseFloat(s));
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }

  function backgroundOf(el) {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = rgba(getComputedStyle(n).backgroundColor);
      if (c[3] > 0) return c;
    }
    return rgba(getComputedStyle(document.documentElement).backgroundColor);
  }

  function clipRects(el) {
    const rects = [[0, 0, vw, vh]];
    for (let n = el.parentElement; n && n !== document.documentElement; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.overflowX !== "visible" || cs.overflowY !== "visible") {
        const r = n.getBoundingClientRect();
        rects.push([r.left + n.clientLeft, r.top + n.clientTop, n.clientWidth, n.clientHeight]);
      }
    }
    return rects;
  }

  function inside(r, c, tol) {
    return r.left >= c[0] - tol && r.top >= c[1] - tol && r.right <= c[0] + c[2] + tol && r.bottom <= c[1] + c[3] + tol;
  }

  function firstFamily(ff) {
    return ff.split(",")[0].trim().replace(/^["']|["']$/g, "");
  }

  const range = document.createRange();
  const elements = [];
  const tagged = Array.from(document.querySelectorAll("[data-category]"));

  tagged.forEach((el, idx) => {
    const cs = getComputedStyle(el);
    const chars = [];
    let invisibleNonSpace = 0;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const s = node.data;
      for (let i = 0; i < s.length; i++) {
        range.setStart(node, i);
        range.setEnd(node, i + 1);
        const rs = Array.from(range.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
        const ch = s[i];
        if (rs.length === 0) {
          if (!isSpace(ch)) invisibleNonSpace++;
          continue;
        }
        const r = rs[0];
        chars.push({ ch, space: isSpace(ch), left: r.left, top: r.top, right: r.right, bottom: r.bottom });
      }
    }

    // Group into visual lines by vertical centre (non-space chars define lines).
    const lines = [];
    let cur = null;
    for (const c of chars) {
      const cy = (c.top + c.bottom) / 2, h = c.bottom - c.top;
      if (c.space) {
        if (cur && Math.abs(cy - cur.cy) <= 0.5 * Math.min(h, cur.h)) cur.text += " ";
        continue;
      }
      if (!cur || Math.abs(cy - cur.cy) > 0.5 * Math.min(h, cur.h)) {
        cur = { text: "", cy, h, left: c.left, top: c.top, right: c.right, bottom: c.bottom, n: 0 };
        lines.push(cur);
      }
      cur.text += c.ch;
      cur.n++;
      cur.left = Math.min(cur.left, c.left);
      cur.top = Math.min(cur.top, c.top);
      cur.right = Math.max(cur.right, c.right);
      cur.bottom = Math.max(cur.bottom, c.bottom);
    }

    const clips = clipRects(el);
    let clipped = false;
    for (const c of chars) {
      if (c.space) continue;
      for (const cr of clips) {
        if (!inside(c, cr, 0.5)) { clipped = true; break; }
      }
      if (clipped) break;
    }
    let visible = null;
    if (clipped) {
      let x0 = 0, y0 = 0, x1 = vw, y1 = vh;
      for (const cr of clips) { x0 = Math.max(x0, cr[0]); y0 = Math.max(y0, cr[1]); x1 = Math.min(x1, cr[0] + cr[2]); y1 = Math.min(y1, cr[1] + cr[3]); }
      const u = lines.reduce((a, l) => ({ l: Math.min(a.l, l.left), t: Math.min(a.t, l.top), r: Math.max(a.r, l.right), b: Math.max(a.b, l.bottom) }), { l: Infinity, t: Infinity, r: -Infinity, b: -Infinity });
      const vx0 = Math.max(u.l, x0), vy0 = Math.max(u.t, y0), vx1 = Math.min(u.r, x1), vy1 = Math.min(u.b, y1);
      if (vx1 > vx0 && vy1 > vy0) visible = [vx0, vy0, vx1 - vx0, vy1 - vy0];
    }

    elements.push({
      idx,
      category: el.getAttribute("data-category"),
      full_text: el.textContent,
      font_family: firstFamily(cs.fontFamily),
      font_weight: parseInt(cs.fontWeight, 10),
      font_style: cs.fontStyle,
      css_px: parseFloat(cs.fontSize),
      color: rgba(cs.color),
      background: backgroundOf(el),
      clipped,
      visible_region: visible,
      invisible_non_space_chars: invisibleNonSpace,
      style: { textTransform: cs.textTransform, textOverflow: cs.textOverflow, fontVariantCaps: cs.fontVariantCaps,
               transform: cs.transform, writingMode: cs.writingMode, fontVariantLigatures: cs.fontVariantLigatures },
      lines: lines.map((l) => ({ text: l.text.replace(/ +/g, " ").trim(), rect: [l.left, l.top, l.right - l.left, l.bottom - l.top], chars: l.n })),
    });
  });

  // Visible text outside any tagged element must not exist (completeness, PILOT A3).
  const untagged = [];
  const w2 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = w2.nextNode(); node; node = w2.nextNode()) {
    if (!node.data.trim()) continue;
    if (node.parentElement && node.parentElement.closest("[data-category]")) continue;
    range.selectNodeContents(node);
    const rs = Array.from(range.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
    if (rs.length) untagged.push(node.data.trim());
  }

  const icons = Array.from(document.querySelectorAll("svg")).map((s) => s.getBoundingClientRect())
    .filter((r) => r.width > 0 && r.height > 0).map((r) => [r.left, r.top, r.width, r.height]);

  return {
    viewport: [vw, vh],
    dpr: window.devicePixelRatio,
    elements,
    untagged_text: untagged,
    nested_tagged: document.querySelectorAll("[data-category] [data-category]").length,
    inner_text: document.body.innerText,
    icons,
  };
}
