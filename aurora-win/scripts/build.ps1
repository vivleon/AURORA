# 배포 빌드(웹 빌드 + 선택적 패키징)
$ErrorActionPreference = "Stop"

if (Test-Path package.json) {
  npm ci
  npm run build
}

# Python 패키징(옵션)
if (Test-Path pyproject.toml) {
  python -m pip install build
  python -m build
}

# Windows 클라이언트(Electron/TAURI/.NET)에 따른 패키징 훅은 추후 실제 구성에 맞춰 추가
Write-Host "Build pipeline complete."
