# Screenshot OCR Benchmark

Status: **pilot only** (PILOT_PLAN.md). No benchmark results exist. Nothing under
`pilot/` is a result or may be published; it is engineering validation.

Design documents: [METHODOLOGY.md](METHODOLOGY.md), [PREREGISTRATION.md](PREREGISTRATION.md),
[PILOT_PLAN.md](PILOT_PLAN.md), [SOURCES_AND_LICENSES.md](SOURCES_AND_LICENSES.md).
Pilot outcome: [PILOT_REPORT.md](PILOT_REPORT.md).

## Layout

```
templates/            HTML/CSS templates (4 pilot templates) + _shared/ + _fixtures/
fonts/                pinned OFL font files + fonts.lock.json (scripts/fetch_fonts.py)
docker/               tools (render/variants/score), ocr-paddle, ocr-torch, ocr-tesseract images
scripts/
  fetch_fonts.py      download + hash-pin fonts
  render_chromium.py  renders, CDP font check, DOM geometry, ink masks, ground truth
  extract.js          in-page geometry extraction
  derive_variants.py  V00–V13 + manifest.jsonl + checks D1–D6
  engines/            engine adapters + worker.py (JSON-lines protocol)
  run_ocr.py          host orchestrator: accuracy / serial-check / rerun / timing / environment / lock
  score.py            normalization, matching, metrics M1–M9
  bootstrap.py        cluster bootstrap, Holm, coverage simulation
  pseudo_engines.py   oracle / perturbed / empty / jitter predictions (C2–C5)
  validate_pilot.py   all pilot checks -> pilot/validation/pilot_checks.{json,md} + review material
  run_tests.py        pytest -> pilot/validation/pytest_results.json
tests/                scorer, bootstrap and extractor tests
pilot/                all pilot outputs (dataset, predictions, scores, validation, review, timing, logs)
```

## Reproduce the pilot (Windows host with Docker Desktop)

```powershell
cd research/screenshot-ocr-benchmark
python scripts/fetch_fonts.py --verify
foreach ($n in 'tools','ocr-tesseract','ocr-paddle','ocr-torch') { docker build -f docker/$n.Dockerfile -t ocrbench-$($n):pilot . }
python -m venv .venv-winocr
.\.venv-winocr\Scripts\pip install winrt-runtime winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams winrt-Windows.Globalization winrt-Windows.Foundation winrt-Windows.Foundation.Collections pillow==12.3.0 numpy

$tools = "docker run --rm --ipc=host -v ${PWD}:/bench -w /bench ocrbench-tools:pilot"
Invoke-Expression "$tools python scripts/render_chromium.py"
Invoke-Expression "$tools python scripts/derive_variants.py"

# OCR: run engines one at a time (running them in parallel oversubscribes the CPU badly)
foreach ($e in 'tesseract5','windows_ocr','doctr','paddle_v5_mobile','easyocr','paddle_v5_server') { python scripts/run_ocr.py accuracy --engines $e }
python scripts/run_ocr.py serial-check
foreach ($e in 'tesseract5','windows_ocr','doctr','paddle_v5_mobile','easyocr','paddle_v5_server') { python scripts/run_ocr.py rerun --engines $e }
python scripts/run_ocr.py timing
python scripts/run_ocr.py lock
python scripts/run_ocr.py environment

Invoke-Expression "$tools python scripts/run_tests.py"
Invoke-Expression "$tools python scripts/pseudo_engines.py"
Invoke-Expression "$tools python scripts/score.py"
Invoke-Expression "$tools python scripts/validate_pilot.py"
```

Linux engines run with `--network none`; all models are baked into the images at build time.
