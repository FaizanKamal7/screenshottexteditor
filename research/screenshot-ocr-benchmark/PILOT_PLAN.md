# Pilot plan (10%)

Status: **design only. Nothing has been run.** The pilot validates the
machinery (ground-truth generation, box coordinates, scoring, compression
variants, engine adapters, runtime and storage) before the full dataset
exists.

- The pilot produces **no publishable results**.
- Pilot accuracy values are used only for bug detection and for the
  sample-size rule in [PREREGISTRATION.md](PREREGISTRATION.md) §2. They are
  not interpreted or published.

## 1. Pilot size

| | Full design | Pilot (10%) |
|---|---|---|
| Templates | 40 (20 mobile + 20 desktop) | **4** (2 mobile + 2 desktop) |
| Base renders (template × scale × theme) | 240 | **24** |
| OCR'd synthetic images (13 variants each) | 3,120 | **312** |
| Size-only variant (V01) | 240 | 24 |
| Device captures | removed (A4) | removed (A4) |
| Core engines | 6 | 6 |
| Engine runs (accuracy pass) | 6 × 3,280 = 19,680 | 6 × 328 = **1,968** |
| Timing subset | V00 of 8 templates (48 images) × 3 reps | V00 of all 4 pilot templates (24 images) × 3 reps |

Pilot templates. Together they cover all 7 fonts and both form factors:

| ID | Type | Fonts | Why it's in the pilot |
|---|---|---|---|
| `m01-settings` | Mobile settings list | Inter | Simple baseline; small captions |
| `m05-chat` | Mobile chat | Roboto, Noto Sans | Coloured bubbles (chroma subsampling), timestamps |
| `d01-dashboard` | Desktop analytics dashboard | Selawik, Liberation Sans | Dense numbers, table, small axis labels |
| `d06-code-editor` | Desktop code editor with docs pane | JetBrains Mono, Source Serif | Monospace and code symbols, serif paragraphs, wrapped text |

## 2. Procedure

1. Write the 4 templates and the font manifest (files and SHA-256 hashes).
2. Run the renderer to produce base PNGs, text-hidden renders, DOM geometry,
   ink masks and ground-truth JSON.
3. Run the variant generator: 13 files per base, plus the manifest.
4. ~~Capture the device set~~: removed (synthetic-only scope, A4). The whole
   pipeline runs unattended: `python scripts/run_pilot.py`.
5. Run the engine adapters: accuracy pass (parallelism allowed), then the
   timing subset (serial, idle machine).
6. Run the scorer: unit tests, then oracle, perturbed-oracle, empty and
   jitter engines, then the 6 real engines.
7. Write the pilot report: validation outcomes, measured runtime and storage,
   variance for the sample-size rule, and any deviations.

## 3. Validation checks and pass criteria

"Zero tolerance" means any failure is a bug that must be fixed and the step
re-run. The pilot does not pass with known failures in these checks.

### A. Ground-truth generation (zero tolerance)

| # | Check | Pass criterion |
|---|---|---|
| A1 | Font fallback via CDP `CSS.getPlatformFontsForNode` | 0 nodes with any fallback glyphs, all 24 bases |
| A2 | Render determinism (render twice) | Pixel-identical, 24/24 |
| A3 | Completeness (automated, A4) | All of AUTOMATED_VALIDATION §1 on every base: token reconciliation; no untagged/nested text; 0 non-DOM text sources; 0 unowned ink and 0 ink in icon regions; Chrome glyph count = rendered characters; 0 occluded characters. (Formerly included human review of 24 overlays.) |
| A4 | Line text correctness (automated, A4) | Every base render pixel-identical to its canonical render; 0 fallback glyphs; visual order = logical order; line texts identical across scales; whitespace fixture and mutation tests pass (AUTOMATED_VALIDATION §2). (Formerly a person reading ~270 lines.) |
| A5 | Wrapping (automated, A4) | For every element: independent range line count = ground-truth line count; lines joined = normalized `innerText`; lines in strict vertical order without overlap (AUTOMATED_VALIDATION §3) |
| A6 | Whitespace reconstruction | Unit fixture with double spaces, `&nbsp;` and `<br>` produces the expected strings exactly |
| A7 | Ignore regions | A deliberately clipped element in one template becomes an ignore region, not ground truth |

### B. Box coordinates (zero tolerance)

| # | Check | Pass criterion |
|---|---|---|
| B1 | Scale consistency | Layout box at scale k = k × box at scale 1, within ±1·k px per edge; ink box within ±2·k px |
| B2 | Ink containment | Ink box inside layout box (+2 px padding), 100% of lines |
| B3 | Ink non-empty | ≥ 1 ink pixel for 100% of lines |
| B4 | Box placement (automated, A4) | Boxes reproducible from the saved mask; tight; every variant exactly sized and registered to its reference within 0.5 px (phase correlation); ignore regions contain ink and touch no ground-truth box; B1–B3 pass (AUTOMATED_VALIDATION §4) |
| B5 | Downscaled boxes (amended, A2) | V12/V13 boxes are measured on the downscaled pixels: every V12 file is pixel-identical to the downscale the boxes were measured on, no downscaled ink falls outside every line's padded region, and every line has ink. (Originally "= 0.5 × V00 boxes within ±1 px"; the pilot showed that assumption is off by up to 6.0 px.) |
| B6 | Device registration | **N/A: synthetic-only scope (A4).** No device set exists |

### C. Scoring (zero tolerance)

| # | Check | Pass criterion |
|---|---|---|
| C1 | Unit tests with hand-computed expected values | Split line, merged line, missing line, extra line, ignore-region drop, empty text, each N1 rule, casefold, numeric tokens, reading order: all pass |
| C2 | Oracle engine (returns ground truth) | M1 = 0, M6 = 1, M7 = 1, M8 F1 = 1 on every pilot image |
| C3 | Perturbed oracle (seeded, known edit counts) | Computed CER = injected edits / reference characters, exactly |
| C4 | Empty engine | M1 = 1 exactly; recall = 0 |
| C5 | Box-jitter oracle (±10% of line height shifts) | Components unchanged at τ_c = 0.5 (checks the threshold isn't brittle) |
| C6 | Interval coverage (amended, A1) | For the design's templates per stratum, the confirmatory intervals (single-engine bootstrap-t; log rate-ratio symmetric bootstrap-t) cover the known truth within [0.93, 0.97] in all 8 synthetic scenarios (5 selection + 3 held-out), 2,000 simulations each. (Originally "200 datasets, roughly 95%": too imprecise, since at 200 simulations the draft method looked borderline-acceptable at 0.91 and 2,000 showed 0.908 ± 0.007.) |
| C7 | Scorer determinism | Two runs produce byte-identical output files |

### D. Compression variants

| # | Check | Pass criterion |
|---|---|---|
| D1 | Decode and dimensions | All 13 variants decode; V12/V13 are half size; others equal V00 |
| D2 | Lossless identity | V01 decoded pixels hash-equal to V00 |
| D3 | Size vs. quality | Bytes non-increasing as quality drops within each format family. Exceptions are investigated and explained, not hidden. |
| D4 | Fidelity vs. quality | PSNR non-increasing as quality drops (sanity check) |
| D5 | Provenance | Encoder library, version and settings recorded for 100% of variants |
| D6 | JPEG subsampling | Verified from file headers: V06 is 4:4:4, V02–V05 and V13 are 4:2:0 |

### E. Engine adapters

| # | Check | Pass criterion |
|---|---|---|
| E1 | Coverage | Every engine attempts all 328 images; failures and timeouts are logged with the error. Failures are classified as engine failure, `resource_oom` (Docker-confirmed kill at the declared 24 GB budget) or infrastructure failure (amendment A3) |
| E2 | Coordinate sanity (automated, A4; bug detector, not a result) | Per engine over all scored images: median best IoU ≥ 0.30; median centre offset within ±0.25 line heights on each axis; median centre-regression slope within [0.98, 1.02] and every image's within [0.95, 1.05] (images with ≥ 8 matches) (AUTOMATED_VALIDATION §5). (Formerly overlay review.) |
| E3 | Determinism | Re-run on a 10% subset (33 images): identical text. A nondeterministic engine switches to 3 runs per image with the mean reported, recorded as a pre-registration amendment before tagging. |
| E4 | Version lock | `engines.lock.json` complete: package versions, model files, weight SHA-256 hashes, Tesseract and tessdata versions |
| E5 | Dependency isolation | Each engine runs in its own environment where pins conflict (for example Paddle's `numpy<2.0`). The same image bytes are confirmed across environments by hash. |
| E6 | Windows OCR host | Reads the identical files (hash check). Hardware recorded separately. |

### F. Runtime

| # | Check | Output |
|---|---|---|
| F1 | Per-image time per engine vs. megapixels and line count | A measured seconds-per-image model, used to project the full run |
| F2 | Timing-subset protocol dry run | Coefficient of variation per image across 3 reps. If CV > 20% for any engine, find the cause (background load, thermal throttling) before the full run. |

### G. Storage

| # | Check | Output |
|---|---|---|
| G1 | Bytes per artifact class (images per variant, masks, text-hidden renders, predictions, scores) | Measured totals, projected to the full set |
| G2 | Host limits | Projection checked against the chosen dataset host's current limits |

## 4. Runtime and storage estimates (before the pilot)

These are **estimates**, not measurements. The only measured input is
`services/pipeline/bench/results.json` (existing bake-off: 8 synthetic
fixtures, 5 reps, 40 runs per engine; hardware not recorded):

| Engine (existing bench) | Median per image | Range |
|---|---|---|
| PaddleOCR PP-OCRv5 mobile | 3.70 s | 0.245–5.125 s |
| RapidOCR ONNX Runtime | 1.69 s | 1.10–2.51 s |
| RapidOCR OpenVINO | 2.22 s | 1.80–2.61 s |
| Tesseract 5 | 0.22 s | 0.16–0.50 s |

**Scaling assumption (unverified).** Those fixtures are small (0.04–0.82 MP,
roughly 0.2 MP median, 3–7 lines each). The benchmark images average about
1.8 MP:

- base renders range from 0.33 MP (mobile 1x) to 4.1 MP (desktop 2x);
- the 2 downscaled variants are a quarter of that;
- the templates are much denser in text.

- **Lower bound:** per-image time stays at the measured median.
- **Upper bound:** time grows linearly with pixels, about 9×.
- EasyOCR, docTR, Paddle server and Windows OCR have **no measurement**. They
  are assumed to fall in the same range as Paddle mobile, which is a guess the
  pilot replaces.

| | Pilot | Full |
|---|---|---|
| Accuracy pass, all 6 engines (CPU time) | about 1.6–16 h | about 16–160 h |
| Timing subset | about 0.3–3.5 h | about 0.7–7 h |
| Rendering and variants | minutes (unmeasured) | under 1–2 h (unmeasured) |

The range is wide on purpose; narrowing it is the pilot's job. Accuracy
passes can run in parallel across cores and engines. Timing runs cannot.

**Storage.** Assumes about 0.1–0.5 bytes/px for UI PNGs; the existing flat
fixture `ios_3x_login.png` is about 0.035 bytes/px, and realistic templates
will be busier. Other variants are assumed to add 2–7× the base PNG size in
total per base.

| | Pilot | Full |
|---|---|---|
| Images, 13 variants plus V01 | about 15–190 MB | about 0.15–1.9 GB |
| Text-hidden renders (internal, not published) | about 5–25 MB | about 50–250 MB |
| Masks (1-bit) | < 5 MB | < 50 MB |
| Device captures | removed (A4) | removed (A4) |
| Predictions JSON (6 engines, 5–50 KB each) | about 10–100 MB | about 0.1–1 GB |
| Scores (Parquet/CSV) | < 20 MB | < 200 MB |
| **Total** | **about 50–400 MB** | **about 0.5–4 GB** |

## 5. Go / no-go for the full run

1. All zero-tolerance checks (A, B, C) pass. D and E pass, or have
   documented, fixed causes.
2. The runtime and storage projections from F and G are accepted.
3. The sample-size rule (PREREGISTRATION §2) is applied using pilot variance,
   and the template count is set.
4. Decisions D1–D5 (PREREGISTRATION §12) are resolved.
5. PREREGISTRATION.md, the scorer and `engines.lock.json` are committed and
   tagged `prereg-v1.0`.

Only then are the remaining 36+ templates generated and the full run
executed.

## 6. Code the pilot requires (Phase 1, not written yet)

```
research/screenshot-ocr-benchmark/
  templates/{m01-settings,m05-chat,d01-dashboard,d06-code-editor}/index.html
  templates/_shared/{base.css, theme.js}
  templates/_fixtures/{whitespace, glyphs}/   # extractor + mutation-test fixtures
  fonts/ (OFL files + fonts.lock.json)
  scripts/render_chromium.py      # base + text-hidden renders, CDP font check, geometry, ink boxes
  scripts/derive_variants.py      # V00–V13, manifest.jsonl
  scripts/auto_checks.py          # automated replacements for human review (A4)
  scripts/run_pilot.py            # unattended end-to-end runner
  scripts/engines/*.py            # adapters (Appendix A of METHODOLOGY.md)
  scripts/run_ocr.py              # resumable, cached, per-engine environments
  scripts/score.py                # normalization, components, M1–M9
  scripts/bootstrap.py            # cluster bootstrap, Holm
  scripts/validate_pilot.py       # checks A–G → pilot_report.md
  tests/test_normalize.py, test_matching.py, test_metrics.py, test_bootstrap.py
  docker/{render,ocr-paddle,ocr-torch,ocr-tesseract}.Dockerfile
  engines.lock.json
```
