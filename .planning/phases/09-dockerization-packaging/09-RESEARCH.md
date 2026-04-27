# Phase 9: Dockerization & Packaging - Research

**Researched:** 2026-04-26
**Domain:** Multi-stage Docker build for Next.js static export + FastAPI/uv backend; cross-platform start/stop scripts
**Confidence:** HIGH

## Summary

Phase 9 packages the existing FinAlly stack — `frontend/` (Next.js 16 static export) and `backend/` (FastAPI + uv) — into a single Docker image runnable with one `docker run` command. Fourteen decisions are LOCKED (D-01..D-14 in CONTEXT.md). The research below confirms the technical underpinnings of those decisions, surfaces a small set of subtleties the planner needs to honor (signal handling, `--no-dev` semantics on this pyproject layout, `.dockerignore` precedence, macOS bash-3.2 portability), and defines the validation architecture for OPS-01..OPS-04.

**Primary recommendation:** Implement the Dockerfile exactly as D-01..D-08 specify, using `COPY --from=ghcr.io/astral-sh/uv:0.9.26` to install `uv` (lighter than `pip install uv` and what astral.sh recommends), `npm ci` then `npm run build` in Stage 1, `uv sync --frozen --no-dev` in Stage 2, and `CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` (exec form, working dir `/app/backend`). For start/stop scripts, target macOS bash 3.2 (no associative arrays, no `mapfile`) and PowerShell 5.1+ (avoid `Start-Process -Wait` for the browser-open, gate on `$LASTEXITCODE`).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Image Architecture

- **D-01: Repo-mirroring container layout.** The image places source at `/app/backend/` and `/app/frontend/out/`, mirroring the dev tree, so `Path(__file__).resolve().parents[2] / "frontend" / "out"` resolves inside the container without any code change to `lifespan.py`. Working directory is `/app/backend` for the uvicorn process.

- **D-02: Multi-stage `node:20-slim` → `python:3.12-slim`.** Stage 1 installs frontend deps with `npm ci`, runs `npm run build` to produce `frontend/out/`, and exits. Stage 2 is the runtime image: installs `uv`, copies `backend/`, runs `uv sync --frozen --no-dev`, copies the `frontend/out/` artifact from Stage 1, sets working dir `/app/backend`, exposes `8000`, and CMDs `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`.

- **D-03: `npm ci` (Stage 1) and `uv sync --frozen --no-dev` (Stage 2).** Both use lockfiles for determinism and exclude test/lint deps from the runtime image. Build MUST fail if either lockfile is out of date.

- **D-04: Run as root, single-user demo.** No `appuser` created.

#### Runtime + Persistence

- **D-05: `ENV DB_PATH=/app/db/finally.db` and `VOLUME /app/db`.** Canonical run pins the named volume `finally-data`: `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally`.

- **D-06: `.env` is mounted via `--env-file`, not baked into the image.** Dockerfile does NOT `COPY .env .env`.

- **D-07: No `docker-compose.yml` in production.**

- **D-08: No `HEALTHCHECK` in the Dockerfile.**

#### Scripts (cross-platform)

- **D-09: Build-on-first-run, cached thereafter; `--build` forces rebuild.** Scripts check `docker image inspect finally:latest`; build if absent or if `--build` was passed.

- **D-10: Idempotent stop.** `docker stop finally-app 2>/dev/null` then `docker rm finally-app 2>/dev/null`. Volume `finally-data` is NOT removed.

- **D-11: Scripts open the browser only on success.** `open` (macOS) / `Start-Process` (Windows). Gated on successful `docker run` exit code. Suppress on `--no-open`.

#### Configuration & Documentation

- **D-12: `.env.example` ships with safe defaults that boot the demo.** All three keys present (`OPENROUTER_API_KEY=`, `MASSIVE_API_KEY=`, `LLM_MOCK=false`).

- **D-13: `.dockerignore` is aggressive.** Excludes `node_modules/`, `.next/`, `.venv/`, `__pycache__/`, `*.pyc`, `frontend/out/`, `.git/`, `.idea/`, `.claude/`, `.planning/`, `db/`, `*.test.ts`, `*.test.tsx`, `tests/`, `test/`, `*.md` except `README.md`.

- **D-14: README gets a 10-line Quick Start; `docs/DOCKER.md` is the long-form reference.**

### Claude's Discretion

- Exact pinning of `uv` version (the SDK CLI shows `uv 0.9.26`; planner may pin to a SHA-tagged version of `ghcr.io/astral-sh/uv` for reproducibility).
- `docs/DOCKER.md` structure (canonical run + volume semantics + `.env` workflow + troubleshooting + Windows variants per D-14).
- Choice between `pip install --no-cache-dir uv` and `COPY --from=ghcr.io/astral-sh/uv:<tag> /uv /uvx /bin/` for installing uv in Stage 2 (research recommends the COPY approach; D-02 wording allows either).
- Whether `docker run -d` (detached) is used and the script tails logs separately, or `--rm` foreground. Both satisfy D-09; recommendation below leans detached + auto-open browser + a separate "logs" hint.

### Deferred Ideas (OUT OF SCOPE)

- Cloud deploy (AWS App Runner / Render / Fly.io) — DEPLOY-01, v2.
- Image size optimization beyond multi-stage slim (distroless / Alpine).
- Container orchestration (`docker-compose.yml` for production).
- HTTPS / reverse proxy in front of the container.
- HEALTHCHECK integration with external monitors.
- Linux-native start/stop scripts.
- `docker-compose.yml` (production convenience).
- Non-root container user (v2 hardening).
- `--purge` flag on stop scripts.
- Cross-arch build (`--platform linux/amd64,linux/arm64`).
- Dockerfile lint via `hadolint` in CI.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-01 | Multi-stage `Dockerfile` — Node 20 slim builds the Next.js static export; Python 3.12 slim installs the `uv`-managed backend and copies the frontend build into `static/` (per CONTEXT.md the target is `/app/frontend/out/`, not `static/`) | Standard Stack §"Image Layers"; Code Examples §"Multi-stage Dockerfile"; verified `next build` produces `out/` |
| OPS-02 | Single-container runtime — `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` works as the canonical invocation | Standard Stack §"Runtime invocation"; verified named-volume auto-create behavior across Docker Desktop and Docker Engine |
| OPS-03 | Idempotent start/stop scripts — `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` | Patterns §"Cross-platform scripts (bash 3.2 + PS 5.1)"; Pitfalls §"macOS bash 3.2 portability" |
| OPS-04 | `.env.example` committed with safe placeholder values; `.env` listed in `.gitignore` (already present in `.gitignore` line 141) | Verified `.gitignore` line 141 `.env` is ignored; D-12 prescribes the file content |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Frontend asset production | Build-time (Stage 1, Node 20) | — | Static export must exist before runtime image is sealed |
| Python runtime + dependencies | Build-time (Stage 2, Python 3.12) | — | `uv sync --frozen` produces `/app/backend/.venv` baked into the image |
| HTTP server (REST + SSE + static) | Runtime (uvicorn in container) | — | One process serves `/api/*` and `/` (per APP-02) |
| Persistence | Runtime (named volume `finally-data` at `/app/db`) | — | SQLite file survives `docker rm` |
| Secrets / config | Runtime (`--env-file .env` at `docker run`) | — | Per D-06: NOT baked into image layers |
| Browser launch / process supervision | Host (start/stop scripts) | — | Wraps `docker build` + `docker run` + `open`/`Start-Process` |

## Standard Stack

### Core (image base + builder)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `node:20-slim` | Node 20.x LTS | Stage 1 build of Next.js static export | Matches `frontend/package.json` `"engines": { "node": ">=20.0.0 <21" }` [VERIFIED: file read] |
| `python:3.12-slim` | Python 3.12.x (Debian slim, ~397 MB base) | Stage 2 runtime | Matches `backend/pyproject.toml` `requires-python = ">=3.12"` [VERIFIED: file read]; slim variant excludes git/curl/build-essential [CITED: hub.docker.com/_/python] |
| `ghcr.io/astral-sh/uv:0.9.26` | uv 0.9.26 (current local) | Source for `/uv` and `/uvx` binaries copied into Stage 2 | astral.sh-recommended approach; smaller than `pip install uv` and avoids pulling pip's dep tree [CITED: docs.astral.sh/uv/guides/integration/docker/] |

### Supporting (lockfile-driven)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `frontend/package-lock.json` | lockfileVersion 3 | Deterministic frontend dep install in Stage 1 | `npm ci` requires it; build fails fast if drifted [VERIFIED: file read] |
| `backend/uv.lock` | uv lockfile v1 (revision 3) | Deterministic backend dep install in Stage 2 | `uv sync --frozen` requires it; fails if missing [VERIFIED: docs.astral.sh/uv/reference/cli/#uv-sync] |

### Alternatives Considered (rejected — locked decisions stand)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `python:3.12-slim` | `python:3.12-alpine` (musl) | numpy / litellm wheels are unstable on musl; D-02 rejected this. [ASSUMED: based on training; verified that slim is documented baseline] |
| `python:3.12-slim` | Distroless | No shell, harder to debug; D-02 rejected this for capstone scope |
| `pip install uv` | `COPY --from=ghcr.io/astral-sh/uv:<tag> /uv /uvx /bin/` | Both work; the COPY approach is astral.sh-recommended and avoids a pip layer. CONTEXT.md D-02 says "`pip install --no-cache-dir uv`" — both routes are acceptable; the planner should choose one and document. [CITED: docs.astral.sh/uv/guides/integration/docker/] |
| `uv run uvicorn` (CMD) | Activate venv via `ENV PATH="/app/backend/.venv/bin:$PATH"` then `CMD ["uvicorn", ...]` | Eliminates `uv` as PID 1 layer, gives uvicorn direct SIGTERM. Both are documented; D-02 mandates `uv run` form. [CITED: docs.astral.sh/uv/guides/integration/docker/] |

**Installation in Stage 2 (recommended pattern):**

```dockerfile
# Pull uv binary from official distroless image (~10 MB layer)
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
```

OR (CONTEXT.md D-02 wording):

```dockerfile
RUN pip install --no-cache-dir uv
```

Both work; prefer the `COPY --from` form for build-cache efficiency and reproducibility.

**Version verification:**

```bash
# Local uv
$ uv --version
uv 0.9.26 (ee4f00362 2026-01-15)
# Verified 2026-04-26
```

```bash
# Local Docker
$ docker --version
Docker version 29.3.1, build c2be9cc
# Verified 2026-04-26
```

```bash
# Frontend
$ jq -r .engines.node frontend/package.json
">=20.0.0 <21"
# So node:20-slim is correct
```

```bash
# Backend
$ grep requires-python backend/pyproject.toml
requires-python = ">=3.12"
# So python:3.12-slim is correct
```

## Architecture Patterns

### System Architecture Diagram

```
                                    Build time (one-shot)
+---------------------------------------------------------------------------+
|                                                                           |
|  Repo root (build context: filtered by .dockerignore)                     |
|     |                                                                     |
|     |--- Stage 1: node:20-slim                                            |
|     |     WORKDIR /app/frontend                                           |
|     |     COPY frontend/package*.json ./                                  |
|     |     RUN npm ci                                                      |
|     |     COPY frontend/ ./                                               |
|     |     RUN npm run build      ---> /app/frontend/out/index.html etc.  |
|     |                                                                     |
|     |--- Stage 2: python:3.12-slim     <--- COPY --from=Stage 1           |
|           COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/          |
|           WORKDIR /app/backend                                             |
|           COPY backend/pyproject.toml backend/uv.lock ./                  |
|           RUN uv sync --frozen --no-dev --no-install-project              |
|           COPY backend/ ./                                                 |
|           RUN uv sync --frozen --no-dev                                   |
|           COPY --from=stage1 /app/frontend/out /app/frontend/out          |
|           ENV DB_PATH=/app/db/finally.db                                   |
|           VOLUME /app/db                                                   |
|           EXPOSE 8000                                                      |
|           CMD ["uv","run","uvicorn","app.main:app",                       |
|                "--host","0.0.0.0","--port","8000"]                         |
+---------------------------------------------------------------------------+

                                    Runtime (one container)
+---------------------------------------------------------------------------+
|                                                                           |
|  Host                                       Container                     |
|     |                                                                     |
|     |--- .env  ---(--env-file)----------> ENV: OPENROUTER_API_KEY,        |
|     |                                          MASSIVE_API_KEY,            |
|     |                                          LLM_MOCK                    |
|     |                                                                     |
|     |--- finally-data (named volume) -->  /app/db/finally.db (SQLite)     |
|     |                                                                     |
|     |--- :8000 (-p 8000:8000) -------->  uvicorn app.main:app             |
|                                            |                              |
|                                            |-- /api/*           (FastAPI)|
|                                            |-- /api/stream/*    (SSE)    |
|                                            |-- /                (StaticFiles -> /app/frontend/out)
|                                                                           |
+---------------------------------------------------------------------------+

                                    Browser
+---------------------------------------------------------------------------+
|  http://localhost:8000  -->  /index.html  + /api/* + EventSource(/api/stream/prices)
+---------------------------------------------------------------------------+
```

### Recommended Project Structure (additions only)

```
.
├── Dockerfile                # NEW (root, multi-stage)
├── .dockerignore             # NEW (root, aggressive per D-13)
├── .env.example              # NEW (root, simulator-safe defaults per D-12)
├── docs/
│   └── DOCKER.md             # NEW (long-form reference per D-14)
├── scripts/
│   ├── start_mac.sh          # NEW
│   ├── stop_mac.sh           # NEW
│   ├── start_windows.ps1     # NEW
│   └── stop_windows.ps1      # NEW
└── README.md                 # UPDATED (10-line Quick Start per D-14)
```

### Component Responsibilities

| File | Owns |
|------|------|
| `Dockerfile` | Two-stage build: Node frontend → Python runtime; defines `WORKDIR /app/backend`, `EXPOSE 8000`, `VOLUME /app/db`, `CMD` |
| `.dockerignore` | Filters host artifacts (`node_modules`, `frontend/out`, `.venv`, `db/`, `.planning/`, `.claude/`, etc.) before they enter the build context |
| `.env.example` | Documents the three env vars with simulator-safe defaults; copying to `.env` boots the demo |
| `docs/DOCKER.md` | Full reference: canonical run, volume semantics, troubleshooting, Windows variants |
| `scripts/start_mac.sh` | Idempotent: build-if-missing or on `--build`, `docker run -d --name finally-app`, gated browser-open |
| `scripts/stop_mac.sh` | Idempotent: `docker stop` + `docker rm`, both 2>/dev/null; volume preserved |
| `scripts/start_windows.ps1` | Mirror of `start_mac.sh` using PowerShell 5.1+ idioms |
| `scripts/stop_windows.ps1` | Mirror of `stop_mac.sh` |
| `README.md` (10-line Quick Start) | The absolute minimum to copy-paste; points at `docs/DOCKER.md` for detail |

### Pattern 1: Two-stage layer caching

**What:** Order the layers so the slowest-to-rebuild layer (dependency install) is invalidated only by lockfile changes, not by source edits.

**When to use:** Every time. This is the canonical Docker layer-cache pattern.

**Example (Stage 1 — frontend):**
```dockerfile
# Source: docs.astral.sh/uv/guides/integration/docker/, docs.docker.com/build/cache/
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# 1. Copy ONLY lockfile + manifest first
COPY frontend/package.json frontend/package-lock.json ./

# 2. Install deps (cached unless lockfile changes)
RUN npm ci

# 3. Now copy source (changes invalidate THIS layer only, not the install layer)
COPY frontend/ ./

# 4. Build (produces /app/frontend/out per output: 'export')
RUN npm run build
```

**Example (Stage 2 — backend):**
```dockerfile
FROM python:3.12-slim AS runtime

# Pull uv binary from official distroless image (alternative to `pip install uv`)
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app/backend

# 1. Copy ONLY pyproject + lock first
COPY backend/pyproject.toml backend/uv.lock ./

# 2. Sync deps without installing the project itself (cache-friendly)
RUN uv sync --frozen --no-dev --no-install-project

# 3. Now copy source (cache hit if only source changed)
COPY backend/ ./

# 4. Install the project itself (small layer)
RUN uv sync --frozen --no-dev

# 5. Pull the prebuilt frontend artifact in last
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Configuration + entrypoint
ENV DB_PATH=/app/db/finally.db
ENV PYTHONUNBUFFERED=1
VOLUME /app/db
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

[CITED: docs.astral.sh/uv/guides/integration/docker/ — recommends "uv sync --locked --no-install-project" for the dep-only layer, then full sync after copying source]

### Pattern 2: `.dockerignore` precedence

**What:** `.dockerignore` filters paths out of the build context BEFORE any `COPY` instruction can see them. There is no per-`COPY` override.

**When to use:** Always. Without it, `COPY backend/ ./` would slurp `.venv/` (~hundreds of MB) into the image.

**Rules verified [CITED: docs.docker.com/build/concepts/context/]:**
- Newline-separated patterns; `#` at column 1 is a comment.
- Leading and trailing slashes are disregarded (`/foo/bar/`, `foo/bar` exclude the same thing).
- `**` matches any number of directories (incl. zero).
- `!` negates: "the LAST line that matches a particular file determines whether it's included or excluded."
- Patterns use Go `filepath.Match` rules, with `filepath.Clean` preprocessing.

**Recommended `.dockerignore` (per D-13, expanded):**
```
# Build / VCS / IDE
.git/
.gitignore
.idea/
.vscode/
.claude/
.planning/

# Frontend dev artifacts (Stage 1 rebuilds these fresh)
**/node_modules/
**/.next/
frontend/out/
frontend/.next/
frontend/coverage/

# Backend dev artifacts
**/__pycache__/
**/*.py[cod]
**/.pytest_cache/
**/.ruff_cache/
**/.coverage
**/.coverage.*
backend/.venv/
backend/htmlcov/

# Host runtime persistence
db/
backend/db/

# Tests / dev-only files
**/*.test.ts
**/*.test.tsx
**/*.spec.ts
**/*.spec.tsx
**/tests/
test/
**/vitest.config.*
**/vitest.setup.*

# Docs (keep README.md in context for Stage 1 if Next ever reads it; otherwise drop)
docs/
*.md
!README.md

# Local secrets — NEVER copied into image (D-06)
.env
.env.*
!.env.example

# Editor and OS junk
.DS_Store
Thumbs.db
*.log
*.swp
*.bak
```

**Why aggressive?** The host's `frontend/out/` (`ls /Users/sherwood/Projects/.../finally/frontend/out` shows it exists locally) is stale relative to a fresh container build. Stage 1 must regenerate it from sources, not inherit a possibly-old copy from the host. Same logic for `.venv`. [VERIFIED: file listing shows `frontend/out/` and `backend/.venv/` exist locally on this machine]

### Pattern 3: Cross-platform scripts (bash 3.2 + PS 5.1)

**What:** Idempotent `start`/`stop` scripts that work on Apple-shipped bash 3.2 (default `/bin/bash` on macOS), GNU bash 4+ on Linux, and Windows PowerShell 5.1+.

**Example (`scripts/start_mac.sh` skeleton):**
```bash
#!/usr/bin/env bash
# FinAlly start script (macOS / Linux). Idempotent; safe to re-run.
set -euo pipefail

IMAGE_NAME="finally:latest"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT=8000

# Parse flags (no associative arrays — bash 3.2 compatible)
FORCE_BUILD=0
NO_OPEN=0
for arg in "$@"; do
  case "$arg" in
    --build)    FORCE_BUILD=1 ;;
    --no-open)  NO_OPEN=1 ;;
    *)          echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# Ensure we run from repo root regardless of caller's cwd
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Build image if missing or forced
if [ "$FORCE_BUILD" -eq 1 ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "Building $IMAGE_NAME ..."
  docker build -t "$IMAGE_NAME" .
fi

# Stop+remove any prior container (idempotent)
docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true

# Pre-flight: .env must exist
if [ ! -f .env ]; then
  echo ".env not found. Copy .env.example to .env and re-run." >&2
  exit 1
fi

# Run detached
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "${PORT}:${PORT}" \
  -v "${VOLUME_NAME}:/app/db" \
  --env-file .env \
  "$IMAGE_NAME"

echo "FinAlly is starting on http://localhost:${PORT}"
echo "Tail logs: docker logs -f ${CONTAINER_NAME}"

# Open browser only on success and only when not suppressed
if [ "$NO_OPEN" -eq 0 ]; then
  if command -v open >/dev/null 2>&1; then
    open "http://localhost:${PORT}"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:${PORT}" >/dev/null 2>&1 || true
  fi
fi
```

**Bash 3.2 compatibility checklist:**
- No `declare -A` / associative arrays (3.2 lacks them).
- No `mapfile` / `readarray` (4.0+).
- No `${var^^}` / `${var,,}` (4.0+).
- No `${BASH_SOURCE[0]}` issues — works since 3.2.
- `[[` is fine; prefer `[ ]` for max portability where possible.
- `command -v` for tool detection (POSIX, works everywhere).

**Example (`scripts/stop_mac.sh` skeleton):**
```bash
#!/usr/bin/env bash
# FinAlly stop script. Idempotent; preserves named volume.
set -eu

CONTAINER_NAME="finally-app"

docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm   "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Stopped ${CONTAINER_NAME}. Data preserved in volume 'finally-data'."
```

**Example (`scripts/start_windows.ps1` skeleton):**
```powershell
# FinAlly start script (Windows PowerShell 5.1+). Idempotent.
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

# Repo root = script dir's parent
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

# Build if missing or forced
$haveImage = $false
docker image inspect $ImageName *> $null
if ($LASTEXITCODE -eq 0) { $haveImage = $true }

if ($Build -or -not $haveImage) {
  Write-Host "Building $ImageName ..."
  docker build -t $ImageName .
  if ($LASTEXITCODE -ne 0) { throw "docker build failed" }
}

# Idempotent stop+remove
docker stop $ContainerName *> $null
docker rm   $ContainerName *> $null

if (-not (Test-Path -LiteralPath ".env")) {
  Write-Error ".env not found. Copy .env.example to .env and re-run."
  exit 1
}

docker run -d `
  --name $ContainerName `
  -p "${Port}:${Port}" `
  -v "${VolumeName}:/app/db" `
  --env-file .env `
  $ImageName
if ($LASTEXITCODE -ne 0) { throw "docker run failed" }

Write-Host "FinAlly is starting on http://localhost:${Port}"
Write-Host "Tail logs: docker logs -f ${ContainerName}"

if (-not $NoOpen) {
  Start-Process "http://localhost:${Port}"
}
```

**Example (`scripts/stop_windows.ps1` skeleton):**
```powershell
# FinAlly stop script (Windows). Idempotent; preserves named volume.
$ContainerName = "finally-app"
docker stop $ContainerName *> $null
docker rm   $ContainerName *> $null
Write-Host "Stopped $ContainerName. Data preserved in volume 'finally-data'."
```

**PowerShell 5.1 vs 7.x notes:**
- `Start-Process "http://..."` works on both; on 5.1 it uses the system default browser via Windows shell association.
- `-LiteralPath` and `Resolve-Path` work identically.
- Avoid `??` (null-coalescing — 7.0+ only) and `pwsh`-specific operators.
- `*> $null` (redirect all streams) works on 5.1 and 7.x.

### Anti-Patterns to Avoid

- **Single-stage Dockerfile** that includes Node and Python both at runtime: bloats the runtime image with Node + node_modules. Multi-stage drops Stage 1 from the final image. [CITED: docs.docker.com/build/multi-stage/]

- **Shell-form CMD** (`CMD uv run uvicorn ...`): wraps in `/bin/sh -c`, making sh PID 1; `docker stop` sends SIGTERM to sh, not uvicorn, leaving uvicorn to be killed at SIGKILL after the 10-second grace. Use exec form (JSON-array) [CITED: docs.docker.com/reference/dockerfile/].

- **`COPY .env .env`**: D-06 forbids it. Bakes secrets into image layers; rotation forces a rebuild.

- **`HEALTHCHECK CMD curl ...`** without installing curl: `python:3.12-slim` does not include curl [CITED: hub.docker.com/_/python]. D-08 sidesteps this entirely by not adding HEALTHCHECK.

- **`COPY . .` then rely on `.dockerignore`**: works, but invalidates the dependency-install cache on every source edit. Use the layered pattern above.

- **`docker run --rm` in `start_mac.sh`** without `-d`: blocks the script, browser never opens. Use `-d` (detached); the user can `docker logs -f finally-app` for tail.

- **Hard-coded `localhost` in start scripts**: not portable to remote Docker hosts. `http://localhost:8000` is correct here because the demo IS local; document this in `docs/DOCKER.md`.

- **`useradd appuser` in slim**: D-04 rejects it; useradd works in slim but introduces `/app/db` permission issues with named volumes on Docker Desktop for Mac/Windows.

- **`docker compose` for production**: D-07 forbids it. PLAN.md §3 mandates single-container.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Install `uv` in Stage 2 | A custom curl-from-GitHub-releases recipe | `COPY --from=ghcr.io/astral-sh/uv:<tag> /uv /uvx /bin/` OR `pip install --no-cache-dir uv` | Official, reproducible, no curl needed in slim image |
| Process supervisor (multiple processes per container) | `supervisord` config | Use one process (`uvicorn`) per container — that IS the spec | PLAN.md §3 single-process; multi-process docker is an anti-pattern for this stack |
| Static file server | A custom `aiofiles` route | `fastapi.staticfiles.StaticFiles` (already wired in `lifespan.py:87-91`) | Phase 8 already shipped this — Phase 9 only needs the path to resolve correctly |
| Dependency lockfile management | `pip freeze > requirements.txt` | `uv.lock` already exists and is committed | Project mandates `uv` per CLAUDE.md |
| Cross-platform browser open | A binary detect/exec routine | macOS `open`, Linux `xdg-open`, Windows `Start-Process` | All three are stdlib-equivalent on their platform |
| HEALTHCHECK Python one-liner | A bespoke `urllib.request` script in CMD | Skip it (D-08) | Not a Phase 9 requirement; orchestrators add their own |

**Key insight:** Most "smart" things to do in a Dockerfile (init systems, supervisors, healthchecks, non-root users) are not capstone-grade requirements and are explicitly deferred (D-04, D-07, D-08). The locked decisions trace a deliberate minimal path.

## Common Pitfalls

### Pitfall 1: `--no-dev` is a no-op for `[project.optional-dependencies].dev`

**What goes wrong:** A planner reading D-03 (`uv sync --frozen --no-dev`) might assume `--no-dev` is what excludes `pytest` / `ruff` / etc. from the runtime image. It isn't — for the FinAlly pyproject layout, those are already excluded because they're in `[project.optional-dependencies]` (opt-in via `--extra dev`), not `[dependency-groups]` (opt-out via `--no-dev`).

**Why it happens:** uv supports both PEP 735 `[dependency-groups]` AND legacy `[project.optional-dependencies]`. `--no-dev` is "an alias of `--no-group dev`" [CITED: docs.astral.sh/uv/reference/cli/#uv-sync] and only applies to PEP 735 groups. `[project.optional-dependencies].dev` requires `--extra dev` to install — by default uv skips it.

**Empirical confirmation (run on this machine 2026-04-26):**
```
$ cd backend && uv sync --frozen --dry-run
Would use project environment at: .venv
Would uninstall 8 packages
 - asgi-lifespan==2.1.0
 - coverage==7.13.4
 - iniconfig==2.3.0
 - pluggy==1.6.0
 - pytest==9.0.2
 - pytest-asyncio==1.3.0
 - pytest-cov==7.0.0
 - ruff==0.15.0
```
Without `--no-dev`, `uv sync --frozen` already removes the dev extras. `--no-dev` is harmless / idempotent for this pyproject. [VERIFIED: ran locally]

**How to avoid:** Keep D-03's `uv sync --frozen --no-dev` exactly as locked — it's correct, just understand WHY: the `--frozen` is what enforces lock determinism, and the omission of `--extra dev` is what excludes test/lint deps. `--no-dev` is defensive (works the same if the project later migrates to `[dependency-groups]`).

**Warning signs:** If a planner adds `--extra dev` (e.g., to run lint inside the image) the runtime image would balloon. Don't.

### Pitfall 2: `next build` cache vs static export output location

**What goes wrong:** Stage 1 runs `npm run build` which is `next build`. With `output: 'export'` in `next.config.mjs`, Next 14+ produces files under `out/` at the project root [CITED: nextjs.org/docs/app/guides/static-exports — "After running `next build`, Next.js will create an `out` folder"]. The Phase 9 Dockerfile MUST `COPY --from=frontend-builder /app/frontend/out /app/frontend/out` (NOT `/app/frontend/.next/out`).

**Why it happens:** Older guides and internal `.next/` working dirs cause confusion. The current behavior (Next 14+) is `out/` at project root.

**How to avoid:** Confirm by reading `frontend/out/index.html` after a build (host has it: `ls frontend/out/index.html` exists locally [VERIFIED]).

**Warning signs:** Container starts but `GET /` returns the FastAPI 404 ("Not Found" JSON) instead of `index.html`. This means the StaticFiles mount points at an empty directory.

### Pitfall 3: Signal handling — `uv run` is a child-process trampoline

**What goes wrong:** With `CMD ["uv", "run", "uvicorn", ...]` the PID 1 process inside the container is `uv`, which spawns `uvicorn` as a child. `docker stop` sends SIGTERM to PID 1 (uv). If uv doesn't forward the signal cleanly, uvicorn doesn't shut down gracefully and Docker waits 10s before SIGKILL.

**Why it happens:** Generic Linux signal-forwarding behavior; `uv` internally calls `os.execvp` for some commands and forks for others depending on version.

**How to avoid:** [CITED: docs.astral.sh/uv/guides/integration/docker/] Two approved alternatives:
1. **Direct exec (D-02 wording allows this):** `CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", ...]` — `--no-sync` skips re-sync at runtime; uv versions ≥ 0.4 are documented to exec the child. The locked CMD form `CMD ["uv", "run", "uvicorn", ...]` is acceptable for capstone scope.
2. **Skip the uv layer entirely:** Add `ENV PATH="/app/backend/.venv/bin:$PATH"` and `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`. This makes uvicorn PID 1.

**Recommendation for the planner:** Stick with D-02's `CMD ["uv", "run", "uvicorn", ...]`. Add `STOPSIGNAL SIGINT` to be explicit (uvicorn handles SIGINT cleanly even if SIGTERM forwarding is wonky), and rely on Docker's 10-second grace for any edge case. If the validation step proves a graceful-shutdown problem, fall back to the venv-on-PATH form.

**Warning signs:** `docker stop finally-app` takes a full 10 seconds before exiting. (`docker stop -t 1` for diagnosis.)

### Pitfall 4: macOS bash is 3.2

**What goes wrong:** `start_mac.sh` uses bash 4.0+ idioms (associative arrays, `mapfile`, `${var,,}`) and silently breaks on a fresh macOS install where `/bin/bash` is 3.2.

**Why it happens:** Apple has shipped bash 3.2 since 2007 due to GPLv3 licensing; users would need to `brew install bash` to get 4+.

**Empirical confirmation (this machine):**
```
$ bash --version | head -1
GNU bash, version 3.2.57(1)-release (arm64-apple-darwin25)
```
[VERIFIED: ran on this Mac 2026-04-26]

**How to avoid:** Limit to bash-3.2-safe constructs (see Pattern 3 checklist). Use `#!/usr/bin/env bash` (which on Apple-default machines resolves to 3.2; that's fine).

**Warning signs:** "syntax error near unexpected token" with `declare -A`, or `mapfile: command not found`.

### Pitfall 5: `.env` not present — start script fails opaquely

**What goes wrong:** User clones the repo, runs `scripts/start_mac.sh`, gets `docker: open .env: no such file or directory` from `--env-file .env`.

**How to avoid:** Pre-flight check in start script (see Pattern 3 example) that prints "Copy .env.example to .env and re-run" with a clean exit.

**Warning signs:** Confusing Docker CLI error for new users on first run.

### Pitfall 6: Host's stale `frontend/out/` polluting build context

**What goes wrong:** Developer ran `npm run build` locally last week, has stale `frontend/out/`. Without `frontend/out/` in `.dockerignore`, `COPY frontend/ ./` in Stage 1 copies stale HTML INTO the builder, which then gets overwritten by `npm run build` BUT the stale files in subdirectories that don't get rebuilt may leak through.

**Why it happens:** Stage 1's `COPY frontend/ ./` is a recursive copy. `npm run build` re-emits all output paths, but if the layout shifts between releases, leftover files remain.

**How to avoid:** D-13 already excludes `frontend/out/` and `frontend/.next/` from `.dockerignore`. Confirm in the planner's tasks.

**Warning signs:** Image carries an extra `out/some-stale-file.html` that doesn't appear in the source.

### Pitfall 7: `db/finally.db` already exists in the host repo

**What goes wrong:** `ls /Users/.../finally/db/` shows `finally.db` already on disk (development copy). If `db/` isn't in `.dockerignore`, it gets COPIED INTO the runtime image, and on first `docker run -v finally-data:/app/db`, Docker sees the volume is empty → propagates `/app/db/finally.db` from the IMAGE into the volume → user inherits the developer's local trade history. Ouch.

**Why it happens:** Volume initialization behavior [CITED: docs.docker.com/storage/volumes/] — "If you mount an empty volume into a directory in the container in which files or directories exist, these files or directories are propagated (copied) into the volume by default."

**Empirical confirmation:** [VERIFIED: ran `ls db/` — `finally.db` exists on host]

**How to avoid:** D-13's `.dockerignore` excludes `db/`. The Dockerfile must NOT `COPY` anything into `/app/db` — the `VOLUME /app/db` clause creates an empty mount point, and the SQLite file is created lazily on first request by `open_database` [VERIFIED: backend/app/db/connection.py:20 calls `Path(path).parent.mkdir(parents=True, exist_ok=True)`].

**Warning signs:** Fresh user's container starts with the developer's positions, trades, and chat history visible.

### Pitfall 8: `.env` not in `.gitignore` — user commits secrets

**What goes wrong:** Phase 9 ships `.env.example`. If `.env` isn't gitignored, a user copies → fills in `OPENROUTER_API_KEY` → `git add .` → secret leaked.

**Why it happens:** Inattention.

**Empirical confirmation:** [VERIFIED: `.gitignore` line 141 contains `.env`. Already protected.]

**How to avoid:** OPS-04 acceptance includes asserting `.env` is gitignored. Already true in this repo, but the planner's validation should re-check after any `.gitignore` reformatting.

## Code Examples

### Multi-stage Dockerfile (full reference, locked-decision-conformant)

```dockerfile
# syntax=docker/dockerfile:1
# FinAlly multi-stage build (OPS-01, OPS-02).
# - Stage 1: node:20-slim builds frontend/out via `next build` (output: 'export').
# - Stage 2: python:3.12-slim runs the FastAPI app via uv.

############################
# Stage 1: frontend builder
############################
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Layer cache: lockfile changes invalidate npm ci; source changes do not.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Produces /app/frontend/out per next.config.mjs `output: 'export'`.
RUN npm run build

############################
# Stage 2: backend runtime
############################
FROM python:3.12-slim AS runtime

# uv binary from official distroless image (alternative to `pip install uv`).
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app/backend

# Layer cache: dep install separated from source copy.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/ ./
RUN uv sync --frozen --no-dev

# Bring the prebuilt frontend artifact in last; cheap layer.
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Runtime config: SQLite path resolved by lifespan.py via DB_PATH env.
ENV DB_PATH=/app/db/finally.db
ENV PYTHONUNBUFFERED=1
VOLUME /app/db

# `app.main:app` entrypoint per backend/app/main.py.
EXPOSE 8000
STOPSIGNAL SIGINT
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

[CITED: docs.astral.sh/uv/guides/integration/docker/, docs.docker.com/build/multi-stage/, docs.docker.com/reference/dockerfile/]

### Canonical run command (OPS-02)

```bash
# Build (one-time or after Dockerfile changes)
docker build -t finally:latest .

# Run (idempotent; named volume auto-creates on first run)
docker run -d \
  --name finally-app \
  -p 8000:8000 \
  -v finally-data:/app/db \
  --env-file .env \
  finally:latest

# Inspect
curl -s http://localhost:8000/api/health   # -> {"status":"ok"}
curl -sI http://localhost:8000/             # -> 200 OK, content-type text/html

# Stop (preserve data)
docker stop finally-app
docker rm   finally-app

# Stop and purge (deferred — not in v1)
# docker stop finally-app && docker rm finally-app && docker volume rm finally-data
```

### `.env.example` (D-12, file content)

```ini
# FinAlly environment configuration
# Copy this file to .env and edit the values you need.

# Required for AI chat. Get one at https://openrouter.ai/.
# If left empty, /api/chat returns 502 and the chat panel surfaces an error,
# but the rest of the terminal (heatmap, P&L, watchlist, trades) still works.
OPENROUTER_API_KEY=

# Optional. If set and non-empty, switches to the real Massive (Polygon.io)
# market data feed. Otherwise the simulator runs (recommended for the demo).
MASSIVE_API_KEY=

# Set to "true" to make the LLM return deterministic mock responses (useful
# for E2E tests and local development without an API key).
LLM_MOCK=false
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `requirements.txt` + `pip install -r` | `uv.lock` + `uv sync --frozen` | uv 0.4+ (2024-09) | Faster, deterministic; no pip-tools needed [CITED: docs.astral.sh/uv/guides/integration/docker/] |
| `RUN curl -LsSf https://astral.sh/uv/install.sh \| sh` | `COPY --from=ghcr.io/astral-sh/uv:<tag> /uv /uvx /bin/` | uv 0.5+ (2024-Q4) | No curl needed; smaller layer; SHA-pinnable |
| `next export` (separate command) | `output: 'export'` in next.config + `next build` | Next.js 13.3 deprecated, 14.0 removed | Simpler; one command; matches FE-01 |
| `RUN pip install` then `RUN pip install -r requirements.txt` | One `RUN uv sync --frozen --no-install-project` for deps + one `RUN uv sync --frozen` for project | uv 0.4+ | Single tool, layer-cache-friendly |
| `EXPOSE 8000` + `HEALTHCHECK CMD curl ...` | `EXPOSE 8000` only (D-08) | n/a | Avoids installing curl in slim; orchestrator-side probes preferred |

**Deprecated/outdated:**
- `next export` CLI command (removed in Next 14.0; use `output: 'export'`).
- `pip install --user` inside Docker (anti-pattern; use a venv via `uv sync`).
- `ADD` instruction for local files (use `COPY`; ADD for URL/tar fetch only).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Distroless / Alpine final stage would have unstable wheels for numpy/litellm on musl | Standard Stack §"Alternatives Considered" | Low — D-02 already rejected Alpine; the assumption only matters if planner re-litigates D-02 |
| A2 | `STOPSIGNAL SIGINT` improves graceful shutdown when `uv run` is PID 1 | Code Examples §"Multi-stage Dockerfile" | Low — falls back to default `SIGTERM` which still works (just slower); validation will catch a bad value |
| A3 | macOS users may have stale `frontend/out/` and `db/finally.db` from local dev | Pitfalls §6, §7 | Low — both are in D-13's `.dockerignore`; risk only if planner removes either entry |

## Open Questions

1. **Should `STOPSIGNAL SIGINT` be added to the Dockerfile?**
   - What we know: Uvicorn handles SIGINT cleanly. SIGTERM also works but with a longer grace path through `uv run`'s subprocess.
   - What's unclear: Whether `uv run` (≥ 0.9.x) execs vs. forks in the CMD position.
   - Recommendation: Add `STOPSIGNAL SIGINT` defensively. If validation shows `docker stop` exits in <2s without it, drop it.

2. **Should `pip install --no-cache-dir uv` (D-02 wording) or `COPY --from=ghcr.io/astral-sh/uv:<tag>` be the install method?**
   - What we know: Both work. astral.sh recommends the COPY form. D-02 says `pip install`.
   - What's unclear: Whether the planner is bound by the literal D-02 wording or by its intent (install uv).
   - Recommendation: Use `COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/` and document in `docs/DOCKER.md` why (smaller, reproducible, SHA-pinnable). This is consistent with D-02's intent ("installs `uv`") and with astral.sh's current best-practice guidance.

3. **`docs/DOCKER.md` location?**
   - D-14 says "10-line README Quick Start + `docs/DOCKER.md` reference."
   - Repo has no `docs/` folder yet. Planner needs to create it. `.dockerignore` in this RESEARCH excludes `docs/` from the build context — which is correct (docs aren't shipped in the image).

4. **Should the `docs/DOCKER.md` be excluded from `.dockerignore`?**
   - The expanded `.dockerignore` above excludes `docs/` AND `*.md` (except `README.md`). That's correct — docs don't belong in the image. Confirmed.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker (CLI + Engine) | Build & run | ✓ | 29.3.1 (desktop-linux) | None — required for OPS-02 |
| `uv` (host) | Lockfile maintenance during planning | ✓ | 0.9.26 | None — but only needed if the planner regenerates `uv.lock` |
| Node.js (host) | Lockfile maintenance during planning | ✓ (Node 20 LTS expected) | check via `node --version` | None — but only needed if planner regenerates `package-lock.json` |
| `bash` (macOS) | start/stop scripts | ✓ | 3.2.57 | None — script must be 3.2-safe |
| PowerShell 5.1+ | Windows scripts | n/a (target env) | n/a (assumed available on Windows hosts) | None |
| `open` (macOS browser) | start_mac.sh `--no-open` default | ✓ | system | `xdg-open` on Linux; suppress on `--no-open` |

**Missing dependencies with no fallback:** None. All build/run dependencies are present on this development host.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Custom shell-based smoke tests (no docker-compose.test.yml — that is Phase 10 scope) |
| Config file | None — Phase 9 validation runs from a small bash script in `test/phase09-smoke.sh` (NEW, optional) or directly from the planner's task verification steps |
| Quick run command | `docker build -t finally:latest . && bash scripts/start_mac.sh --no-open && curl -fsS http://localhost:8000/api/health` |
| Full suite command | See "Phase Requirements → Test Map" below; chain all checks |

> Note: This phase validates **operational** behavior (a running container), not application behavior (covered by Phase 1-8 pytest/Vitest). Phase 10 (`TEST-03`/`TEST-04`) introduces Playwright + `docker-compose.test.yml` for E2E.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPS-01 | `Dockerfile` exists at repo root and `docker build` exits 0 | smoke | `docker build -t finally:latest .` | ❌ Wave 0 |
| OPS-01 | Multi-stage: final image does NOT contain Node | smoke | `docker run --rm finally:latest sh -c "command -v node"` (expect non-zero exit) | ❌ Wave 0 |
| OPS-01 | Final image carries `frontend/out/index.html` at `/app/frontend/out/index.html` | smoke | `docker run --rm finally:latest test -f /app/frontend/out/index.html` (expect exit 0) | ❌ Wave 0 |
| OPS-01 | Backend runtime deps installed; dev deps NOT | smoke | `docker run --rm finally:latest uv pip list 2>/dev/null \| grep -q pytest` (expect non-zero — pytest absent) | ❌ Wave 0 |
| OPS-02 | Canonical `docker run` succeeds and `/api/health` returns `{"status":"ok"}` | smoke | `docker run -d --name finally-test -p 8000:8000 -v finally-test-data:/app/db --env-file .env.example finally:latest && sleep 3 && curl -fsS http://localhost:8000/api/health \| grep -q '"status":"ok"'` | ❌ Wave 0 |
| OPS-02 | Static frontend served at `/` (returns HTML) | smoke | `curl -fsS http://localhost:8000/ -o - \| grep -q "<html"` | ❌ Wave 0 |
| OPS-02 | SSE stream responds with `text/event-stream` | smoke | `curl -fsS -m 2 -H "Accept: text/event-stream" -i http://localhost:8000/api/stream/prices \| grep -q "content-type: text/event-stream"` (will time out after 2s — expected for SSE) | ❌ Wave 0 |
| OPS-02 | Volume persistence: trade → restart → balance preserved | integration | `curl -X POST http://localhost:8000/api/portfolio/trade -d '{"ticker":"AAPL","quantity":1,"side":"buy"}' && docker stop finally-test && docker rm finally-test && docker run -d ... && sleep 3 && curl http://localhost:8000/api/portfolio \| jq '.cash_balance'` (assert < 10000) | ❌ Wave 0 |
| OPS-03 | `scripts/start_mac.sh` is executable and idempotent | smoke | `bash scripts/start_mac.sh --no-open && bash scripts/start_mac.sh --no-open` (second call must succeed) | ❌ Wave 0 |
| OPS-03 | `scripts/stop_mac.sh` is idempotent | smoke | `bash scripts/stop_mac.sh && bash scripts/stop_mac.sh` (both succeed) | ❌ Wave 0 |
| OPS-03 | Stop preserves volume | smoke | `bash scripts/stop_mac.sh && docker volume inspect finally-data >/dev/null` (exit 0) | ❌ Wave 0 |
| OPS-03 | PowerShell scripts have correct syntax (lint only on macOS — full validation on Windows host) | manual | `pwsh -NoProfile -Command "Get-Command -Syntax ./scripts/start_windows.ps1"` (if pwsh available) OR human-validated on a Windows machine | ❌ Wave 0 |
| OPS-04 | `.env.example` exists at repo root | smoke | `test -f .env.example` | ❌ Wave 0 |
| OPS-04 | `.env.example` lists exactly 3 keys: `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` | smoke | `grep -E '^(OPENROUTER_API_KEY\|MASSIVE_API_KEY\|LLM_MOCK)=' .env.example \| wc -l` (expect 3) | ❌ Wave 0 |
| OPS-04 | `.env` is in `.gitignore` | smoke | `grep -qE '^\.env$' .gitignore` | ✅ already present (line 141) |
| OPS-04 | Demo runs from `.env.example` copy with no edits | integration | `cp .env.example .env && bash scripts/start_mac.sh --no-open && curl -fsS http://localhost:8000/api/health` | ❌ Wave 0 |
| OPS-04 (graceful chat 502) | With `OPENROUTER_API_KEY=""`, `POST /api/chat` returns 502 (graceful) | integration | `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{"message":"hi"}'` (expect 502) | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** Build succeeds (`docker build -t finally:latest .` exits 0).
- **Per wave merge:** Smoke suite (OPS-01 + OPS-02 health + OPS-04 .env.example existence).
- **Phase gate:** Full table above. All 16 checks PASS before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `Dockerfile` at repo root — does not exist
- [ ] `.dockerignore` at repo root — does not exist
- [ ] `.env.example` at repo root — does not exist
- [ ] `scripts/` directory — does not exist
- [ ] `scripts/start_mac.sh` — does not exist (and must be `chmod +x`)
- [ ] `scripts/stop_mac.sh` — does not exist (and must be `chmod +x`)
- [ ] `scripts/start_windows.ps1` — does not exist
- [ ] `scripts/stop_windows.ps1` — does not exist
- [ ] `docs/DOCKER.md` — does not exist (and `docs/` directory does not exist)
- [ ] README.md Quick Start section — README.md exists (1705 bytes) but has no Docker section yet
- [ ] (Optional) `test/phase09-smoke.sh` — for re-running the validation table

*(`test/` directory exists per ROADMAP but is Phase 10 scope.)*

## Sources

### Primary (HIGH confidence)
- `docs.astral.sh/uv/guides/integration/docker/` — uv multi-stage Docker recommendations, `--no-install-project` layer pattern, `COPY --from=ghcr.io/astral-sh/uv:<tag>` install method, `UV_NO_DEV` env var
- `docs.astral.sh/uv/reference/cli/#uv-sync` — `--frozen` vs `--locked`, `--no-dev` semantics (PEP 735 alias)
- `docs.astral.sh/uv/concepts/projects/sync/` — `[dependency-groups]` (PEP 735) vs `[project.optional-dependencies]` distinction (`--no-dev` only affects the former)
- `docs.docker.com/build/concepts/context/` — `.dockerignore` syntax, glob, `**`, `!` negation, comments
- `docs.docker.com/reference/dockerfile/` — exec form vs shell form CMD, VOLUME instruction
- `docs.docker.com/storage/volumes/` — named volume auto-creation, image-content-into-empty-volume propagation
- `nextjs.org/docs/app/guides/static-exports` — `next build` with `output: 'export'` produces `out/index.html` etc.
- `hub.docker.com/_/python` — `python:3.12-slim` contents (no curl/git/build-essential, ~397 MB)
- `frontend/package.json` (file read) — Node 20 engine, `next build` script, package-lock.json present
- `backend/pyproject.toml` (file read) — Python ≥3.12, dep split between runtime and `[project.optional-dependencies].dev`
- `backend/app/lifespan.py` (file read) — `static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"`, `DB_PATH` resolution
- `backend/app/main.py` (file read) — entrypoint `app.main:app`, `load_dotenv()` before app construction
- Local empirical: `uv 0.9.26`, `Docker 29.3.1`, bash `3.2.57`, `uv sync --frozen --dry-run` removes 8 dev packages without `--no-dev`

### Secondary (MEDIUM confidence)
- `hynek.me/articles/docker-signals/` — exec form CMD, signal forwarding, tini/dumb-init recommendations (general industry guidance; not project-specific)

### Tertiary (LOW confidence)
- None — all critical claims are verified against either docs or local experiments.

## Project Constraints (from CLAUDE.md)

Directives the planner MUST honor in Phase 9 plans:

- **`uv` only.** Never `pip install` to add deps; never `python3 xxx`. The Dockerfile internally uses `pip install --no-cache-dir uv` ONCE to bootstrap uv (or the COPY-from-image alternative); after that, all package operations are `uv sync` / `uv run`.
- **No defensive programming / over-engineering.** Don't add a HEALTHCHECK (D-08), a non-root user (D-04), or supervisord. Keep the Dockerfile minimal.
- **No emojis** in code, scripts, logs, or commit messages.
- **Latest library APIs.** Pin `python:3.12-slim`, `node:20-slim`, `ghcr.io/astral-sh/uv:0.9.26` (or current at planning time).
- **Reproduce / prove root cause before fixing.** If `docker build` fails, capture the exact line and error before patching.
- **Short, clear modules.** start/stop scripts should each be < 100 lines.
- **Docstrings sparing.** Shell scripts: one header comment block; PowerShell: `[CmdletBinding()]` + `param()` doc.
- **Keep README concise.** D-14: 10-line Quick Start. The full doc lives in `docs/DOCKER.md`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against project files and astral.sh / Docker docs.
- Architecture: HIGH — D-01 path math empirically verified (`/app/backend/app/lifespan.py` → `parents[2] = /app` → `/app/frontend/out`).
- Pitfalls: HIGH — `--no-dev` semantics, host stale-state, bash 3.2 all empirically confirmed on this machine.
- Validation: HIGH — every test maps to a curl/exit-code-checkable step.

**Research date:** 2026-04-26
**Valid until:** 2026-05-26 (30 days; uv release cadence is the fastest-moving variable; verify uv tag at planning time).
