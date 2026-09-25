# Screenshot OCR Benchmark

Status: **pilot only.** No benchmark results exist. Nothing under `pilot/` is a
result or may be published; it is engineering validation.

**Scope: synthetic-only.** Images are headless-Chromium renders of our own UI
templates, scored against ground truth generated with each render. The
benchmark makes no claim about OCR on real-device or real-world screenshots
(METHODOLOGY §6).

**No human review.** Every validity check is automated and mutation-tested
([AUTOMATED_VALIDATION.md](AUTOMATED_VALIDATION.md)), and the whole pipeline
runs unattended.

Design documents: [METHODOLOGY.md](METHODOLOGY.md), [PREREGISTRATION.md](PREREGISTRATION.md),
[PILOT_PLAN.md](PILOT_PLAN.md), [AUTOMATED_VALIDATION.md](AUTOMATED_VALIDATION.md),
[SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md). Pilot outcome: [PILOT_REPORT.md](PILOT_REPORT.md).

## Layout

```
templates/            4 pilot templates, _shared/ (base.css, theme.js), _fixtures/ (test pages)
fonts/                pinned OFL font files + fonts.lock.json
docker/               tools (render/variants/score), ocr-paddle, ocr-torch, ocr-tesseract images
scripts/
  run_pilot.py        unattended end-to-end runner (start here)
  fetch_fonts.py      download + hash-pin fonts
  render_chromium.py  renders (normal, text-hidden, canonical, repeat), CDP font/glyph checks, ground truth
  extract.js          in-page geometry + validity evidence
  derive_variants.py  V00–V13 + manifest.jsonl
  downscaled_gt.py    ground-truth boxes measured on the 50% variants
  engines/            engine adapters + worker.py (JSON-lines protocol)
  run_ocr.py          accuracy / serial-check / rerun / timing / environment / lock
  score.py            normalization, matching, metrics M1–M9
  bootstrap.py        cluster bootstrap-t, log rate-ratio tests, Holm, coverage studies
  c6_study.py         interval coverage study (PILOT C6)
  auto_checks.py      automated validity checks A3/A4/A5/B4/E2
  pseudo_engines.py   oracle / perturbed / empty / jitter predictions (C2–C5)
  validate_pilot.py   all pilot checks -> pilot/validation/pilot_checks.{json,md}; exit 1 on any FAIL
  run_tests.py        pytest -> pilot/validation/pytest_results.json
tests/                scorer, bootstrap, extractor, failure-class and mutation tests
pilot/                all pilot outputs
```

## Reproduce (Windows host with Docker Desktop)

One-time setup:

```powershell
cd research/screenshot-ocr-benchmark
foreach ($n in 'tools','ocr-tesseract','ocr-paddle','ocr-torch') { docker build -f docker/$n.Dockerfile -t ocrbench-$($n):pilot . }
python -m venv .venv-winocr
.\.venv-winocr\Scripts\pip install winrt-runtime winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams winrt-Windows.Globalization winrt-Windows.Foundation winrt-Windows.Foundation.Collections pillow==12.3.0 numpy
```

Paddle server needs about 22 GB at 2560×1600, so give the WSL2 VM at least 26 GB
(`%USERPROFILE%\.wslconfig`: `[wsl2]` / `memory=26GB`).

Then run everything, unattended:

```powershell
python scripts/run_pilot.py            # render -> variants -> OCR -> tests -> score -> validate
python scripts/run_pilot.py --timing   # also re-measure runtime (slow)
```

The runner re-runs OCR only for images whose pixels changed, and exits
non-zero if a test or any validation check fails. Engines run one at a time;
running them in parallel oversubscribes the CPU. Linux engines run with
`--network none`, a 24 GB memory cap and baked-in models.
