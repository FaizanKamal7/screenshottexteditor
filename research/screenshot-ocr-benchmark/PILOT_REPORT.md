# Pilot report: Screenshot OCR Benchmark

Status (2026-09-25): **pilot runs fully unattended with no human review.** The
last unattended run passed every check **except E2**, which fails under its
current criterion. That criterion is not valid for heavily mis-segmented images
(§4), and a replacement is proposed for your decision, not applied. Accuracy
numbers here come from 4 templates, are **not benchmark results**, and must not
be published.

Scope: **synthetic-only.** Results describe OCR on headless-Chromium renders of
our own templates, scored against ground truth generated with each render.
**Nothing here validates OCR on real-device or real-world screenshots**
(METHODOLOGY §6).

Key documents: [AUTOMATED_VALIDATION.md](AUTOMATED_VALIDATION.md) (checks,
criteria, mutation tests), [PREREGISTRATION.md](PREREGISTRATION.md) (amendments
A1–A4), [METHODOLOGY.md](METHODOLOGY.md). Outputs: `pilot/validation/pilot_checks.json`,
`pilot/scores/`, `pilot/logs/run_pilot.log`.

## 1. What ran (unattended: `python scripts/run_pilot.py`)

| Item | Count |
|---|---|
| Templates / base renders / ground-truth lines | 4 / 24 / 1,074 |
| OCR'd images (V00, V02–V13) | 312 (+24 size-only V01) |
| Engines on all 312 images | 6: `tesseract5`, `windows_ocr`, `doctr`, `paddle_v5_mobile`, `easyocr`, `paddle_v5_server` |
| Scored predictions | 1,872, 0 engine failures, 0 memory exclusions |
| Determinism re-runs | 186, 0 differences |
| Automated tests | 65 passed, 0 failed (26 are mutation tests of the automated checks) |

The redesign changed template typography (§3), so the runner re-rendered all 24
bases. It detected by pixel hash that only the 12 `m01`/`m05` bases had changed.
It deleted exactly those images' 1,044 predictions (936 accuracy + 108
determinism) and re-ran them. The 12 `d01`/`d06` renders were byte-identical and
kept their predictions.

## 2. Manual-review dependencies removed

| Removed | Replaced by |
|---|---|
| 381-item review page (`pilot/review/index.html`, `items.json`), line crops, line sheets, 10% sample CSV, `REVIEW_GUIDE.md` | Automated criteria below |
| CSV export and ingest (`scripts/build_review.py`, `scripts/ingest_review.py`, `human_review.json`, validator `apply_human_review`) | `validate_pilot.py` computes every status; exits 1 on any FAIL |
| Device set: RQ7, 160 device screenshots, fiducials, Label Studio verification, D4 | Synthetic-only scope (A4); B6 = N/A |
| One-off pass scripts (`finish_pilot.ps1`, `finish_remediation.ps1`) | `scripts/run_pilot.py`, which also removes stale predictions by pixel hash |

Overlay images still exist only as optional debugging output
(`validate_pilot.py --overlays`, `pilot/diagnostics/`). No criterion uses them.

## 3. Replacement criteria and results

All criteria are zero-tolerance unless a threshold is stated. Details and the
reasoning for each are in AUTOMATED_VALIDATION.md.

| Check | Former human step | Automated acceptance criterion | Result |
|---|---|---|---|
| **A3** completeness | Review 24 overlays | Token reconciliation vs `innerText`; no untagged/nested text; **0 non-DOM text sources** (canvas, img, SVG `<text>`, form controls, background images, generated content); **0 unowned ink and 0 ink in icon regions**; **Chrome glyph count = rendered characters**; **0 occluded characters** (hit-test lands on the character's own element) | **PASS** 24/24 bases |
| **A4** line text | Read ~270 lines | **Pixel-identical to a canonical render** (ligatures, contextual alternates, `text-transform`, small caps and generated content forced neutral); 0 fallback glyphs; **visual order = DOM order**; line texts identical across scales; whitespace + mutation tests pass | **PASS** 24/24 bases |
| **A5** wrapping | Check paragraph splits | **Independent range line count = ground-truth line count**; **lines joined = normalized `innerText`**; strictly increasing, non-overlapping lines | **PASS** 24/24 (48 multi-line elements) |
| **B4** box placement | Review 52 overlays | **Boxes reproducible from the saved mask**; tight edges; **every variant exactly sized and registered ≤ 0.5 px** (phase correlation); ignore regions contain ink and touch no box; B1–B3 pass | **PASS**: 24/24 bases; 336 files, worst shift 0.0044 px |
| **E2** engine boxes | Review 24 overlays | Median best IoU ≥ 0.30; median centre offset ≤ ±0.25 line heights per axis; median slope ∈ [0.98, 1.02] and **every image's slope ∈ [0.95, 1.05]** (Theil–Sen) | **FAIL** (§4) |
| **B6** device registration | Human-verified device captures | None: removed by scope | **N/A (synthetic-only)**, not a pass |

Every criterion has a mutation test that must catch a planted defect:
- ligature, `text-transform`, generated content, fallback font, reordered text,
  occluded text and canvas/SVG text;
- a line-count mismatch, a lost character and misordered lines (A5);
- a 1 px box change, a wrong-size variant, a 1 px image shift and an ink-free
  ignore region (B4);
- ×1.1 scale, a 0.4-line offset, and a 4% scale bug hidden among 25% outliers (E2).

It must also pass the clean controls, including syntax-highlighted code. All
26 mutation tests pass.

Two bugs in my first implementation were caught along the way:
- The occlusion check accepted a child element covering the text; fixed to
  require an exact hit on the text's own element.
- The glyph-count check compared Chrome's whole-subtree count against direct
  text only, so it wrongly failed syntax-highlighted code; fixed and covered by
  a new true-negative fixture.

**Template change needed for A4 (documented, not a relaxation).** The canonical
render showed Inter's contextual alternates re-shape "9:41" and Roboto's
standard ligatures join "fi". A person reads the same characters either way,
but only a strict one-glyph-per-character rule can be proven without looking.
The same feature family turns JetBrains Mono's `=>` into an arrow. Templates now
render with ligatures and contextual alternates off. This is a small, stated
realism cost (METHODOLOGY §3, §12).

## 4. E2: why it fails, and the proposed alternative

- **Evidence of no coordinate bug:** every engine's median slope is
  1.000 ± 0.0003 on both axes, and median centre offsets are within 0.11 line
  heights. Four engines pass outright.
- **Where it fails:** one image each for two engines.
  - `tesseract5`: `d06-code-editor_dpr2_light_V00`, x-slope 0.928.
  - `easyocr`: `d06-code-editor_dpr1_light_V13`, x-slope 0.946.
- **Why:** on those images, 33% and 41% of matched boxes are merged or split
  lines (width more than 50% off the ground-truth line). Tesseract joins the
  file tree, code and docs pane into one box; EasyOCR fragments tiny
  half-resolution code. That exceeds what any robust per-image slope estimator
  tolerates (Theil–Sen: ~29%).
- **Conclusion:** the per-image criterion cannot validly separate coordinate
  errors from heavy segmentation on such images. Segmentation itself is already
  measured by the accuracy metrics.
- **History (disclosed):** the criterion first used least-squares slopes, which
  failed 4 of 6 engines for the same reason. It was changed to Theil–Sen after
  seeing that result (AUTOMATED_VALIDATION §5), with new mutation tests proving
  it still catches real scale bugs. I have not changed it a second time.

**Proposed replacement (not applied, needs your approval): pool by image
size.**
- A coordinate-mapping bug comes from engine code that depends on image
  dimensions (e.g. an internal resize above some size). So pool matched pairs
  per (engine, exact image size) instead of per image, and require each pooled
  Theil–Sen slope to fall in [0.95, 1.05].
- A size-dependent bug moves every image of that size, so pooling keeps full
  detection power, while no single mis-segmented image can dominate. The pilot
  has 10 image sizes per engine.
- Adoption would need a mutation test proving a bug confined to one image size
  is still caught.

### Update 2026-09-25: pooling approved and implemented; E2 still fails, on E2.4 only

**E2.3 pooling (approved):**
- Implemented, with regression tests: a ×1.08 bug confined to one image size is
  caught; a half-scale bug at one size is caught; one 42%-mis-segmented image
  among clean same-size images passes.
- On the full unattended run (`python scripts/run_pilot.py`, 2026-09-25 17:35),
  **E2.3 passes for all 6 engines**, with pooled slopes 0.999–1.014 at every
  image size.

**E2.4 (my addition, not part of the approved proposal) fails for
`tesseract5`:**
- It required a median best IoU ≥ 0.30 at every image size. Tesseract falls
  below that at three sizes: 0.048 at 640×400, 0.169 at 2560×1600 and 0.20 at
  195×422.
- Its pooled slopes at those same sizes are exactly 1.000, so its coordinates
  are correct. The low IoU comes from segmentation: giant merged boxes and
  fragments.
- E2.4 as written has the same flaw the original per-image slope had. The
  pipeline therefore still exits 1, and the failure is recorded, not hidden.

**Proposed replacement for E2.4 (not applied, needs your decision):** "every
image size where the engine returned ≥ 8 boxes yields ≥ 8 one-to-one matches at
IoU ≥ 0.3".
- It targets the actual gap directly (no matches, so no slope), with no IoU
  magnitude involved.
- Measured as a diagnostic on the pilot data: every engine meets it at all 10
  sizes, with a minimum of 12 (Windows OCR) to 207 (docTR) matches.
- A half-scale bug gives 0 matches, so it is still caught.
- **The alternative is to drop E2.4**, which leaves exactly the design you
  approved.

**Implementation correction:** pools were first keyed by (base size,
downscale), giving 12 keys where there are only 10 real pixel sizes. They are
now keyed by exact pixel size, as approved. Every slope is ~1.000, so pass/fail
does not change.

## 5. Pilot scores (engineering only, not for publication)

M1 (character error rate, N1):

| Engine | V00 | V05 JPEG q60 | V09 WebP q50 | V11 AVIF q60 | V12 50% | V13 50% + JPEG |
|---|---|---|---|---|---|---|
| doctr | .017 | .019 | .017 | .018 | .040 | .070 |
| paddle_v5_mobile | .022 | .031 | .029 | .020 | .081 | .125 |
| paddle_v5_server | .093 | .033 | .036 | .031 | .086 | .116 |
| easyocr | .061 | .062 | .060 | .062 | .358 | .359 |
| windows_ocr | .081 | .089 | .087 | .082 | .465 | .481 |
| tesseract5 | .135 | .129 | .123 | .125 | .432 | .446 |

Paddle server's V00 value is dominated by one reproducible failure on one
image: it returns 7 of ~65 lines on a lossless dark code-editor render. Only 4
templates, so these numbers don't support any comparison.

## 6. Runtime and storage (unchanged from the previous round)

- **Timing:** the timing pass was not re-run in this round (`run_pilot.py`
  skips it unless `--timing`). The earlier measurements (Paddle server median
  32.8 s per V00 image, others 0.07–8.8 s) came from `m01`/`m05` renders that
  used font features since disabled. They are glyph-level changes only, but
  their effect on runtime is **unmeasured**.
- **Full-run projection** (80 templates): ~4–5 days of machine time on this
  laptop.
- **Storage:** ~1.9 GB publishable.

## 7. Still open

1. **E2:** approve the pooled-by-image-size criterion (§4), or propose another.
   Until then, the pilot does not pass.
2. **Approval of amendments:** A1 (80 templates; bootstrap-t / log rate-ratio),
   A2, A3/A3b, A4 (no human review, synthetic-only, no ligatures).
3. **Decisions:** D1 (Paddle model / MKL-DNN), D2 (cloud / LLM engines),
   D3 (Mac for Apple Vision), D5.
4. **Earlier out-of-scope items:** reading-order sensitivity for multi-column
   predictions, the unreachable U+2033 rule, stress-line wording, middle-dot
   separator, pinned names list.
5. **Commit and tag `prereg-v1.0`.** Nothing is committed.

No step requires a person to inspect images or OCR output.
