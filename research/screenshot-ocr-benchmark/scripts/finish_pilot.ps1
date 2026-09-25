# Runs the remaining pilot passes. Every step is serial (one engine at a time).
# paddle_v5_server is excluded: its accuracy pass was stopped after confirmed
# out-of-memory kills on 2560x1600 images (see PILOT_REPORT.md).
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
$engines = 'tesseract5','windows_ocr','doctr','paddle_v5_mobile','easyocr'
$log = "pilot\logs\finish_pilot.log"

"== serial-check $(Get-Date -Format o)" | Out-File -Append -Encoding utf8 $log
python scripts\run_ocr.py serial-check --engines $engines 2>&1 | Out-File -Append -Encoding utf8 $log
foreach ($e in $engines) {
  "== rerun $e $(Get-Date -Format o)" | Out-File -Append -Encoding utf8 $log
  python scripts\run_ocr.py rerun --engines $e 2>&1 | Out-File -Append -Encoding utf8 $log
}
"== timing $(Get-Date -Format o)" | Out-File -Append -Encoding utf8 $log
python scripts\run_ocr.py timing --engines $engines 2>&1 | Out-File -Append -Encoding utf8 $log
python scripts\run_ocr.py lock 2>&1 | Out-File -Append -Encoding utf8 $log
python scripts\run_ocr.py environment 2>&1 | Out-File -Append -Encoding utf8 $log
"== DONE $(Get-Date -Format o)" | Out-File -Append -Encoding utf8 $log
