#Requires -Version 5.1
Write-Host "=== AURORA bootstrap ==="

# 1) 기본 도구
choco -v 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Installing Chocolatey..."
  Set-ExecutionPolicy Bypass -Scope Process -Force
  [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
  Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

# 2) Python & Node
choco install -y python --version=3.11.9
choco install -y nodejs-lts

# 3) pip / venv
$py = (Get-Command python).Source
Write-Host "Python path: $py"
python -m pip install --upgrade pip

# 4) 프로젝트 의존성
if (Test-Path requirements.txt) {
  Write-Host "Installing Python deps..."
  pip install -r requirements.txt
}
if (Test-Path pyproject.toml) {
  Write-Host "Editable install..."
  pip install -e .
}

if (Test-Path package.json) {
  Write-Host "Installing Node deps..."
  npm ci
}

Write-Host "Bootstrap complete."
