#Requires -Version 5.1
Write-Host "=== AURORA Preflight (PS) ==="
if (-not (Test-Path ".venv")) {
  Write-Host "Creating venv..."
  python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
python scripts\preflight.py
