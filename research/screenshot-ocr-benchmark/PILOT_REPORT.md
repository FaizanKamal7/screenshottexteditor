# Pilot report: Screenshot OCR Benchmark

Status (2026-09-25): **pilot complete, remediation of C6, B5 and the Paddle-server
issue complete.** All automated checks pass. Still open before any full run: a
human review, the device set, and your approval of the amended design (§8).
Accuracy numbers here come from 4 templates, are **not benchmark results**, and
must not be published or quoted.

Machine-readable outputs: `pilot/validation/pilot_checks.json`,
`pilot/validation/c6_study_*.json`, `pilot/scores/`, `pilot/timing/timing.jsonl`,
`pilot/engines.lock.json`, `pilot/environment/environment.json`.

## 1. What was run

| Item | Count |
|---|---|
| Templates | 4 (`m01-settings`, `m05-chat`, `d01-dashboard`, `d06-code-editor`) |
| Base renders / ground-truth lines | 24 / 1,074 |
| OCR'd images (V00, V02–V13) | 312 (+24 size-only V01) |
| Engines completed on all 312 images | **6**: `tesseract5`, `windows_ocr`, `doctr`, `paddle_v5_mobile`, `easyocr`, `paddle_v5_server` |
| Scored predictions | 1,872 (6 × 312), 0 failures, 0 exclusions |
| Determinism re-runs | 31 images × 6 engines = 186, 0 differences |
| Timing measurements | 24 V00 images × 3 reps × 6 engines = 432 |
| Device captures | 0 (§6) |

Host: Intel i9-13900H (14 cores / 20 threads), 31.8 GB RAM, Windows 11. Linux
engines ran one at a time in Docker Desktop: WSL2 VM raised to 26 GB (with your
approval; `C:\Users\faiza\.wslconfig`), each engine container capped at 24 GB
with no swap, `--network none`. Windows OCR ran natively.

## 2. Remediation

### C6: interval coverage (amendment A1)

Selection rules were written into `scripts/bootstrap.py` **before** each study
ran. Coverage was measured on synthetic populations with known truth, 2,000
simulations each, target band [0.93, 0.97].

| Round | Setting | Outcome |
|---|---|---|
| 1 | 4 methods × 5 scenarios, 20 templates/stratum | Nothing passed. Percentile (the draft method) 0.85–0.93. Bootstrap-t good for single rates (0.941–0.952) but not for paired differences (0.89–0.93) |
| 2 | New candidates + **3 held-out scenarios**, 20/stratum | Nothing passed all 8 scenarios. Best two methods failed only the held-out scenario with extreme template-length spread (H2) |
| At 40/stratum | Same methods, all 8 scenarios | **Single-engine bootstrap-t: 0.933–0.960. Log rate-ratio symmetric bootstrap-t: 0.934–0.959. Both pass.** Absolute differences still 0.910–0.953 |

Adopted:
- **Intervals:** bootstrap-t for single-engine rates.
- **Engine comparisons:** confirmatory tests on the relative effect
  (rate A ÷ rate B, log scale), with Holm applied to those p-values.
- **Absolute differences:** reported descriptively, labelled with their
  simulated coverage.
- **Templates:** **80 (40 per stratum)**, the maximum the preregistered
  template rule already allowed. **This needs your approval:** it doubles
  template authoring and full-run time.
- **Context:** real pilot templates hold 302–1,202 reference characters each,
  much closer to the uniform scenarios than to H2's 30–40,000.

### B5: 50%-variant boxes (amendment A2)

- **Before:** boxes for V12/V13 were 0.5 × the full-resolution boxes. The
  pilot showed these missed the downscaled ink by up to 6.0 px.
- **Now:** boxes are measured on the downscaled pixels themselves
  (`scripts/downscaled_gt.py`), with the same ownership logic as at full
  resolution.
- **Follow-up:** the first version counted any changed pixel as ink. That
  merged adjacent lines' boxes at the smallest text and made C5 (box-jitter
  robustness) fail on 4 of 312 images. Ink is now a change above 16/255, the
  threshold fixed for the original B5 check before its results were seen.
- **Result:** all 24 V12 files are pixel-identical to the downscale the boxes
  were measured on; zero unowned ink; every line has ink; C5 passes on 312/312.
- **Scope:** full-resolution ground truth is unchanged (verified semantically
  identical after a refactor). No OCR re-run was needed.

### Paddle server (amendments A3, A3b)

- **Failure classes:** out-of-memory kills are now identified from Docker's own
  `OOMKilled` record, not inferred. A kill at the declared 24 GB budget is a
  `resource_oom`: excluded from accuracy and reported, not scored as empty
  output. Genuine engine errors are still scored empty. Peak memory is recorded
  per image.
- **Hang guard (your decision):** the 120 s timeout-as-failure became a 900 s
  hang guard. Paddle server's 2560×1600 images take ~140–240 s on this CPU, and
  the old rule would have scored that slowness as wrong answers.
- **Result:** 312/312 images completed with 0 errors and 0 exclusions.

Peak memory and time grow with image size:

| Image size | Mean time | Peak memory |
|---|---|---|
| 0.33 MP (mobile 1x) | 7.9 s | 3.1 GB |
| 1.02 MP (desktop 1x) | 27.7 s | 6.6 GB |
| 2.96 MP (mobile 3x) | 53.5 s | 16.5 GB |
| **4.1 MP (desktop 2x)** | **154 s (max 238 s)** | **22.1 GB of the 24 GB budget** |

- **Memory headroom:** only about 2 GB at the largest size. Anything larger
  would be excluded under A3.
- **One reproducible failure:** on `d06-code-editor_dpr2_dark_V00`
  (lossless), Paddle server returns only the 7 status-bar lines. Two fresh
  re-runs on identical pixels gave the same 7 lines, while its JPEG/WebP
  variants return 65. That is engine behaviour, not a pipeline fault, so it
  stays in the scores. It alone accounts for most of Paddle server's pilot V00
  CER (§4).

### Human-review preparation

- **Review page:** `pilot/review/index.html` has 381 items: A3 24, A4 269,
  A5 12, B4 52, E2 24. You answer Agree/Disagree with a note; answers stay in
  your browser until you export a CSV.
- **Guide:** `pilot/review/REVIEW_GUIDE.md` covers the colour key, per-check
  questions, pass criteria (unchanged) and time (~1.5 h).
- **Ingest:** `scripts/ingest_review.py` turns exported CSVs into check results;
  `validate_pilot.py` then uses them.

## 3. Check results (from `pilot/validation/pilot_checks.json`)

| Check | Result |
|---|---|
| A1, A2, A6, A7 | PASS |
| A3, A5 | Automated PASS; **human review pending** |
| A4 | **Human review pending** |
| B1, B2, B3 | PASS |
| B4 | **Human review pending** |
| B5 | **PASS** (was FAIL) |
| B6 | **NOT RUN** (§6) |
| C1–C5, C7 | PASS (39/39 tests) |
| C6 | **PASS at the amended 40 templates/stratum** (was FAIL) |
| D1–D6 | PASS |
| E1 | **PASS** (was FAIL): 6 × 312 attempted, 0 failures |
| E2 | PASS automated (median IoU 0.60–0.98); **human review pending** |
| E3 | **PASS** (was FAIL): 186 re-runs, 0 differences |
| E4, E5, E6 | PASS |
| F1 | Measured (§5) |
| F2 | Unexplained host variance, recorded (§5) |
| G1, G2 | Measured (§5) |
| Sample-size rule | Not informative from this pilot; moot (see below) |

On the sample-size rule: bootstrap-t is ill-posed with 2 templates per stratum,
because resamples that pick the same template twice have zero SE. It produced
meaningless half-widths (e.g. 7.1). The rule can only increase the template
count, and A1 already sets the maximum, so it can't change the design.

## 4. Pilot scores (engineering only, not for publication)

M1 (character error rate, N1) by variant:

| Engine | V00 | V05 (JPEG q60) | V09 (WebP q50) | V11 (AVIF q60) | V12 (50%) | V13 (50% + JPEG) | M7 numeric @V00 |
|---|---|---|---|---|---|---|---|
| doctr | .018 | .019 | .017 | .018 | .040 | .071 | .977 |
| paddle_v5_mobile | .022 | .031 | .029 | .020 | .081 | .124 | .899 |
| paddle_v5_server | .093 | .033 | .035 | .031 | .087 | .117 | .810 |
| easyocr | .061 | .062 | .061 | .061 | .358 | .360 | .562 |
| windows_ocr | .081 | .090 | .087 | .082 | .466 | .482 | .740 |
| tesseract5 | .135 | .129 | .124 | .125 | .433 | .446 | .678 |

Paddle server's V00 is inflated by the single reproducible failure in §2. It is
a clear example of why intervals are clustered by template: one template-image
can dominate a 4-template pilot.

## 5. Runtime and storage

Uncontended, per V00 image (timing pass, 3 reps):

| Engine | Median | p90 | Fitted s/MP |
|---|---|---|---|
| windows_ocr | 0.07 s | 0.12 s | 0.02 |
| tesseract5 | 0.90 s | 1.70 s | 0.29 |
| doctr | 2.20 s | 3.61 s | 0.19 |
| easyocr | 6.62 s | 12.87 s | 3.12 |
| paddle_v5_mobile | 8.82 s | 15.51 s | 2.76 |
| paddle_v5_server | 32.8 s | 71.3 s | 17.96 |

**F2:** repeated timings of the same image varied up to CV 0.32 for Paddle
server at 4.1 MP (56–121 s) and CV 0.51 for Windows OCR (±59 ms on ~0.1 s
calls). There was no trend with rep order. The likely causes are laptop thermal
throttling under sustained load and memory pressure (22 GB peak in a 26 GB VM),
but neither is confirmed. Runtime numbers from this laptop should be treated as
indicative.

**Full-run projection at the amended 80 templates (6,240 images, 20× pilot):**

| Pass | Estimate |
|---|---|
| Accuracy, five engines | ~34 h |
| Accuracy, Paddle server | ~58–81 h (timing fit vs. the observed 4.03 h pilot pass × 20) |
| Determinism and timing passes | +~10% |
| **Total** | **roughly 4–5 days of continuous machine time** on this laptop |

A desktop or cloud machine with more cores and RAM would shorten this
substantially.

**Storage:** 124 MB for the whole pilot (96 MB publishable), so the full run
projects to about 1.9 GB publishable. Ship it as archives or Parquet/JSONL:
Zenodo allows 100 files per record, Hugging Face 10k files per folder.

## 6. Still open

1. **Human review** (A3, A4, A5, B4, E2): ~1.5 h with the prepared page.
2. **B6 / RQ7 device set:** not built. There is no evidence yet that the
   synthetic results transfer to real devices.
3. **Approval of the 80-template design** (A1) and of amendments A2, A3 and A3b
   as written in PREREGISTRATION §11.
4. **Decisions D1–D4.** D5 is moot unless cloud engines are added.
5. **Items from the first pilot report outside this round's scope:**
   reading-order sensitivity for multi-column predictions (§4.5 of the
   previous report), the unreachable U+2033 normalization rule, the stress-line
   wording, the middle-dot separator, and the pinned names list.
6. **Commit and tag `prereg-v1.0`.** Nothing is committed.

## 7. Change log

| # | Change |
|---|---|
| P1–P7 | First pilot round: fresh-paint hidden render, ligature guard, `font-variant-caps`, m05 chip fix, serial engines, `rapidfuzz` in `services/pipeline/bench`, BOM-tolerant worker |
| P8 | `.wslconfig` created: `memory=26GB` (approved; delete the file to restore defaults) |
| P9 | Worker records per-image peak RSS; orchestrator caps containers at 24 GB, reads `OOMKilled`, classifies `resource_oom` |
| P10 | Old Paddle server predictions (15.5 GB VM run) moved to `pilot/superseded/`; full re-run |
| P11 | Scorer uses measured half-resolution boxes and excludes `resource_oom` images |
| P12 | Timeout → 900 s hang guard (your decision) |
| P13 | `timing.jsonl` merge wrote a UTF-8 BOM that crashed validation; stripped, and the reader made BOM-tolerant |

## 8. Is the pilot ready for the full benchmark?

**Not yet.** The three fixes are done and every automated check passes, but the
plan's own go/no-go criteria still require:
- a completed human review;
- a decision on the device set (B6), either building it or formally scoping the
  benchmark as synthetic-only;
- your approval of the amended design;
- committing and tagging the preregistration.

The biggest practical consequence of the fixes is cost. At 80 templates, the
full run is about 4–5 days of machine time on this laptop, and the full
template set doubles to 80.
