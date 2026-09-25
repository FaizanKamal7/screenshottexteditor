# Pilot report: Screenshot OCR Benchmark

Status: **pilot complete (2026-09-24). Not ready for the full benchmark** (§8).
This is engineering validation. Accuracy numbers below come from 4 templates,
are **not benchmark results**, and must not be published or quoted.

Machine-readable outputs: `pilot/validation/pilot_checks.json` (every check),
`pilot/scores/` (raw and summarized scores), `pilot/timing/timing.jsonl`,
`pilot/engines.lock.json`, `pilot/environment/environment.json`.

## 1. What was run

| Item | Count |
|---|---|
| Templates | 4 (`m01-settings`, `m05-chat`, `d01-dashboard`, `d06-code-editor`) |
| Base renders (template × scale × theme) | 24 |
| Ground-truth lines | 1,074 |
| OCR'd images (V00, V02–V13) | 312 (+24 size-only V01) |
| Engines completed on all 312 images | 5: `tesseract5`, `windows_ocr`, `doctr`, `paddle_v5_mobile`, `easyocr` |
| `paddle_v5_server` | Stopped after 70 images: 54 ok, 16 out-of-memory kills (§4.1) |
| Scored predictions | 1,630 (5 × 312 + 70) |
| Determinism re-runs | 31 images × 5 engines = 155 |
| Timing measurements | 24 V00 images × 3 reps × 5 engines = 360 |
| Device captures | 0 (§4.4) |

Host: Intel i9-13900H (14 cores / 20 threads), 31.8 GB RAM, Windows 11.
Linux engines ran in Docker Desktop (WSL2 VM: 20 CPUs, 15.5 GB RAM),
`--network none`, models baked into images. Windows OCR ran natively.

## 2. Go / no-go checks

| Check | Result | Notes |
|---|---|---|
| A1 font fallback | **PASS** | 0 fallback nodes in 24 bases (CDP) |
| A2 render determinism | **PASS** | 24/24 pixel-identical; 18 untouched bases also byte-identical across two independent render runs |
| A3 completeness | Automated PASS, **human review pending** | Token reconciliation vs `innerText` exact on 24/24; overlays in `pilot/review/gt_overlays/` |
| A4 line text correctness | **Human review pending** | Sheets in `pilot/review/line_sheets/`, sample in `pilot/review/line_sample.csv` |
| A5 wrapping | Automated PASS, **human review pending** | |
| A6 whitespace | **PASS** | Chromium fixture test, 2/2 |
| A7 ignore regions | **PASS** | After fix P4, clipped chip → one ignore region per `m05` base, scaled exactly with DPR |
| B1 scale consistency | **PASS** | Worst layout deviation 0.001 px·k, worst ink 2.0 px·k (limit 2) |
| B2 ink containment | **PASS** | 0 ink pixels outside every padded line box |
| B3 ink non-empty | **PASS** | 1,074/1,074 lines |
| B4 overlays | **Human review pending** | 24 base overlays + 28 variant overlays (2 bases × 14 files) generated |
| B5 downscale boxes | **FAIL** (see §4.3) | Box transform is exact; measured half-res ink extends up to 3.5 px beyond 0.5 × boxes on 162/1,074 lines |
| B6 device registration | **NOT RUN** (§4.4) | |
| C1 unit tests | **PASS** | 24 scorer + 6 bootstrap + 2 extractor tests |
| C2 oracle | **PASS** | M1 = 0, M6 = M7 = F1 = 1 on 312/312 images |
| C3 perturbed oracle | **PASS** | 18,752 injected edits scored as exactly 18,752 |
| C4 empty engine | **PASS** | M1 = 1.0, recall 0 on 312/312 |
| C5 box jitter | **PASS** | Component partitions unchanged on 312/312 |
| C6 bootstrap coverage | **FAIL** (see §4.2) | Validator's 200-sim run gave 0.91 (edge of band); 2,000 sims give 0.908 ± 0.007 |
| C7 scorer determinism | **PASS** | 16/16 output files byte-identical across two runs |
| D1–D6 variants | **PASS** | 336 files; subsampling verified from JPEG headers |
| E1 coverage | **FAIL** | `paddle_v5_server` 70/312 attempted; other 5 engines 312/312, 0 errors |
| E2 coordinate sanity | PASS, **human review pending** | Median IoU 0.60–0.98 (threshold 0.3) |
| E3 determinism | **FAIL (incomplete)** | 5 engines: 0 of 31 re-run images differ. `paddle_v5_server` not re-run |
| E4 version lock | **PASS** | Versions, configs, weight hashes, tessdata commit, image IDs |
| E5 identical inputs | **PASS** | File and decoded-pixel hashes match manifest for every OK prediction |
| E6 Windows host inputs | **PASS** | 312/312 pixel hashes match Linux decoding despite a different libjpeg build |
| F1 runtime model | MEASURED (§5) | |
| F2 timing stability | Investigated: **acceptable** | Only `windows_ocr` > 20% CV; its SD is ≤ 59 ms on ~70–130 ms calls (timer-scale noise), not machine load |
| G1 storage | MEASURED (§6) | |
| G2 host limits | Checked (§6) | |
| Sample-size rule (§2 prereg) | Applied, **no increase indicated** | Caveat: pilot has 2 templates per stratum, and C6 shows the intervals are too narrow |

PILOT_PLAN §5 go / no-go:

| Criterion | Met? |
|---|---|
| 1. A, B, C all pass; D and E pass or fixed | **No**: B5, C6, E1, E3 fail; B6 not run; A3/A4/A5/B4 await a human |
| 2. Runtime and storage projections accepted | Needs your decision (§5, §6) |
| 3. Sample-size rule applied | Yes (with caveat) |
| 4. Decisions D1–D5 resolved | **No** |
| 5. Committed and tagged `prereg-v1.0` | **No** (you asked me not to commit) |

## 3. Pilot scoring results (engineering only, not for publication)

V00, 24 images per engine, 4 templates:

| Engine | M1 CER | M3 CER (casefold) | M5 WER | M6 exact lines | M7 numeric | M8 F1@0.5 | M9 BoW F1 | Failures |
|---|---|---|---|---|---|---|---|---|
| doctr | 0.018 | 0.016 | 0.077 | 0.830 | 0.977 | 0.715 | 0.948 | 0 |
| paddle_v5_mobile | 0.022 | 0.018 | 0.129 | 0.843 | 0.899 | 0.641 | 0.915 | 0 |
| easyocr | 0.061 | 0.060 | 0.296 | 0.588 | 0.562 | 0.694 | 0.811 | 0 |
| windows_ocr | 0.081 | 0.079 | 0.248 | 0.670 | 0.740 | 0.904 | 0.860 | 0 |
| tesseract5 | 0.135 | 0.134 | 0.270 | 0.557 | 0.678 | 0.637 | 0.829 | 0 |
| paddle_v5_server | 0.345 | — | — | — | — | — | — | 2 of 6 images (OOM) |

The `paddle_v5_server` row is **invalid**. It covers only `d01-dashboard`, and
2 of its 6 V00 images are out-of-memory kills scored as empty output. It shows
the bias in §4.1; it says nothing about the engine.

M1 by variant:

| Engine | V00 | V02 | V03 | V04 | V05 | V06 | V07 | V08 | V09 | V10 | V11 | V12 | V13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| doctr | .018 | .017 | .017 | .018 | .019 | .018 | .018 | .017 | .017 | .017 | .018 | .040 | .071 |
| paddle_v5_mobile | .022 | .020 | .024 | .028 | .031 | .023 | .021 | .026 | .029 | .020 | .020 | .081 | .123 |
| easyocr | .061 | .062 | .061 | .061 | .062 | .061 | .061 | .059 | .061 | .062 | .061 | .359 | .363 |
| windows_ocr | .081 | .080 | .083 | .083 | .090 | .082 | .080 | .087 | .087 | .081 | .082 | .466 | .482 |
| tesseract5 | .135 | .119 | .119 | .137 | .129 | .129 | .119 | .118 | .124 | .123 | .125 | .433 | .446 |

Scorer behaviour visible in these numbers:
- Split and merged lines are not penalized. M9 (order-agnostic) and M1 broadly agree for 4 engines, with one exception (§4.5).
- Most errors are genuine misreads, confirmed by reading the largest error units: `0`→`θ` (Paddle), `()`→`O` and `{`→`f` (docTR), `$`→`S` (EasyOCR), `m`→`n` (Tesseract).
- Tesseract's errors are mostly whole-line deletions: 1,201 of 2,183 edits at V00.
- The confusion table also shows a template content issue: the middle dot `·` (U+00B7) is read as `-` or `•` by several engines (§4.6).

## 4. Problems found

### 4.1 Out-of-memory kills are scored as engine failures (methodology problem)

`paddle_v5_server` was killed by the Docker VM's kernel on every 2560×1600 image
(16/16). `dmesg` shows `Out of memory: Killed process … anon-rss ≈ 15.4 GB`
against a 15.5 GB VM (28 kills; `pilot/logs/paddle_v5_server_oom_dmesg.txt`).
All 54 images at 2.3 MP or below succeeded. The 3.0 MP mobile images were never
attempted.

PREREGISTRATION §8.3 scores a crash as an empty prediction. For out-of-memory
kills, that scores **our test host's memory limit**, not the engine. I stopped
the run instead of producing more of these failures. Options:

- (a) Raise the WSL2 memory limit (`.wslconfig`, e.g. 26 GB of the 31.8 GB host)
  and re-run `paddle_v5_server`. This changes your machine's configuration, so
  it's your call.
- (b) Amend §8.3: an infrastructure out-of-memory kill invalidates the run,
  which is repeated on a larger host. Record peak memory per engine.
- (c) Drop `paddle_v5_server` from the core set.

### 4.2 Bootstrap intervals under-cover (C6 fails)

The preregistered percentile cluster bootstrap was checked on a synthetic
population with known truth (skewed per-template error rates):

| Templates per stratum | Coverage (2,000 sims) |
|---|---|
| 10 | 0.903 |
| 20 (planned) | 0.908 ± 0.007 |
| 40 | 0.928 |

A linearised stratified t-interval, tested as a diagnostic, also under-covers:
0.927 at 20 per stratum. The preregistered "95% intervals" would really be
about 91% intervals, and Holm-adjusted tests would be anti-conservative. The
cause is few clusters combined with skewed rates, so there's no drop-in fix.
Candidates, each to be re-checked with this simulation before registration:

- BCa or bootstrap-t intervals;
- intervals on a log/logit scale;
- more templates;
- stating the achieved coverage honestly.

Results are in `pilot/validation/c6_extended.json`.

### 4.3 Downscaled ground-truth boxes are tighter than the real ink (B5)

The scorer scales V00 ink boxes by exactly 0.5 for V12/V13. Measured on real
pixels, Lanczos resampling spreads ink by up to 3.5 half-res pixels:

- 162 of 1,074 lines exceed ±1 px at a 16/255 threshold;
- every line exceeds it at a threshold of any change.

This mainly lowers IoU-based detection metrics (M8) on V12/V13. The component
matching (τ_c on overlap/min-area) is less affected. Options: accept this and
state it, or derive V12/V13 boxes from downscaled ink masks. It's a
methodology choice, so I haven't changed anything.

### 4.4 No real-device captures (B6, RQ7)

No iOS, Android or macOS devices were available to this session. A Windows Edge
capture would have meant driving your desktop, so I didn't do it. The collector
and fiducial-registration scripts are not written. RQ7 (synthetic vs. real
rendering) cannot be answered until this exists, and the pilot has no evidence
yet that the synthetic results generalize. That is the main external-validity
risk.

### 4.5 Reading-order sensitivity in multi-line components

When an engine returns one box spanning several columns (Tesseract in the code
editor: gutter number + code + docs pane), component matching joins GT lines
from different columns, and CER then depends on reading order. For Tesseract,
components with 3 or more GT lines hold 10.3% of reference characters but 20.3%
of edits. Excluding them moves M1 from 0.135 to 0.120. docTR is affected by
0.7% of edits; Paddle mobile and Windows OCR not at all. M4 and M9 provide
order-agnostic views. Consider adding an order-agnostic CER sensitivity row to
§9 of the preregistration.

### 4.6 Smaller items

- **Unreachable normalization rule.** PREREGISTRATION §4 N1 maps U+2033 → `"`,
  but NFKC runs first and turns U+2033 into two U+2032, which become `''`. The
  test pins the actual behaviour; fix the wording.
- **Stress lines.** Stress lines are excluded from headline metrics by treating
  them as ignore regions. The preregistration implies this but doesn't say it.
- **Middle dot.** Templates use `·` as a separator; engines plausibly read `-`
  or `•`. Either keep it as legitimate (it is a real UI glyph) or avoid
  visually ambiguous separators. Decide before building the other 36 templates.
- **D1 still open.** Paddle used the multilingual recognition model with
  `enable_mkldnn=False` (the production values).
- **Names list not pinned.** Template names were hand-written; the pinned
  public-domain name list is still to be chosen.

### 4.7 Fixed during the pilot (logged, PREREGISTRATION §8.6)

| # | Change | Why |
|---|---|---|
| P1 | Text-hidden render is a separate fresh page load | Injecting CSS into a painted page re-rasterized rounded corners, leaking 25–32 non-text pixels into ink masks at 1x |
| P2 | Ligatures disabled in the code template; automated guard added | JetBrains Mono drew `=>` as one arrow glyph, so rendered text ≠ DOM text. Add this rule to METHODOLOGY §3 |
| P3 | `font-variant-caps` instead of the `font-variant` shorthand | The shorthand silently undid P2; the guard caught it |
| P4 | `m05-chat` chip text shortened | The clipped test chip was fully off-screen at 1x, so A7 wasn't exercised. 84 files regenerated; the 156 predictions made on the old images were deleted and re-run |
| P5 | Engines run one at a time | Parallel engines oversubscribed the CPU: EasyOCR took 340 s on one image under contention and 4.8 s alone. Contended timings are not used |
| P6 | `services/pipeline/bench` switched to `rapidfuzz` | GPL removal; identical distances on 20,000 random pairs |
| P7 | Worker tolerates a UTF-8 BOM on requests | PowerShell pipes add one; the orchestrator never sends it |

Record-keeping note: docTR predictions written before P5's labelling fix say
`conditions: parallel` even for the single-engine part of its run. Accuracy
outputs are unaffected; only that metadata field is imprecise.

## 5. Actual runtime

Uncontended, from the timing pass (3 interleaved reps, V00):

| Engine | Median s/image | p90 | Fitted s per MP | Projected full accuracy pass (3,120 images) |
|---|---|---|---|---|
| windows_ocr | 0.07 | 0.12 | 0.02 | 0.06 h |
| tesseract5 | 0.90 | 1.70 | 0.29 | 0.9 h |
| doctr | 2.20 | 3.61 | 0.19 | 2.1 h |
| easyocr | 6.62 | 12.87 | 3.12 | 5.6 h |
| paddle_v5_mobile | 8.82 | 15.51 | 2.76 | 8.2 h |
| paddle_v5_server | 10.6 s (0.26 MP) to 45.3 s (2.3 MP), single-engine accuracy pass | — | ≈17 | roughly 30 h, **if** given enough memory |

Wall-clock of the uncontended pilot passes:

| Pass | Time |
|---|---|
| Rendering (24 bases) | 36 s |
| Variants | 5.3 min |
| Determinism re-runs | 10 min |
| Timing pass | 26 min |
| Tesseract accuracy (312 images) | 62 s |
| Windows OCR accuracy | 9 s |

The docTR, Paddle mobile and EasyOCR accuracy passes were partly re-run after
P4/P5, so their logged wall-clock times are not single clean runs.

**Full benchmark projection:** about 17 CPU-hours for the five working engines,
plus about 30 h for `paddle_v5_server` (with memory fixed), plus timing and
determinism passes. That is **≈ 2–2.5 days of machine time** on this laptop,
run serially. The pre-pilot estimate was 16–160 h.

## 6. Storage

| Artifact | Pilot |
|---|---|
| Images, all 14 variants | 34.2 MB |
| Source renders / text-hidden renders / masks / ground truth | 3.2 / 0.4 / 0.3 / 0.6 MB |
| Predictions (+ re-runs) | 11.2 MB (+1.0 MB) |
| Scores | 42.2 MB |
| **Pilot total** | **111 MB** (88 MB publishable) |
| **Full projection (×10, excluding device set)** | **≈ 0.9 GB** publishable |

The pre-pilot estimate was 0.5–4 GB. Host limits:
- **Zenodo:** 100 files and 50 GB per record, so the dataset must ship as a few
  archives, not ~3,400 loose images and ~20,000 prediction files.
- **Hugging Face:** under 10k files per folder, so ship Parquet/JSONL shards.

## 7. Engine consistency

- **Determinism:** 5 engines gave identical text and boxes on all 31 re-run
  images, including after switching between parallel and single-engine
  scheduling.
- **Identical inputs:** every OK prediction's file and decoded-pixel hashes match
  the manifest across three Linux images and the Windows host. That includes
  JPEG/WebP/AVIF decoding, even though Windows Pillow reports a different
  libjpeg version.
- **Timing stability:** CV ≤ 14% for 4 engines. Windows OCR's CV is
  proportionally high, but its absolute spread is ≤ 59 ms.
- **Box geometry:** median IoU against ground-truth ink boxes ranges 0.60–0.98.
  No coordinate-mapping bugs; the engines simply draw looser or tighter boxes.

## 8. Is the pilot ready to proceed?

**No.** The pipeline itself works:
- ground truth is exact and deterministic;
- the scorer is validated exactly;
- variants are verified;
- engine inputs are identical everywhere;
- runtime and storage are measured and modest.

But these block the full run under the plan's own rules:

1. **C6:** the interval method needs replacing and re-validating (§4.2).
2. **Paddle server memory:** decide between options (a), (b) and (c) in §4.1,
   then re-run E1, E3 and F for it.
3. **B6/RQ7:** no device pipeline and no device captures (§4.4).
4. **Human review:** A3, A4, A5, B4 and E2 need a person to look at `pilot/review/`.
5. **B5 and §4.5:** decide how to handle downscaled boxes and reading-order sensitivity.
6. **D1–D5, the §4.6 wording fixes, then commit and tag `prereg-v1.0`.**

Estimated work before a full run can start: C6 re-design and simulation (hours);
memory fix and Paddle server re-run (~1 h plus its passes); device collector and
capture of 16 pilot device images (1–2 days, needs devices); human review
(about 2–3 hours of reading). The full run itself then takes about 2–2.5 days of
machine time.
