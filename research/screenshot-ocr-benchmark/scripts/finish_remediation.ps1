# After the paddle_v5_server re-run (26 GB VM, 24 GB container budget): its E3 re-run and
# F timing pass (serial, idle machine), lock/environment, then scoring, validation and
# the human-review package for all engines.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$log = "pilot\logs\finish_remediation.log"
function Log($m) { "== $m $(Get-Date -Format o)" | Out-File -Append -Encoding utf8 $log }

while ((Get-ChildItem pilot\predictions\paddle_v5_server -File -Filter *.json).Count -lt 312) { Start-Sleep -Seconds 30 }
while (Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 'run_ocr.py accuracy' }) { Start-Sleep -Seconds 10 }

Log "serial-check paddle_v5_server"
python scripts\run_ocr.py serial-check --engines paddle_v5_server 2>&1 | Out-File -Append -Encoding utf8 $log
Log "rerun paddle_v5_server"
if (Test-Path pilot\predictions_rerun\paddle_v5_server) { Remove-Item -Recurse -Force pilot\predictions_rerun\paddle_v5_server }
python scripts\run_ocr.py rerun --engines paddle_v5_server 2>&1 | Out-File -Append -Encoding utf8 $log
Log "timing paddle_v5_server"
if (Test-Path pilot\timing\timing.jsonl) { Copy-Item pilot\timing\timing.jsonl pilot\timing\timing_5engines.jsonl -Force }
python scripts\run_ocr.py timing --engines paddle_v5_server 2>&1 | Out-File -Append -Encoding utf8 $log
Move-Item pilot\timing\timing.jsonl pilot\timing\timing_paddle_v5_server.jsonl -Force
Get-Content pilot\timing\timing_5engines.jsonl, pilot\timing\timing_paddle_v5_server.jsonl | Set-Content -Encoding utf8 pilot\timing\timing.jsonl
Log "lock + environment"
python scripts\run_ocr.py lock 2>&1 | Out-File -Append -Encoding utf8 $log
python scripts\run_ocr.py environment 2>&1 | Out-File -Append -Encoding utf8 $log

Log "tests, pseudo, score, validate, review"
$root = (Get-Location).Path
docker run --rm --ipc=host -v "${root}:/bench" -w /bench ocrbench-tools:pilot sh -c "python scripts/run_tests.py; python scripts/pseudo_engines.py && python scripts/score.py && python scripts/validate_pilot.py && python scripts/build_review.py" 2>&1 | Out-File -Append -Encoding utf8 $log
Log "DONE"
