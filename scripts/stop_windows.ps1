# FinAlly stop script (Windows PowerShell 5.1+). Idempotent; preserves named volume.
# Phase 9 / OPS-03 (D-10).

$ErrorActionPreference = "Stop"

$ContainerName = "finally-app"

docker stop $ContainerName *> $null
docker rm   $ContainerName *> $null

Write-Host "Stopped $ContainerName. Data preserved in volume 'finally-data'."
Write-Host "To remove the volume too: docker volume rm finally-data"
