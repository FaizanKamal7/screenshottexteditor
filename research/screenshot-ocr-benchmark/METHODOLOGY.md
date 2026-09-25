# Screenshot OCR Benchmark: methodology

Status: **design draft (Phase 0). No results exist.** This document describes
the complete intended benchmark. The binding analysis rules are in
[PREREGISTRATION.md](PREREGISTRATION.md). The validation run is in
[PILOT_PLAN.md](PILOT_PLAN.md). Prior work and licensing are in
[SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md).

## 1. Question

How accurately do OCR engines read the text in **user-interface screenshots**,
and how does accuracy change with:

- **display scale**: 1x/2x/3x on mobile; 1x/1.5x/2x on desktop
- **file format and quality**: PNG, JPEG, WebP, AVIF, and downscaling
- **theme**: light vs. dark
- **text size**: measured as rendered x-height in image pixels
- **text type**: labels, numbers, buttons, code, paragraphs

## 2. Data sources: what is and is not used

| Used | Not used, ever |
|---|---|
| HTML/CSS templates we write, with our own text content | User-uploaded images from ScreenshotTextEditor |
| Renders of those templates in headless Chromium | Analytics or telemetry of any kind |
| Native screenshots of those templates on devices we own | Production logs or production data |
| OFL-licensed fonts, pinned by file hash | Third-party screenshot datasets (Rico, WebUI); see SOURCES_AND_LICENSES.md |

Text content rules:
- Written by hand for each template, plus seeded fillers for names, amounts,
  dates and emails.
- Emails use `example.com`/`example.org`. Names come from a pinned
  public-domain name list, to be chosen in the pilot.
- No real people, brands or personal data.
- Content is English and Latin script only in v1.
- Confusable glyphs (`Il1|`, `O0o`, `rn`/`m`, `5S`, `8B`) appear at natural
  frequency. A small, separately tagged stress set exists for the confusion
  analysis and is **excluded from the headline metrics**.

## 3. Templates

- **40 templates**: 20 mobile (390×844 CSS px viewport) and 20 desktop
  (1280×800 CSS px).
- **Mobile types:** settings list, login form, profile, chat conversation, notification list, pricing card, checkout, onboarding, app-store listing, map sheet.
- **Desktop types:** analytics dashboard, data table, email inbox, admin form, code editor, terminal, documentation page, pricing page, calendar, file manager.
- Each template supports **light and dark** via a `data-theme` attribute.
- Each type appears twice, with different font, density and content, to give
  within-type variety.
- Fonts: Inter, Roboto, Noto Sans, Liberation Sans, Selawik, Source Serif and
  JetBrains Mono. They are served from local `@font-face` files and pinned by
  SHA-256 hash. No web font CDNs.
- Icons are inline SVG. **No icon fonts and no emoji**, so every DOM text node
  is real text.
- No `::placeholder`. Placeholder-looking text is a styled `<span>` so it has
  DOM geometry.
- No CSS transforms, rotation or vertical text on text elements (out of scope
  for v1).
- Each text element carries `data-category`: `label`, `value-numeric`,
  `button`, `heading`, `paragraph`, `code`, `nav`, `caption`, `input`,
  `disabled`, or `stress`.

## 4. Synthetic set: rendering and ground truth

For each (template, device-scale factor, theme):

1. **Render.** Launch Playwright Chromium (pinned version) with a fixed
   viewport, `deviceScaleFactor` ∈ {1,2,3} (mobile) or {1,1.5,2} (desktop),
   `colorScheme`, a fixed locale and timezone, and animations disabled. Wait
   for `document.fonts.ready`. Take a full-viewport PNG screenshot.
2. **Verify fonts.** For every text node, use Chrome DevTools Protocol
   `CSS.getPlatformFontsForNode` to confirm the glyphs came from the intended
   font file with **zero fallback glyphs**. If any node falls back, fix the
   template or the font and regenerate. Never exclude it silently.
3. **Extract geometry.** In the page, walk every visible text node, create a
   `Range` per character, and read `getClientRects()`.
   - Collapsed whitespace (zero-width rects) is dropped.
   - Characters are grouped into **visual lines** by containing element and
     line-box top.
   - Word boundaries come from the source text, so each line's text is the
     rendered text with single spaces.
   - Rects are converted from CSS px to image px (× device-scale factor). This
     gives the **layout box** of each line.
4. **Ink mask.** Re-render the identical page with every text node set to
   `color: transparent` (text-shadow off). The per-pixel difference between the
   two renders is exactly the ink of all text.
   - Each line's **ink box** is the bounding box of difference pixels inside
     its layout box, padded by 2 image px.
   - Ink boxes are the primary geometry for matching, because engines report
     ink-like boxes rather than CSS line boxes.
5. **Metadata per line:** font family and weight (from computed style and
   CDP), CSS font size, **x-height in image px** (from fontTools `OS/2.sxHeight
   / unitsPerEm` × CSS size × scale factor), cap height (same method), text and
   background colour, WCAG contrast ratio, category, and a clipping flag.
6. **Clipping and ignore regions.** Text whose rects are not fully inside the
   viewport, or that is clipped by an `overflow` ancestor, becomes an **ignore
   region**: it is excluded from ground truth, and predictions over it are not
   penalized. This follows the ICDAR "don't care" convention.
7. **Determinism check.** Each page is rendered twice and must be pixel
   identical. Otherwise it fails validation and is fixed.

## 5. Compression and resize variants

From each lossless base PNG:

| ID | Variant | Encoder / settings (pinned in pilot) | OCR'd? |
|---|---|---|---|
| V00 | PNG (reference) | Playwright output, re-saved losslessly | yes |
| V01 | WebP lossless | libwebp `lossless=True` | **no**: pixel-identical to V00 (verified), so it's reported for file size only |
| V02–V05 | JPEG q95 / q85 / q75 / q60 | Pillow + libjpeg(-turbo), default 4:2:0 chroma subsampling | yes |
| V06 | JPEG q85, 4:4:4 | Pillow, `subsampling=0` | yes |
| V07–V09 | WebP lossy q90 / q75 / q50 | libwebp, method 4 (default) | yes |
| V10–V11 | AVIF q80 / q60 | libavif (encoder and speed pinned) | yes |
| V12 | Downscale 50%, PNG | Lanczos (Pillow `Image.LANCZOS`) | yes |
| V13 | Downscale 50% then JPEG q75 | as above, then V04 settings | yes |

- Every variant records: bytes, bits per pixel, encoder library and version,
  settings, and PSNR and SSIM against V00 (after upscaling back to V00 size
  for V12–V13; used only as a diagnostic).
- Downscaled variants use ground-truth boxes **measured on the downscaled
  pixels** (amendment A2, `scripts/downscaled_gt.py`): the normal and
  text-hidden renders are downscaled with the V12 filter; pixels changed by more
  than 16/255 are ink (faint Lanczos ringing is not), assigned to lines exactly
  as at full resolution (pad 4 px). In the pilot,
  scaling boxes by 0.5 missed Lanczos-spread ink by up to 6.0 px (every line
  affected, counting any changed pixel as ink; up to 3.5 px on 162 of 1,074
  lines counting only changes above 16/255).
  x-heights are still scaled by 0.5 (a font metric, not a pixel measurement).
- Chroma subsampling matters for coloured text on coloured backgrounds,
  which is why V06 exists.

## 6. Real-device set: external validity

Purpose: check whether the synthetic findings hold for real OS text
rasterization (Core Text, DirectWrite/ClearType, Android Skia), not just
headless Chromium.

- **Templates:** a subset of 20 (10 mobile, 10 desktop), in light and dark,
  opened in the native browser on each device.
- **Platforms:** iOS Safari, Android Chrome, Windows Edge (ClearType on,
  default scaling), macOS Safari (if a Mac is available).
- **Capture:** the OS's native screenshot, lossless PNG, original resolution.
- **Ground-truth text:** known, because the content is fixed by the template
  (a device variant uses `system-ui` fonts, so layout differs from the
  synthetic set).
- **Ground-truth geometry:**
  - The template's own script collects per-character rects,
    `devicePixelRatio` and viewport size in the device browser. It posts them
    to a local collector on the LAN; no third party is involved.
  - Four fiducial markers, drawn at known CSS positions, are detected in the
    screenshot to solve for the offset and scale between page coordinates and
    screenshot pixels (browser chrome, status bar).
  - Geometry is then verified by a human in Label Studio: 100% in the pilot, a
    ≥ 20% random sample in the full set.
  - If fiducial registration fails, fall back to manual box drawing by two
    annotators, with disagreements adjudicated.
- **Theme:** dark mode is set through the OS setting and the template's
  `prefers-color-scheme` CSS.
- **Size:** 20 templates × 2 themes × 3–4 platforms = **120–160 images**,
  lossless only.
- **What is recorded:** device model, OS version, browser version, scaling
  setting and capture date.

## 7. Engines

Each engine runs in one pre-registered configuration, as close to the
documented defaults as possible. There is **no per-engine tuning**. The only
permitted change is fixing a misconfiguration that the engine's maintainers
confirm; every such fix is logged as a deviation.

**Track L (located text: lines with boxes). Core, local, free:**

| ID | Engine | Configuration (to be frozen in the pilot) |
|---|---|---|
| `tesseract5` | Tesseract 5.x LSTM, `tessdata_best` eng (pinned commit) | `--oem 1 --psm 3`; lines from `image_to_data` (block, paragraph, line) grouping. No preprocessing. |
| `paddle_v5_mobile` | PaddleOCR 3.x, PP-OCRv5 mobile det + rec | Doc orientation, unwarping and text-line orientation disabled (inputs are never rotated or warped). Recognition model choice (multilingual vs. English) is an open decision. |
| `paddle_v5_server` | PaddleOCR 3.x, PP-OCRv5 server det + rec | Same flags |
| `easyocr` | EasyOCR 1.7.x | `Reader(['en'], gpu=False)`, `readtext(detail=1, paragraph=False)` |
| `doctr` | python-doctr 1.x | `ocr_predictor(pretrained=True)` defaults at the pinned version; lines from `export()` |
| `windows_ocr` | Windows.Media.Ocr (en-US) via `winrt` | Words → line boxes as the API reports them. Runs natively on a Windows host. Record `OcrEngine.MaxImageDimension`. |

**Appendix only:** `rapidocr_ort` (RapidOCR with ONNX Runtime). It runs the
**same PP-OCRv5 mobile weights** as `paddle_v5_mobile`, so it is reported as a
runtime comparison rather than a separate accuracy entry.

**Optional in Track L (pending decisions):** `apple_vision`
(`VNRecognizeTextRequest`, accurate level), `google_vision` (`TEXT_DETECTION`,
feature choice to be frozen), `azure_read` (Image Analysis 4.0 READ, API
version pinned), `aws_textract` (`DetectDocumentText`, LINE blocks). See the
terms review before enabling any of them.

**Track T (transcription only; optional):** vision LLMs such as Claude,
Gemini and GPT.
- They return text without reliable boxes, so they are scored **only** with
  segmentation- and order-agnostic metrics (§8.4). They are never mixed into
  the Track L leaderboard.
- The prompt is fixed verbatim in the preregistration. Temperature is 0 where
  supported, with 3 runs per image; the mean and the range across runs are
  reported.
- Model ID and run date are recorded.
- Provider-side image resizing is recorded, because it confounds the scale
  comparison.

## 8. Scoring

Full rules, with thresholds, are in PREREGISTRATION.md §5–7. Summary:

### 8.1 Normalization

Three levels, applied identically to ground truth and hypotheses:

- **N0 (raw):** codepoints as rendered.
- **N1 (primary):**
  - NFKC normalization, then removal of zero-width characters and soft hyphens.
  - Typographic quotes, dashes and the minus sign are mapped to their ASCII
    equivalents, and non-breaking/other spaces to a normal space.
  - Whitespace runs are collapsed and the text is trimmed. Case is kept.
- **N2:** N1 plus Unicode casefold.

### 8.2 Matching (Track L)

- **Components.** Build a bipartite graph between ground-truth lines (ink
  boxes) and predicted lines. Add an edge when
  `area(g ∩ p) / min(area(g), area(p)) ≥ 0.5`. Each connected component is
  scored as a unit: reference = its ground-truth lines in reading order,
  hypothesis = its predictions in reading order, each joined by one space.
  This handles split lines and merged lines (a label and value read as one
  line) without penalizing segmentation choices that preserve the text.
- **Unmatched lines.** Unmatched ground-truth lines count as full deletions.
  Unmatched predictions count as insertions, unless they fall mostly (≥ 50% of
  their area) inside an ignore region.
- **Detection metrics.** A separate, strict one-to-one greedy IoU matching at
  IoU ≥ 0.5 gives line-level detection precision, recall and F1. It reuses the
  existing bench's `_match_lines`.

### 8.3 Metrics

| ID | Metric | Role |
|---|---|---|
| M1 | **CER (N1)** = (S + D + I) / reference characters, micro-averaged over a cell | **Primary** |
| M2–M4 | CER under N0, N2, and N1 with all whitespace removed | Sensitivity |
| M5 | WER (N1) | Secondary |
| M6 | Line exact-match rate (component level, weighted by ground-truth lines) | Secondary |
| M7 | **Numeric-token accuracy**: tokens with ≥ 1 digit reproduced exactly | Secondary (headline for dashboards) |
| M8 | Detection precision / recall / F1 at IoU 0.5 (also 0.3 and 0.7) | Secondary |
| M9 | Bag-of-words F1 per image (order- and segmentation-agnostic) | Robustness check for Track L; **primary for Track T** |
| M10 | Runtime: median and p90 wall-time per image, by resolution class, on stated hardware | Secondary, caveated |
| — | Character confusion counts from edit-operation alignment | Descriptive |

### 8.4 Track T scoring

M9 bag-of-words F1, plus a page-level CER computed after sorting both
reference and hypothesis lines in reading order. Because line order in an
LLM's transcript isn't guaranteed, the order-sensitive page CER is reported
only as secondary.

## 9. Statistics (summary)

- The unit of resampling is the **template**, because lines and images from
  the same template are not independent.
- 95% percentile intervals come from a cluster bootstrap with 10,000 resamples
  and a fixed seed. Engine comparisons use **paired** bootstrap differences.
- A pre-declared confirmatory family is corrected with Holm; everything else
  is labeled exploratory.
- Details are in PREREGISTRATION.md §7.

## 10. Outputs and data schema

```
dataset/
  manifest.jsonl          one row per image
  images/{image_id}.{png|jpg|webp|avif}
  ground_truth/{base_id}.json
  masks/{base_id}.png     1-bit ink mask (diagnostic, published)
  templates/              HTML/CSS + font files (OFL) + font hashes
predictions/{engine_id}/{image_id}.json
scores/
  line_scores.parquet (+ .csv)
  component_scores.parquet
  summary.csv, summary.json
  confusions.csv
environment/{run_id}.json
```

`manifest.jsonl`:

```json
{"image_id": "m03-settings_dpr3_dark_V04", "base_id": "m03-settings_dpr3_dark",
 "template_id": "m03-settings", "form_factor": "mobile", "source": "chromium",
 "device": null, "os": null, "browser": "chromium 1xx.x", "dpr": 3,
 "theme": "dark", "variant": "V04", "format": "jpeg", "quality": 75,
 "chroma_subsampling": "4:2:0", "lossless": false, "downscale": 1.0,
 "width": 1170, "height": 2532, "bytes": 0, "bpp": 0.0,
 "psnr_vs_v00": 0.0, "ssim_vs_v00": 0.0,
 "encoder": "libjpeg-turbo x.y via Pillow a.b", "sha256": "…",
 "license": "CC-BY-4.0", "generator_git_sha": "…"}
```

(Numeric values above are placeholders showing types, not data.)

`ground_truth/{base_id}.json`:

```json
{"base_id": "…", "width": 0, "height": 0, "dpr": 3,
 "lines": [{"line_id": "L0001", "text": "…", "layout_box": [0,0,0,0],
            "ink_box": [0,0,0,0], "font_family": "Inter", "font_weight": 400,
            "css_px": 15.0, "xheight_px": 0.0, "capheight_px": 0.0,
            "fg_rgb": [0,0,0], "bg_rgb": [0,0,0], "contrast_ratio": 0.0,
            "category": "label", "stress": false}],
 "ignore_regions": [[0,0,0,0]],
 "validation": {"font_fallback_nodes": 0, "render_deterministic": true}}
```

Boxes are `[x, y, w, h]` in image pixels, origin top-left, matching the
existing bench's `BenchLine.bbox` convention.

`predictions/{engine}/{image_id}.json`:

```json
{"engine_id": "tesseract5", "engine_version": "…", "config": {},
 "image_id": "…", "status": "ok|error|timeout", "error": null,
 "total_s": 0.0, "detect_s": null, "recognize_s": null,
 "lines": [{"bbox": [0,0,0,0], "text": "…", "confidence": 0.0}],
 "raw": {}}
```

`line_scores` columns: `image_id, engine_id, line_id, component_id,
component_gt_count, component_pred_count, detected_iou50, iou, ref_text,
hyp_text, cer_n0, cer_n1, cer_n2, cer_nows, wer, exact_n1,
numeric_tokens, numeric_correct, category, xheight_px, contrast_ratio, dpr,
theme, variant, form_factor, source`.

`environment/{run_id}.json`: CPU model, core count, RAM, OS, Python version,
all package versions (`pip freeze`), Tesseract and tessdata versions,
model-weight hashes, Chromium version, git SHA, and UTC start and end times.
The existing bench did not record hardware, which is a gap to close.

Downloads are published as CSV, Parquet and JSON, plus a ZIP of the full
dataset, on Zenodo (DOI) and/or Hugging Face Datasets, with a `CITATION.cff`.

## 11. Results page (after the full run; not built in Phase 0)

- **Route:** `/research/screenshot-ocr-benchmark/`, English only,
  prerendered.
- **Charts:** static SVG generated at build time from `summary.json`, each
  with a table fallback. No client-side chart library, consistent with the
  homepage LCP work.
- **Sections:**
  - Key findings, written only from computed values.
  - Main table.
  - Charts: CER vs. x-height; CER vs. bytes per format; scale; theme;
    synthetic vs. device.
  - Confusion table and sample overlays.
  - Methodology link, limitations, and a conflict-of-interest note (the
    product uses PaddleOCR).
  - Changelog, downloads, citation block.

## 12. Known limitations (stated up front)

- Synthetic renders come from one rasterizer (Chromium/Skia on Linux). The
  device set exists to measure how far that generalizes, but it is small.
- English, Latin script, horizontal text only.
- "Default configuration" is a policy choice. Engines tuned by an expert
  (for example Tesseract with upscaling) may do better. That is reported as
  exploratory, never as the headline.
- Runtime numbers are specific to one machine. Windows OCR runs on a
  different host from the Linux engines, so its runtime is not comparable and
  is reported separately.
- Cloud and LLM results are snapshots of a moving service. The run date and
  model ID are part of the result.

---

## Appendix A. Reuse review of `services/pipeline/bench/`

Read in full: `engines.py`, `run_benchmark.py`, `Dockerfile`,
`requirements-bench.txt`, the head of `roundtrip_check.py`,
`tests/fixtures/generate_synthetic_fixtures.py`, and the `results.json`
summary. The benchmark will **copy** reusable code into `research/` rather
than import it, so the published benchmark never depends on production code
paths.

| Item | Reuse? | Changes required |
|---|---|---|
| `engines.py` `BenchLine`, `BenchResult`, `BenchEngine.construct()/run()` pattern | **Yes, as is** | Add `engine_version`, `config` and `status` fields |
| `engines.py` `_quad_to_bbox` | **Yes** | none |
| `engines.py` `PaddleEngine` | **Yes, with changes** | It mirrors the *production* config (including `enable_mkldnn=False`, a production workaround). For the benchmark, config is a pre-registered decision. Add a server-model variant. Record weight hashes. |
| `engines.py` `RapidEngine` | **Yes (appendix engine)** | Uses `LangRec.CH` (the multilingual PP-OCRv5 model), consistent with Paddle mobile. Drop the OpenVINO arm (it isolates runtime only). |
| `engines.py` `TesseractEngine` | **Yes, with changes** | Make `--oem 1 --psm 3 -l eng` explicit; record `tesseract --version` and the tessdata commit. The (block, paragraph, line) grouping is kept as is. |
| `run_benchmark.py` `_iou` | **Yes** | none |
| `run_benchmark.py` `_match_lines` (greedy IoU) | **Yes, for M8 detection metrics** | Threshold becomes 0.5 primary (was 0.3), with 0.3 and 0.7 for sensitivity |
| `run_benchmark.py` `_cer` | **Formula yes, library no** | Swap GPL `Levenshtein` for MIT `rapidfuzz.distance.Levenshtein`. Normalization happens before the CER call. |
| `run_benchmark.py` interleaved rep-major timing loop and untimed warm-up call | **Yes** | Used for the M10 timing subset only; accuracy runs need one pass |
| `run_benchmark.py` accuracy-vs-Paddle | **No** | Replaced by scoring against exact ground truth; comparing to Paddle's output is not ground truth |
| `run_benchmark.py` `load_fixtures` | **Yes** | Read `manifest.jsonl` instead of globbing |
| `Dockerfile` | **Structure yes** | Keep `python:3.12-slim` and baking models at build time. Add EasyOCR and docTR weight baking, and pin tessdata_best by commit rather than the Debian `tesseract-ocr` default data. Rendering needs a separate image (Playwright). |
| `requirements-bench.txt` | **Pins as a starting point** | Replace `python-Levenshtein` with `rapidfuzz`. `numpy<2.0` (Paddle constraint) may conflict with docTR/EasyOCR; the pilot resolves this, possibly with one container per engine. |
| `tests/fixtures/generate_synthetic_fixtures.py` | **No** | PIL rendering (documented rasterizer mismatch vs. real renderers in `docs/pipeline-tuning.md`), and it exports no ground-truth boxes |
| `tests/fixtures/*.png/jpg` (8 images) | **Smoke-test input only** | No ground-truth files; not part of the dataset |
| `results.json` | **Runtime prior only** | Used in PILOT_PLAN.md for the pre-pilot estimate; hardware unrecorded |
| `run_log.txt` | No | Contains only `placeholder` |
| `roundtrip_check.py`, `match_instrumented.py`, `scoring_investigation.py`, `run_match_investigation.py` | **No (OCR track)** | Font-matching tools; relevant only to a possible later font-identification track |
