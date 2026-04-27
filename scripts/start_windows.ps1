# FinAlly start script (Windows PowerShell 5.1+). Idempotent; safe to re-run.
# Phase 9 / OPS-03. Mirrors scripts/start_mac.sh argument-for-argument.

[CmdletBinding()]
param(
  [switch]$Build,
  [switch]$NoOpen
)

$ErrorActionPreference = "Stop"

$ImageName     = "finally:latest"
$ContainerName = "finally-app"
$VolumeName    = "finally-data"
$Port          = 8000

# Resolve repo root regardless of caller cwd.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

# Pre-flight: .env must exist.
if (-not (Test-Path -LiteralPath ".env")) {
  Write-Error ".env not found at $RepoRoot\.env"
  Write-Host  "Hint:  Copy-Item .env.example .env  (then re-run this script)"
  exit 1
}

# Build image if missing or forced (D-09).
docker image inspect $ImageName *> $null
$haveImage = ($LASTEXITCODE -eq 0)

if ($Build -or -not $haveImage) {
  Write-Host "Building $ImageName ..."
  docker build -t $ImageName .
  if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
}

# Stop+remove any prior container (idempotency).
docker stop $ContainerName *> $null
docker rm   $ContainerName *> $null

# Canonical run (PLAN.md section 11 + D-05 + D-06).
docker run -d `
  --name $ContainerName `
  -v "${VolumeName}:/app/db" `
  -p "${Port}:${Port}" `
  --env-file .env `
  $ImageName
if ($LASTEXITCODE -ne 0) { throw "docker run failed" }

Write-Host "FinAlly is starting on http://localhost:${Port}"
Write-Host "Tail logs: docker logs -f $ContainerName"
Write-Host "Stop:      .\scripts\stop_windows.ps1"

# Open browser only on success and only when not suppressed (D-11).
if (-not $NoOpen) {
  Start-Process "http://localhost:${Port}"
}
