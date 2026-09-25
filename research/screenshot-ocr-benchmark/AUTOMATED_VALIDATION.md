# No-human-review validation design (amendment A4)

Status: **design + implementation record (2026-09-25).** This replaces every
check that depended on a person looking at images (A3, A4, A5, B4, E2) and
resolves B6 by scope. Nothing here marks a check as passed. Each replacement is a
reproducible computation with a fixed acceptance criterion, and each criterion
has a **mutation test**: a fixture with a known defect that the check must catch
(`tests/test_automated_checks.py`). A check that can't catch its known defect
counts as broken.

The authoritative expected text for every synthetic image is the ground truth
generated with it (DOM text + measured ink geometry). The validity checks below
establish that this ground truth is correct *for the synthetic render*. They do
**not** establish anything about real-world screenshots (§7).

---

## 1. A3: completeness

**Existing meaning** (PILOT_PLAN §3): all visible text in the render is in the
ground truth and nothing else is. Automated token reconciliation against
`innerText`, **plus a person checking 24 overlays** for missing or extra boxes.

**What the person was guarding against:** text drawn by something other than
DOM text nodes (images, canvas, SVG `<text>`, form controls, CSS generated
content); text hidden behind other elements; boxes on non-text; extraction
dropping an element.

**Automated replacement.** All of these must hold for every base render (zero
tolerance):

| ID | Criterion | How |
|---|---|---|
| A3.1 | Token multiset of tagged elements = token multiset of `document.body.innerText` | existing |
| A3.2 | No visible text node outside a tagged element; no nested tagged elements | existing |
| A3.3 | **No non-DOM text sources**: 0 `<canvas>`, `<img>`, `<picture>`, `<video>`, `<iframe>`, `<object>`, `<embed>`, `<input>`, `<textarea>`, `<select>`, SVG `<text>`; 0 elements with a `url(...)` background image; 0 `::before`/`::after` with generated content | DOM + computed-style scan in `extract.js` |
| A3.4 | **Pixel accounting**: every pixel that changes when text is hidden belongs to a ground-truth line or an ignore region (0 unowned), and 0 such pixels fall inside icon regions | text/no-text difference render (existing ownership + new icon test) |
| A3.5 | **Chrome's glyph count** for every element that owns text = the number of characters with a rendered box | CDP `CSS.getPlatformFontsForNode` `glyphCount`. Independent of our extractor; catches generated or hidden duplicate text |
| A3.6 | **No occlusion**: for every ground-truth character, `document.elementFromPoint` at its centre returns its own element (or a descendant) | `extract.js` |

---

## 2. A4: line text correctness

**Existing meaning:** a person reads 100% of lines on 4 bases plus a ≥10% sample
and confirms the ground-truth string equals the rendered text, with zero
tolerance.

**What the person was guarding against:** rendered glyphs that differ from the
DOM characters (ligatures, contextual alternates, `text-transform`, small caps,
generated content, fallback fonts); reordered or overprinted characters;
extractor bugs (whitespace, line grouping).

**Pilot finding behind the design:** Chrome's `glyphCount` counts characters, not
shaped glyphs. A JetBrains Mono `=>` ligature and `text-transform: uppercase`
both report the same count as the plain case, so glyph counting alone cannot
replace reading. Canonical-render equivalence (A4.1) can.

**Automated replacement** (zero tolerance, every base render):

| ID | Criterion | How |
|---|---|---|
| A4.1 | **Canonical-render equivalence**: the render is pixel-identical to a fresh render of the same page with every character-changing feature forced neutral (ligatures and contextual alternates off, `text-transform: none`, `font-variant-caps: normal`, generated content removed). Every drawn glyph is therefore the plain rendering of exactly the DOM characters that form the ground truth | `?canonical=1` fresh first paint (same technique as the text-hidden render) |
| A4.2 | Every glyph comes from its pinned font file (0 fallback nodes, correct PostScript face) | existing A1 |
| A4.3 | **Visual order = logical order**: within each line, character left edges are non-decreasing in DOM order, and no character overlaps its predecessor by more than 50% of its width | `extract.js` per-character rects |
| A4.4 | Line texts identical across the 3 scale factors of each template/theme | existing (B1 precondition) |
| A4.5 | Extractor correctness on fixtures with hand-written expected strings | existing A6 whitespace fixture |
| A4.6 | Mutation tests: the glyph fixture's ligature, uppercase-transform, generated-content and fallback cases are each detected by A4.1/A4.2/A3.5 | `tests/test_automated_checks.py` |

**Template rule this requires:** templates render with ligatures and contextual
alternates disabled (`base.css`). The pilot showed Inter's `calt` re-shapes the
colon in "9:41" and Roboto's `liga` joins "fi". Neither changes the character a
person reads, but only the strict rule can be proven automatically. The same
`calt` feature is what turns JetBrains Mono's `=>` into an arrow. This is a
documented realism limitation (§7), not a relaxation.

**What automation does not establish:** that a person would transcribe
intrinsically ambiguous glyphs (e.g. `I` vs `l` in a sans-serif) the same way.
Ground truth is defined as the intended characters, as in every
synthetic-ground-truth OCR benchmark; confusable-glyph lines are the tagged
stress set, excluded from headline metrics.

---

## 3. A5: line wrapping

**Existing meaning:** each wrapped paragraph's line splits match what is visible.
Automated check only counted multi-line elements; a person confirmed the splits.

**Automated replacement** (zero tolerance, every tagged element of every base):

| ID | Criterion | How |
|---|---|---|
| A5.1 | **Independent line count**: the number of line boxes Chrome reports for the element's whole range (`Range.getClientRects`, grouped by vertical overlap) = the number of ground-truth lines for that element | Different API path from the per-character grouping that builds the ground truth |
| A5.2 | **Lossless split**: the element's lines, joined with single spaces and normalized, equal the element's normalized `innerText` | No character lost, duplicated or moved between elements |
| A5.3 | **Geometric order**: consecutive lines of a multi-line element have strictly increasing vertical centres and layout boxes that do not overlap vertically | |

---

## 4. B4: box placement

**Existing meaning:** a person reviews overlays of all 24 bases and all 13
variants of 2 bases: green boxes hug the text with no offset or scale error, and
red ignore boxes sit only on clipped text.

**Automated replacement** (zero tolerance):

| ID | Criterion | How |
|---|---|---|
| B4.1 | **Reproducible boxes**: recomputing every line's ink box from the saved 1-bit mask plus the same ownership rule gives exactly the stored box | Catches serialization or transform bugs |
| B4.2 | **Tight boxes**: each ink box's four edge rows/columns each contain at least one ink pixel of that line | |
| B4.3 | **Variant registration**: every variant file is exactly its expected size (V12/V13 = ⌊w/2⌋×⌊h/2⌋), and phase correlation against its reference (V00 for full-size; the Lanczos-downscaled render for V12/V13) finds a global shift of ≤ 0.5 px in x and y | Proves no geometric transform, so reference-derived boxes stay on the text in every variant |
| B4.4 | **Ignore regions**: each ignore region contains text ink, intersects no ground-truth ink box, and comes from an element flagged clipped (existing A7) | |
| B4.5 | Existing B1 (scale consistency), B2 (containment, 0 unowned ink), B3 (every line has ink), B5 (downscaled boxes measured) | existing |

---

## 5. E2: engine coordinate sanity

**Existing meaning:** a bug detector, not a result. A person looks at overlays of
each engine's boxes on 4 images for systematic shift or scale (for example an
internal resize not mapped back). Automated part: median best IoU ≥ 0.3.

**Automated replacement.** Per engine, over all scored images:

| ID | Criterion |
|---|---|
| E2.1 | Median best IoU of ground-truth lines that have a prediction ≥ 0.30 (existing) |
| E2.2 | **No systematic offset**: for predictions matched one-to-one at IoU ≥ 0.3, the median centre offset, normalized by ground-truth line height, is within ±0.25 in x and in y |
| E2.3 | **No scale error**: for each image with ≥ 8 such matches, least-squares slopes of predicted vs. ground-truth centre x and y are computed. The engine's median slope is within [0.98, 1.02], and no image's slope is outside [0.95, 1.05] |

A mutation test feeds oracle predictions scaled ×1.1 and shifted by one line
height; E2.2 and E2.3 must flag both.

---

## 6. B6: device registration, resolved by scope

**Existing meaning:** fiducial residual ≤ 2 px plus human verification of 16
device captures (RQ7: do synthetic rankings hold on real devices?).

**Decision: the benchmark is synthetic-only.** RQ7, the device set, the device
collector, fiducial registration and decisions D3 (for device captures) and D4
are removed. B6 is **N/A by scope**. It is not "passed".

Why synthetic-only is sufficient for the stated purpose: the benchmark's
questions (RQ1–RQ6, RQ8–RQ10) are controlled comparisons of engines under
manipulated scale, compression, theme and text size. Those need exact ground
truth and controlled variation, which synthetic renders provide and device
captures don't. Generalization to real devices was a secondary,
external-validity question.

The alternative was rejected: an automated real-device dataset would need
physical devices, each OS's native screenshot path, and a registration step
whose correctness can only be spot-checked by looking at it. Deterministic
ground truth there is not achievable without human verification or reliance on
the device's own text layer, which is the thing under test.

## 7. Scope and honest limits (to appear on the results page)

- Results describe OCR on **synthetic UI screenshots rendered by headless
  Chromium (Skia, Linux) from our templates**, with pinned open fonts, English,
  Latin script, horizontal text, **no ligatures or contextual alternates**, and
  the 13 specified compression/resize variants.
- They are **not** a measurement of OCR on real-device screenshots (other
  rasterizers such as ClearType or Core Text, subpixel anti-aliasing, system
  fonts, real apps), photos of screens, documents, or scene text. Rankings may
  differ there. No claim of real-world generality is made.
- Automated validity checks prove the ground truth matches what was rendered.
  They do not prove the templates are representative of real interfaces.
- A future, still-automated extension that would widen rasterizer coverage
  without human work: render the same templates in Playwright's Firefox and
  WebKit builds with the same extraction. Not part of v1.

## 8. Removed

- The 381-item review page (`pilot/review/index.html`, `items.json`), crops, line
  sheets, the line sample CSV and `REVIEW_GUIDE.md`.
- The CSV export and ingest workflow (`scripts/build_review.py`,
  `scripts/ingest_review.py`, `human_review.json`) and the validator's
  `apply_human_review`.
- Device-set plans (METHODOLOGY §6, PILOT_PLAN device rows).
- Kept as optional diagnostics only, generated with `--overlays` and not part of
  any criterion: ground-truth, variant and engine overlay images.
