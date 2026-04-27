#!/usr/bin/env bash
# FinAlly start script (macOS / Linux). Idempotent; safe to re-run.
# Phase 9 / OPS-03. Wraps the canonical docker run from PLAN.md section 11.

set -euo pipefail

IMAGE_NAME="finally:latest"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT=8000

# Parse flags (no associative arrays - bash 3.2 compatible).
FORCE_BUILD=0
NO_OPEN=0
for arg in "$@"; do
  case "$arg" in
    --build)    FORCE_BUILD=1 ;;
    --no-open)  NO_OPEN=1 ;;
    -h|--help)
      echo "Usage: $0 [--build] [--no-open]"
      echo "  --build    Force a docker rebuild even if the image is cached."
      echo "  --no-open  Skip launching the default browser (useful for CI)."
      exit 0
      ;;
    *)          echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# Resolve repo root regardless of caller cwd.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Pre-flight: .env must exist. Friendly error rather than a Docker stack trace.
if [ ! -f .env ]; then
  echo "Error: .env not found at $REPO_ROOT/.env" >&2
  echo "Hint:  cp .env.example .env  (then re-run this script)" >&2
  exit 1
fi

# Build image if missing or forced (D-09).
if [ "$FORCE_BUILD" -eq 1 ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "Building $IMAGE_NAME ..."
  docker build -t "$IMAGE_NAME" .
fi

# Stop+remove any prior container (idempotency).
docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true

# Canonical run (PLAN.md section 11 + D-05 + D-06).
docker run -d \
  --name "$CONTAINER_NAME" \
  -v "${VOLUME_NAME}:/app/db" \
  -p "${PORT}:${PORT}" \
  --env-file .env \
  "$IMAGE_NAME"

echo "FinAlly is starting on http://localhost:${PORT}"
echo "Tail logs: docker logs -f ${CONTAINER_NAME}"
echo "Stop:      bash scripts/stop_mac.sh"

# Open browser only on success and only when not suppressed (D-11).
if [ "$NO_OPEN" -eq 0 ]; then
  case "$(uname)" in
    Darwin) open "http://localhost:${PORT}" >/dev/null 2>&1 || true ;;
    Linux)
      if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:${PORT}" >/dev/null 2>&1 || true
      fi
      ;;
  esac
fi
