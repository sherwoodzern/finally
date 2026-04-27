#!/usr/bin/env bash
# FinAlly stop script (macOS / Linux). Idempotent; preserves named volume.
# Phase 9 / OPS-03 (D-10).

set -eu

CONTAINER_NAME="finally-app"

docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Stopped ${CONTAINER_NAME}. Data preserved in volume 'finally-data'."
echo "To remove the volume too: docker volume rm finally-data"
