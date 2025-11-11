# 개발 모드 동시 실행(백엔드 + 프론트 / 또는 윈도우 클라이언트)
param(
  [switch]$BackendOnly,
  [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"

# .env 로드
if (Test-Path .env) {
  Get-Content .env | ForEach-Object {
    if ($_ -match "^\s*#") { return }
    if ($_ -match "^\s*$") { return }
    $name, $value = $_.Split("=",2)
    [System.Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
  }
}

$jobs = @()

if (-not $FrontendOnly) {
  if (Test-Path "backend\main.py") {
    $jobs += Start-Job -ScriptBlock { python backend\main.py --dev }
  } elseif (Test-Path "server\main.py") {
    $jobs += Start-Job -ScriptBlock { python server\main.py --dev }
  } else {
    Write-Host "[dev] Python backend not found - skipping"
  }
}

if (-not $BackendOnly) {
  if (Test-Path "package.json") {
    $jobs += Start-Job -ScriptBlock { npm run dev }
  } elseif (Test-Path "aurora-win\*.sln") {
    # .NET 솔루션이 있는 경우: 필요 시 빌드/실행 명령으로 교체
    Write-Host "[dev] Found .sln - please run via Visual Studio or add run script"
  } else {
    Write-Host "[dev] Frontend/Windows client not found - skipping"
  }
}

Write-Host "Dev processes started. Press Ctrl+C to stop."
Wait-Job -Any | Out-Null
