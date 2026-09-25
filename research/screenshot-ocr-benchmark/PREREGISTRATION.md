# Preregistration: Screenshot OCR Benchmark v1

**Status: DRAFT v0.1, not yet registered.** This document becomes binding
only after:

1. every item marked `DECISION` is resolved,
2. the pilot ([PILOT_PLAN.md](PILOT_PLAN.md)) passes, and
3. it is committed and tagged `prereg-v1.0` (and optionally deposited on
   OSF Registries) **before** the full dataset is OCR'd.

After tagging, any change goes into the deviations log (§11) with a reason
and a date.

No results exist at the time of writing. Nothing in this document is a
finding.

Companion documents: [METHODOLOGY.md](METHODOLOGY.md) (full design),
[SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md).

## 1. Research questions

We make **no directional predictions**. All tests are two-sided.

**Confirmatory** (Holm-corrected families, §7.4):

- **RQ1. Engine comparison.** On lossless synthetic screenshots (V00), do
  core Track L engines differ in character error rate (M1)?
- **RQ2. Compression and resize.** For each core engine, does M1 differ
  between V00 and each of: JPEG q60 (V05), WebP q50 (V09), AVIF q60 (V11),
  and 50% downscale (V12)?
- **RQ3. Theme.** For each core engine, on V00, does M1 differ between dark
  and light themes?
- **RQ4. Display scale.** For each core engine, on V00, does M1 differ
  between the lowest and highest scale within each form factor (mobile 1x vs.
  3x; desktop 1x vs. 2x)?

**Descriptive** (estimates with confidence intervals, no hypothesis tests):

- **RQ5. Small-text threshold.** Per engine, the rendered x-height (image px)
  at which the predicted probability of an exactly correct line reaches 0.95
  ("x95").
- **RQ6. Numbers.** Numeric-token accuracy (M7) per engine, overall and per
  variant.
- **RQ7. Real devices.** Agreement between engine rankings on the real-device
  set and on the matching synthetic renders (Kendall τ-b), and the per-engine
  M1 difference.
- **RQ8. Rate vs. accuracy.** M1 as a function of bits per pixel, per format
  family.
- **RQ9. Confusions.** The most frequent character substitution pairs per
  engine.
- **RQ10. Runtime.** Median and p90 per-image time per engine and resolution
  class.

**Exploratory** (labeled as such wherever reported): anything else, including
per-category, per-font, per-contrast breakdowns, preprocessing variants
(for example Tesseract with upscaling), Track T (vision LLMs), and optional
cloud engines if added.

## 2. Dataset construction (fixed)

- **Synthetic set** (template count amended, A1, **pending approval**).
  - **80 templates** (40 mobile at 390×844 CSS px, 40 desktop at 1280×800 CSS
    px). This was 40 in the draft; the pilot's coverage study (§7.2–7.3) found
    the confirmatory intervals reach nominal coverage only at 40 per stratum.
    80 is the maximum the template-count rule below already allowed.
  - Scale factors: mobile {1, 2, 3}, desktop {1, 1.5, 2}. Themes: {light, dark}.
  - That gives **480 base renders**, each with 13 OCR'd variants (V00, V02–V13
    per METHODOLOGY.md §5): **6,240 images**.
  - V01 (lossless WebP) is size-only.
- **Template count rule.** The count may be **increased** (steps of 10, max
  80) after the pilot, if the pilot's template-level variance projects a 95%
  interval half-width for any core engine's V00 M1 greater than
  max(0.2 percentage points, 25% of that engine's pilot M1). It may never be
  decreased. The pilot's variance estimate is the only input to this rule.
- **Real-device set.** 20 templates (10 mobile, 10 desktop) × 2 themes ×
  {iOS Safari, Android Chrome, Windows Edge, macOS Safari*} = 160 images
  (*120 if no Mac is available; `DECISION D3`). Lossless native screenshots
  only.
- **Ground truth.**
  - Text and geometry are extracted from the DOM and ink boxes from
    text/no-text difference renders (synthetic). Device geometry comes from
    fiducial registration, human-verified.
  - Generation, validation and exclusion rules are in METHODOLOGY.md §4–6
    and §8 here.
- **Content.** Written by us, English, Latin script only. Confusable-glyph
  "stress" lines are tagged `stress=true` and **excluded from all
  confirmatory and descriptive metrics** except RQ9.
- **Forbidden inputs.** No user-uploaded images, analytics, production data
  or third-party screenshot datasets.

## 3. Engines and configurations

**Core Track L engines** (confirmatory analyses use exactly these):
`tesseract5`, `paddle_v5_mobile`, `paddle_v5_server`, `easyocr`, `doctr`,
`windows_ocr`.

- Configurations are as listed in METHODOLOGY.md §7, with exact package
  versions, model files and weight hashes frozen in `engines.lock.json` at
  tagging time.
- `DECISION D1`: Paddle recognition model, multilingual PP-OCRv5 or an
  English-specific PP-OCRv5 model if the pinned version ships one. Also:
  whether `enable_mkldnn` follows the library default or the production value.
- No engine receives preprocessing (no resizing, binarization or colour
  inversion) in confirmatory analyses.
- Each engine call has a **900 s hang guard** (amendment A3b; was a 120 s
  failure rule). Output that completes is scored normally however long it
  took; speed is reported separately (M10). Only a call that exceeds the guard,
  or crashes, is an engine failure (§8.3). The 120 s rule would have scored
  `paddle_v5_server`'s 2560×1600 images (~140–240 s each on the reference
  CPU) as wrong answers, making its accuracy depend on host speed.
- Optional engines (`apple_vision`, `google_vision`, `azure_read`,
  `aws_textract`) and Track T (vision LLMs) are **exploratory in v1**. They
  can only be added before tagging (`DECISION D2`).
- Track T prompt, fixed verbatim:
  > Transcribe all text visible in this screenshot exactly as it appears.
  > Output one visual line of text per output line, top to bottom, left to
  > right. Preserve capitalization, punctuation, symbols and numbers exactly.
  > Do not describe the image, add commentary, or correct apparent errors.

  Temperature 0 where supported; 3 runs per image; model ID and date
  recorded.

## 4. Normalization rules

Applied identically to reference and hypothesis strings, in this order.

**N0 (raw).** Strings as produced. No changes.

**N1 (primary):**
1. Unicode NFKC. This also maps compatibility forms, for example
   `…` → `...` and `ﬁ` → `fi`.
2. Delete U+200B, U+200C, U+200D, U+2060, U+FEFF and U+00AD.
3. Map U+2018, U+2019, U+201A, U+201B, U+2032 → `'`.
   Map U+201C, U+201D, U+201E, U+201F, U+2033 → `"`.
   Map U+2010–U+2015 and U+2212 → `-`.
4. Map every Unicode `Zs` character, and tab, to U+0020.
5. Collapse runs of whitespace to one space; strip leading and trailing
   whitespace.
6. Case is **preserved**.

**N2.** N1 followed by Unicode `casefold()`.

**No-whitespace variant (M4).** N1 with every space removed.

**Tokenization** (M5, M7, M9): split N1 text on single spaces. A **numeric
token** is a token containing ≥ 1 character from `0-9`.

## 5. Matching rules and thresholds

Geometry: axis-aligned boxes `[x, y, w, h]` in image px. Quadrilaterals are
converted to their bounding rectangle. Ground-truth geometry is the **ink
box**. For the 50% variants (V12, V13) the ink box is **measured on the
downscaled pixels** (amendment A2): the normal and text-hidden renders are
downscaled with the same filter as V12; a pixel is ink when any channel changes
by more than 16/255, and ink is assigned to lines as at full resolution with a
4 px pad. The threshold excludes faint Lanczos ringing: counting any change
merged adjacent lines' boxes at the smallest text (pilot C5 failed on 4 of 312
images). It is not 0.5 × the
full-resolution box, which the pilot (B5) showed misses the downscaled ink by
up to 6.0 px. V13 shares V12's boxes, just as V02–V11 share V00's.

**5.1 Component matching (Track L text metrics).**
- Edge between ground-truth line *g* and prediction *p* if
  `area(g ∩ p) / min(area(g), area(p)) ≥ τ_c`, with **τ_c = 0.5** (primary)
  and sensitivity values {0.3, 0.7}.
- Connected components of this bipartite graph are the scoring units.
- **Reading order** (within a component, for both sides): sort by box
  vertical centre. Boxes whose vertical centres differ by less than half the
  smaller box height are on the same row, and are ordered by left edge.
  Members are joined with one space.
- Ground-truth lines with no edge are **deletions**: reference = the line,
  hypothesis = empty.
- Predictions with no edge are **insertions**: reference = empty,
  hypothesis = the prediction. The exception is a prediction with ≥ 50% of
  its area inside ignore regions, which is dropped.
- Predictions with empty text after N1 are dropped before matching.

**5.2 One-to-one detection matching (M8).** Greedy by descending IoU;
pairs are accepted when **IoU ≥ 0.5** (primary), with sensitivity values
{0.3, 0.7}. Implementation: `_match_lines` from the existing bench.

**5.3 Track T.** No geometry. Bag-of-words F1 (M9) over the multiset of N1
tokens per image. Page CER uses reference lines in reading order (§5.1 rule)
vs. the hypothesis lines as returned.

## 6. Metric definitions

Let `ed(a, b)` be the Levenshtein distance (unit costs; implementation
`rapidfuzz.distance.Levenshtein`).

- **M1 CER (primary)** for a set of scoring units U (components, deletions
  and insertions within a cell):
  `M1 = Σ_u ed(ref_u, hyp_u) / Σ_u len(ref_u)`, under N1. Micro-averaged:
  longer lines weigh more. Insertion units add to the numerator only.
- **M2, M3, M4.** As M1 under N0, N2 and no-whitespace N1 respectively.
- **M5 WER.** As M1 with tokens in place of characters.
- **M6 line exact-match rate.** The share of (non-stress) ground-truth lines
  whose component has `hyp == ref` under N1. Each component is weighted by its
  number of ground-truth lines.
- **M7 numeric-token accuracy.** Over all numeric reference tokens: correct
  if an identical token exists in the same component's hypothesis token
  multiset (matching consumes the token).
- **M8.** Detection precision = matched / predictions (excluding
  ignore-region drops); recall = matched / ground-truth lines; F1.
- **M9 bag-of-words F1.** Per image: precision and recall of the token
  multiset intersection; cell value = mean over images.
- **M10 runtime.**
  - Wall-clock time of the engine call only (image already decoded in
    memory), after one untimed warm-up.
  - Measured on a **timing subset**: all V00 images of 8 templates, 3
    interleaved repetitions (rep → image → engine), same host for all
    Linux engines. Windows OCR is measured on its own host and reported
    separately.
  - Summary: median and p90, by resolution class (< 1 MP, 1–3 MP, > 3 MP).
- **Confusions (RQ9).** From `rapidfuzz` edit operations on single-GT-line
  components under N1: counts of (reference character → hypothesis
  character) substitutions. The top 20 per engine are reported.
- **x95 (RQ5).** Per engine, on synthetic V00 non-stress lines in
  single-ground-truth-line components:
  - Fit a logistic regression of `exact_n1` on `log2(xheight_px)`.
  - x95 is the x-height where the fitted probability equals 0.95.
  - If it lies outside the observed x-height range, report "not reached
    within [min, max]" rather than extrapolating.

## 7. Statistical methodology

**7.1 Resampling unit.** The template. All images, variants and lines from
one template are resampled together.

**7.2 Intervals** (amended, A1).
- Cluster bootstrap with B = 9,999 resamples of templates, with
  replacement, stratified by form factor (mobile and desktop templates
  resampled separately), seed `20260924`.
- The statistic is recomputed from the pooled units in each resample (not
  averaged across templates).
- **Single-engine rates** (M1 and other ratio metrics): studentized bootstrap
  (bootstrap-t), using the linearized stratified standard error of the pooled
  ratio in the original sample and in every resample.
- The draft's 95% percentile interval was dropped. In the pilot's coverage
  study (C6) it covered only 0.85–0.93 at 20 templates per stratum.

**7.3 Paired comparisons** (amended, A1).
- For contrasts within an engine (RQ2–RQ4) or between engines (RQ1), both
  statistics are computed on the **same** resampled templates in each
  bootstrap iteration.
- **Confirmatory tests use the relative effect**, the rate ratio
  R_a / R_b. The test is a symmetric studentized bootstrap on log(R_a / R_b)
  with a linearized paired SE; the interval is back-transformed;
  `p = P*(|t*| ≥ |t_obs|)` tests H0: R_a = R_b. Holm (§7.4) is applied to these
  p-values.
- **Absolute differences Δ** (percentage points) are still reported (§7.6), with
  a studentized bootstrap interval, but **descriptively only**. The pilot found
  their coverage below nominal (0.910–0.953 at 40 templates per stratum), so the
  results page labels them "approximate; simulated coverage 91–95%" and draws
  no confirmatory conclusion from them.
- If either pooled rate in a contrast is 0 the log ratio is undefined. That
  contrast is then tested with the Δ bootstrap-t interval and flagged.
- **Why, and evidence:** coverage was simulated on 8 synthetic populations
  with known truth (5 used to choose, 3 held out), 2,000 simulations each
  (`pilot/validation/c6_study_*.json`), under selection rules written before
  each round ran (`scripts/bootstrap.py`: `SELECTION_RULE`, `ROUND2_RULE`). At
  40 templates per stratum, bootstrap-t covered 0.933–0.960 and the log-ratio
  method 0.934–0.959 across all 8. At 20 per stratum both failed at least one
  held-out scenario.

**7.4 Multiplicity.** Holm–Bonferroni at family-wise α = 0.05 within each
family:
- **F1 (RQ1):** all 15 pairwise differences among the 6 core engines, M1, V00.
- **F2 (RQ2–RQ4):** per core engine, 7 contrasts (V05, V09, V11 and V12 vs.
  V00; dark vs. light; mobile 1x vs. 3x; desktop 1x vs. 2x) × 6 engines =
  **42 tests**.

**7.5 Practical significance.**
- A difference is described as practically meaningful on the results page
  only if it is Holm-significant **and** |Δ| ≥ max(0.1 percentage points
  CER, 10% of the smaller of the two values).
- Significant differences below that threshold are reported as "detectable
  but small".
- A non-significant result is reported as "no difference detected at this
  sample size", never as "no difference".

**7.6 Effect sizes.** Always report Δ (absolute percentage points) and the
ratio, with 95% intervals. p-values are secondary.

**7.7 RQ7 (devices).**
- Kendall τ-b between engine orderings by M1 on (a) the device set and (b)
  the synthetic V00 renders of the same 20 templates and 2 themes, at the
  scale factor nearest the device's. Bootstrap interval over templates.
- Per-engine Δ(device − synthetic) with intervals.
- Descriptive only; the device set is too small for confirmatory claims.

**7.8 RQ8 (rate vs. accuracy).**
- Plot M1 against mean bits per pixel for JPEG 4:2:0 (V02–V05), WebP
  (V07–V09) and AVIF (V10–V11), with V06 as a single point.
- Comparisons at equal bits per pixel use linear interpolation on
  log(bits per pixel), **only inside the range where formats overlap**.
  They are exploratory.

## 8. Exclusions and data handling

Decided before any data exists:

1. **Ground-truth lines excluded (and logged):**
   - stress lines (all metrics except RQ9);
   - lines with zero ink pixels (expected 0; any occurrence is a generator
     bug to fix before OCR);
   - clipped text, which becomes an ignore region.
2. **Images:** any image failing validation (font fallback, render
   nondeterminism, variant decode failure, dimension mismatch) is **fixed and
   regenerated before OCR**. No image is excluded after OCR output has been
   seen.
3. **Engine failures** (amended, A3): failures are classified from the
   container runtime's own record, not guessed.
   - **Engine failure** — an exception, a crash not caused by the memory budget,
     or a call exceeding the 900 s hang guard (uncontended). Scored as an empty
     prediction (every ground-truth line is a deletion), as before.
   - **Resource failure (`resource_oom`)** — the engine's container is killed
     for exceeding the declared memory budget (Docker `State.OOMKilled`, with
     one automatic retry). This is not an accuracy result: the image is
     **excluded** from that engine's accuracy cells and from any paired
     comparison involving that engine and image; comparisons use the images
     both engines completed. Every exclusion is listed and counted per engine,
     variant and resolution, and reported on the results page as "exceeds the
     memory budget at this resolution".
   - **Infrastructure failure** (daemon or host error unrelated to the engine) —
     the run is invalid and repeated.
   - **Declared budget (reference host):** each Linux engine container is
     limited to 24 GB with swap disabled, inside a 26 GB VM; 20 vCPUs; engines
     run one at a time. Peak resident memory is recorded per image and reported
     per engine as a resource metric (M11).
   - Failure counts per engine and variant are reported. If an engine fails or
     is excluded on more than 5% of images in a cell, that cell is flagged on
     the results page.
4. **Icons:** predictions over SVG icons are **not** ignore regions; reading
   glyphs from an icon is a real error. Sensitivity analysis: M1 recomputed
   with icon-overlapping insertions removed.
5. **No outlier removal** of any kind.
6. **Pilot data:**
   - Pilot OCR outputs and scores are used only for engineering validation
     and the sample-size rule (§2). They are never published as results.
   - Pilot templates remain in the full set, regenerated with the frozen
     generator. This is allowed because engine configurations are frozen
     before the pilot and are not tuned on it.
   - Any pilot-driven change (bug fixes, confirmed misconfigurations) is
     logged.

## 9. Planned analyses and outputs

| Output | Answers | Data |
|---|---|---|
| Main table: M1, M6, M7, M8 F1 per core engine, 95% intervals | RQ1, RQ6 | synthetic V00 |
| Pairwise difference matrix with Holm-adjusted p-values | RQ1 | synthetic V00 |
| Per-engine contrast table (7 contrasts) | RQ2–RQ4 | synthetic |
| Line chart: P(exact) vs. x-height per engine, with x95 markers | RQ5 | synthetic V00 |
| Rate-accuracy chart: M1 vs. bits per pixel per format family and engine | RQ8 | synthetic V02–V11 |
| Grouped bars: M1 by scale factor; M1 by theme | RQ3, RQ4 | synthetic V00 |
| Synthetic vs. device comparison and τ-b | RQ7 | device + matched synthetic |
| Confusion-pair table | RQ9 | synthetic V00 (includes stress) |
| Runtime table | RQ10 | timing subset |
| Sensitivity table: M1 under N0/N2/no-whitespace, τ_c ∈ {0.3, 0.7}, icon-insertion removal | robustness | synthetic V00 |
| Engine failure counts | transparency | all |
| Exploratory appendix (labeled) | — | as run |

## 10. Blinding and analysis freeze

- The scoring code, the summary scripts and this document are tagged
  **before** the full run.
- The full run is scored exactly once with the tagged code.
- The results page publishes the pre-registered outputs **regardless of what
  they show**, including results unfavorable to the engine our product uses
  (`paddle_v5_mobile`).
- Conflict of interest: ScreenshotTextEditor uses PaddleOCR PP-OCRv5 mobile
  in production. This is stated on the results page.
- Before publication, each engine's configuration and its results are sent to
  that engine's maintainers. Confirmed misconfigurations are fixed, the
  affected engine is re-run, and the change is logged as a deviation.

## 11. Deviations log

Pre-registration amendments made **before tagging**, driven by the pilot
(details in PILOT_REPORT.md):

| ID | Date | Section | Change | Reason |
|---|---|---|---|---|
| A1 | 2026-09-24 | §2, §7.2, §7.3 | Bootstrap-t for single-engine intervals; confirmatory paired tests on the log rate ratio (symmetric bootstrap-t); Δ intervals descriptive only; 80 templates (40 per stratum) | Pilot C6: percentile intervals covered 0.85–0.93; no method reached nominal coverage for all scenarios at 20 per stratum |
| A2 | 2026-09-24/25 | §5 | 50%-variant ground-truth boxes measured on downscaled pixels (ink = change > 16/255) | Pilot B5: 0.5 × boxes missed Lanczos-spread ink by up to 6.0 px. The threshold was added after "any change" made C5 fail on 4/312 of the smallest images |
| A3 | 2026-09-24 | §8.3 | Failure classes (engine / `resource_oom` / infrastructure); declared 24 GB container budget; OOM kills excluded, not scored empty; peak memory recorded | Pilot: `paddle_v5_server` was OOM-killed by a 15.5 GB VM on 2560×1600 images; scoring that as engine failure measured the host, not the engine |
| A3b | 2026-09-24 | §3, §8.3 | 120 s timeout-as-failure replaced by a 900 s hang guard; completed output always scored; speed via M10 (owner decision) | With memory fixed, `paddle_v5_server` completes 2560×1600 images in ~140–240 s (peak ~21.7 GB); the 120 s rule would score slowness as wrong answers |

Deviations after tagging:

| Date | Section | Change | Reason | Effect on results |
|---|---|---|---|---|
| (none yet) | | | | |

## 12. Open decisions blocking registration

- `D1` Paddle recognition model variant and MKL-DNN setting (§3).
- `D2` Include optional cloud engines and/or Track T (vision LLMs) in v1?
- `D3` Is a Mac available (Apple Vision engine, macOS Safari device captures)?
- `D4` Which physical devices, OS and browser versions for the device set?
- `D5` Accept the reciprocal-benchmarking conditions (Google, AWS,
  Microsoft) if cloud engines are included?
