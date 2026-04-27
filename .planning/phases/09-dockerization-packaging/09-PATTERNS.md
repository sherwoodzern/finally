# Phase 9: Dockerization & Packaging - Pattern Map

**Mapped:** 2026-04-26
**Files analyzed:** 7 new artifacts (Dockerfile, .dockerignore, .env.example, 4 scripts, docs/DOCKER.md, README.md update)
**Analogs found:** 0 / 7 (greenfield phase — see Constraint Inventory)

## Greenfield Notice

Phase 9 has **no in-repo file analogs**. There is no existing Dockerfile, no `.dockerignore`, no `scripts/` directory, no `.env.example`, no `docs/` directory. Every artifact is created from scratch.

**This PATTERNS.md therefore inverts the usual format:** instead of "copy from analog X," it provides a **constraint inventory** — for each new file, the in-repo "source of truth" files that constrain it (paths, env var names, container layout, lockfile usage), with verbatim excerpts the planner MUST preserve in plan `<read_first>` blocks.

The "patterns" here are **invariants the new artifacts must respect**, not code excerpts to copy.

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `Dockerfile` | config (build) | batch | none — greenfield | constraint-only |
| `.dockerignore` | config (build) | batch | `.gitignore` (complement) | partial — see below |
| `.env.example` | config (runtime) | request-response (env load) | `.env` (mirror keys) | shape-only |
| `scripts/start_mac.sh` | utility (ops) | batch | none — greenfield | constraint-only |
| `scripts/stop_mac.sh` | utility (ops) | batch | none — greenfield | constraint-only |
| `scripts/start_windows.ps1` | utility (ops) | batch | none — greenfield | constraint-only |
| `scripts/stop_windows.ps1` | utility (ops) | batch | none — greenfield | constraint-only |
| `docs/DOCKER.md` | documentation | static | `README.md` (project doc voice) | tone-only |
| `README.md` (update) | documentation | static | `README.md` (existing) | edit-in-place |

## Constraint Inventory

### `Dockerfile` (NEW)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `backend/pyproject.toml` — picks Python version, runtime vs dev extras
- `backend/app/lifespan.py` lines 86-91 — static_dir resolution (constrains container layout)
- `backend/app/main.py` lines 1-20 — uvicorn entrypoint (constrains CMD)
- `frontend/package.json` lines 5-8 — Node engine constraint, build script
- `frontend/next.config.mjs` lines 1-4 — `output: 'export'` produces `frontend/out/`
- `backend/uv.lock` (~451 KB present) — required by `uv sync --frozen`
- `frontend/package-lock.json` — required by `npm ci`
- `planning/PLAN.md` §11 (lines 540-580 of PLAN; multi-stage Dockerfile spec)

**Container layout constraint (D-01 from CONTEXT.md):**

`backend/app/lifespan.py:86`:
```python
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"
```

This means: from `/app/backend/app/lifespan.py`, `parents[2]` is `/app`. Therefore the container MUST place:
- backend at `/app/backend/` (so `app/lifespan.py` lives at `/app/backend/app/lifespan.py`)
- frontend export at `/app/frontend/out/` (so `parents[2] / "frontend" / "out"` resolves)
- working directory `/app/backend` for the uvicorn process (so `app.main:app` import resolves)

**Python version pin (from `backend/pyproject.toml:6`):**
```toml
requires-python = ">=3.12"
```
→ Stage 2 base image: `python:3.12-slim` (D-02).

**Node engine pin (from `frontend/package.json:5-7`):**
```json
"engines": {
  "node": ">=20.0.0 <21"
}
```
→ Stage 1 base image: `node:20-slim` (D-02). Do NOT use `node:22` or `node:lts` — the engine field locks the major.

**Lockfile-driven installs (D-03):**
- Stage 1: `npm ci` (requires `frontend/package-lock.json` to be present and up to date)
- Stage 2: `uv sync --frozen --no-dev` (requires `backend/uv.lock`; `--no-dev` excludes pytest/ruff/httpx/asgi-lifespan)

**Frontend build artifact (from `frontend/next.config.mjs:3` + Plan 08-08):**
```javascript
output: 'export'
```
+ `npm run build` produces `frontend/out/index.html` (verified present at `frontend/out/index.html`).

**Stage 2 entrypoint (from `backend/app/main.py:20`):**
```python
app = FastAPI(lifespan=lifespan)
```
→ Canonical CMD (per D-02 + ROADMAP SC#1):
```dockerfile
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Volume + DB path (D-05, mirrors `backend/app/lifespan.py:59`):**

`backend/app/lifespan.py:59`:
```python
db_path = os.environ.get("DB_PATH", "db/finally.db")
```

Dockerfile must set:
```dockerfile
ENV DB_PATH=/app/db/finally.db
VOLUME ["/app/db"]
```

(The default is a *relative* path `db/finally.db`, so without `ENV DB_PATH=/app/db/finally.db` and WORKDIR `/app/backend`, SQLite would write to `/app/backend/db/finally.db` and miss the volume.)

**Port (D-02):**
```dockerfile
EXPOSE 8000
```

**No `.env` baked in (D-06):**
The Dockerfile does NOT `COPY .env`. Env is mounted via `--env-file .env` at run time. `backend/app/main.py:16` calls `load_dotenv()` which reads `.env` from CWD upward — but inside the container, `--env-file` populates `os.environ` directly, so the dotenv call becomes a silent no-op (it does not crash if `.env` is absent — APP-03 contract).

**No HEALTHCHECK (D-08):** Do not add `HEALTHCHECK` — adds noise without demo value.

**No USER directive (D-04):** Run as root. Single-user localhost demo.

---

### `.dockerignore` (NEW)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `.gitignore` (existing) — already excludes `.env`, `.venv`, `__pycache__/`, `*.py[codz]`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`
- `backend/` — has `__pycache__`, `.coverage`, `.pytest_cache`, `.ruff_cache`, `.venv` (verified via `ls backend/`)
- `frontend/` — has `node_modules/`, `out/`, `tsconfig.tsbuildinfo` (verified via `ls frontend/`)
- `.planning/`, `.claude/`, `.idea/` — agent metadata, never goes into the image
- `db/` — runtime SQLite mount target

**Complement-not-duplicate strategy:**

`.gitignore` already covers most Python artifacts. `.dockerignore` adds the build-context exclusions `.gitignore` does NOT cover (because they are tracked or intentionally not in `.gitignore`):

```
# Aggressive build context exclusion (D-13)

# Frontend build artifacts (Stage 1 rebuilds these from source)
node_modules/
.next/
frontend/out/
frontend/node_modules/
frontend/.next/
frontend/tsconfig.tsbuildinfo

# Python venv/caches (not all are in .gitignore for backend/)
.venv/
backend/.venv/
__pycache__/
**/__pycache__/
*.pyc
*.pyo
backend/.pytest_cache/
backend/.ruff_cache/
backend/.coverage

# Runtime data (volume-mounted at run time)
db/
db/*.db
*.sqlite3
*.sqlite3-journal

# Agent / IDE metadata (never in image)
.git/
.github/
.idea/
.claude/
.planning/
.vscode/

# Tests / docs (D-13: exclude *.md except README.md)
test/
tests/
backend/tests/
frontend/src/**/*.test.ts
frontend/src/**/*.test.tsx
*.md
!README.md
planning/

# Misc dev artifacts
.env
.envrc
savedfiles/
```

**Critical:** `.dockerignore` MUST exclude `frontend/out/` even though it currently exists on disk — Stage 1 must produce it freshly inside the build, and copying a stale host-built artifact into Stage 1 would defeat the deterministic build.

**Critical:** Do NOT exclude `backend/uv.lock` or `frontend/package-lock.json` — the build relies on them.

---

### `.env.example` (NEW — must mirror `.env` keys)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `.env` (existing, 94 bytes; contains `OPENROUTER_API_KEY = sk-or-v1-...`) — DO NOT copy the secret value; mirror the *key* only
- `backend/app/main.py:16` — `load_dotenv()` is the consumer
- `backend/app/lifespan.py:50-57` — env var consumption sites:
  ```python
  if (
      os.environ.get("LLM_MOCK") != "true"
      and not os.environ.get("OPENROUTER_API_KEY")
  ):
  ```
- `backend/app/lifespan.py:59` — `DB_PATH` (defaulted, but documented)
- `backend/app/market/factory.py:24` — `os.environ.get("MASSIVE_API_KEY")` (per codebase summary)
- `planning/PLAN.md` §5 — env var documentation

**Three keys, in this order, with verbatim text from CONTEXT.md D-12:**

```
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

**Format constraints:**
- No `KEY = value` (with spaces around `=`); use `KEY=value`. The existing `.env` uses spaces, but `--env-file` is finicky on the spaces; safer to use `KEY=value` in `.env.example` and let the user copy that style.
- No quotes around values.
- Newline-terminated.
- Order: required key first, optional second, mock-mode last.

**Default-must-boot constraint (SC#4):** With all three values blank/false, `cp .env.example .env && ./scripts/start_mac.sh` must boot the simulator-mode demo successfully — `MASSIVE_API_KEY=""` selects `SimulatorDataSource`, `OPENROUTER_API_KEY=""` only fails `/api/chat` (502 with graceful UI), `LLM_MOCK=false` is the default chat path.

**Update `.gitignore`:** Confirm `.env` is gitignored. `.gitignore:142` already has `.env` — no change needed. `.env.example` is committed (no entry needed).

---

### `scripts/start_mac.sh` (NEW; bash; macOS bash 3.2 + Linux bash 4+ portable)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `planning/PLAN.md` §11 — canonical `docker run` invocation:
  ```bash
  docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
  ```
- `.planning/phases/09-dockerization-packaging/09-CONTEXT.md` D-09, D-10, D-11 — script behavior
- `.env.example` (this phase) — document `cp .env.example .env` if `.env` missing

**Required behavior (D-09, D-10, D-11):**

1. `set -e` (fail fast); `set -u` is OK; do not use `set -o pipefail` if targeting bash 3.2 strictly (it's safe in 3.2 but verify).
2. Resolve script directory portably (works on macOS and Linux):
   ```bash
   SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
   REPO_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
   cd "$REPO_ROOT"
   ```
3. Parse flags: `--build` (force rebuild), `--no-open` (skip browser launch).
4. Image presence check (D-09):
   ```bash
   if ! docker image inspect finally:latest >/dev/null 2>&1 || [ "$FORCE_BUILD" = "1" ]; then
     docker build -t finally:latest .
   fi
   ```
5. Stop-then-start the container so the script is idempotent (re-running while a stale container exists must not fail):
   ```bash
   docker stop finally-app >/dev/null 2>&1 || true
   docker rm finally-app >/dev/null 2>&1 || true
   ```
6. Canonical run (D-05, mirrors PLAN.md §11):
   ```bash
   docker run -d --name finally-app \
     -v finally-data:/app/db \
     -p 8000:8000 \
     --env-file .env \
     finally:latest
   ```
7. Browser open (D-11), gated on success and `--no-open`:
   ```bash
   if [ "$NO_OPEN" != "1" ]; then
     case "$(uname)" in
       Darwin) open http://localhost:8000 ;;
       Linux)  command -v xdg-open >/dev/null && xdg-open http://localhost:8000 ;;
     esac
   fi
   ```
8. Print the URL last so users see it even when `--no-open` is set or the OS detection fails.

**Bash 3.2 compatibility constraints (macOS default):**
- No `[[ ... ]]` regex matches if avoidable (`[[` itself is fine; the `=~` regex behavior differs minorly).
- No associative arrays (`declare -A`) — bash 3.2 lacks them.
- No `mapfile`/`readarray` — bash 4+ only.
- Use `command -v` for command existence (POSIX).

**Idempotency invariants:**
- Running `start_mac.sh` while `finally-app` is already running must succeed (stop-then-start is the cleanest path).
- Running with `--build` while already built must rebuild and start.
- Running without `.env` must print a friendly message: `cp .env.example .env` and exit non-zero.

---

### `scripts/stop_mac.sh` (NEW)

**Source-of-truth files:** Same as `start_mac.sh`.

**Required behavior (D-10):**

```bash
#!/usr/bin/env bash
set -e
docker stop finally-app 2>/dev/null || true
docker rm finally-app 2>/dev/null || true
echo "FinAlly container stopped. Volume 'finally-data' preserved."
```

**Critical:** Do NOT remove the `finally-data` volume. Data persists by default. A `--purge` flag is a deferred idea (CONTEXT.md "Deferred Ideas").

**Exit code:** Always 0 if both `docker stop` and `docker rm` either succeed or "container not found" — `|| true` swallows the not-found case.

---

### `scripts/start_windows.ps1` (NEW; PowerShell 5.1+ default on Windows)

**Source-of-truth files:** Same as `start_mac.sh` — must implement the SAME `docker` arguments.

**Required behavior:**

1. `$ErrorActionPreference = "Stop"` (analog of `set -e`).
2. Resolve script root:
   ```powershell
   $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
   Set-Location $RepoRoot
   ```
3. Parse params via `param([switch]$Build, [switch]$NoOpen)`.
4. Image presence check:
   ```powershell
   docker image inspect finally:latest 2>$null | Out-Null
   if ($LASTEXITCODE -ne 0 -or $Build) {
     docker build -t finally:latest .
   }
   ```
5. Stop/remove existing container (idempotent):
   ```powershell
   docker stop finally-app 2>$null | Out-Null
   docker rm   finally-app 2>$null | Out-Null
   ```
6. Canonical run (same args as bash):
   ```powershell
   docker run -d --name finally-app `
     -v finally-data:/app/db `
     -p 8000:8000 `
     --env-file .env `
     finally:latest
   ```
7. Browser open (D-11):
   ```powershell
   if (-not $NoOpen) { Start-Process "http://localhost:8000" }
   ```

**PowerShell 5.1 compatibility:**
- No PowerShell 7-only operators (e.g., `??`, `?:` ternary).
- Use `Start-Process` for browser open (works on every Windows version with Docker Desktop).
- Backtick `` ` `` is the line-continuation char (do not use `\`).

**Critical:** Do NOT require WSL2 explicitly in the script — Docker Desktop on Windows handles it. The script should be runnable from PowerShell, Windows Terminal, or VS Code's integrated PowerShell.

---

### `scripts/stop_windows.ps1` (NEW)

```powershell
$ErrorActionPreference = "Stop"
docker stop finally-app 2>$null | Out-Null
docker rm   finally-app 2>$null | Out-Null
Write-Host "FinAlly container stopped. Volume 'finally-data' preserved."
```

Exit code semantics same as bash counterpart.

---

### `docs/DOCKER.md` (NEW — long-form reference)

**Source-of-truth files the planner MUST reference in `<read_first>`:**

- `planning/PLAN.md` §11 — canonical `docker run`, volume semantics
- `.planning/phases/09-dockerization-packaging/09-CONTEXT.md` — every D-decision becomes a doc section
- `Dockerfile` (this phase) — describe what each stage does
- `.env.example` (this phase) — describe each var

**Required sections (D-14):**

1. **Quickstart** — copy/paste:
   ```bash
   cp .env.example .env
   ./scripts/start_mac.sh   # or .\scripts\start_windows.ps1
   ```
2. **Canonical `docker run`** — verbatim from PLAN.md §11:
   ```bash
   docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
   ```
3. **Image architecture** — Stage 1 (Node 20 slim → static export) → Stage 2 (Python 3.12 slim + uv) — cite D-02.
4. **Volume semantics** — `finally-data` named volume, `/app/db` mount point, persists across `docker rm`, NOT removed by `stop_mac.sh` (D-10).
5. **`.env` workflow** — `--env-file .env` not baked in (D-06), copy `.env.example` to start, three keys explained.
6. **Troubleshooting**:
   - Port 8000 already in use → `lsof -i :8000` (mac/Linux) or `Get-NetTCPConnection -LocalPort 8000` (Windows)
   - Image not found → run `start_mac.sh --build`
   - Volume reset → `docker volume rm finally-data` (destructive — flagged)
7. **Windows PowerShell equivalents** for every command shown.

**Tone constraint (project rule):** No emojis. Concise. Short paragraphs. Match `README.md` voice.

---

### `README.md` update (NOT new — edit existing)

**Source-of-truth file:**

- `README.md` (existing, 50 lines, already has a "Quick Start" section at line 16-23 that references `scripts/start_mac.sh` and `.env.example`)

**Current README.md:16-23 (already correct in shape; verify accuracy after Phase 9 lands):**
```markdown
## Quick Start

```bash
cp .env.example .env     # add OPENROUTER_API_KEY
./scripts/start_mac.sh   # or scripts/start_windows.ps1
```

Open http://localhost:8000. You start with a 10-ticker watchlist and $10,000 in virtual cash.
```

**Phase 9 README change is minimal (D-14):** Verify the existing block matches the actual script names produced by Phase 9; add a single-line link to `docs/DOCKER.md` for the long-form reference. Do NOT expand the README into a Docker tutorial — that lives in `docs/DOCKER.md`.

**Suggested addition (one line):**
```markdown
For details on the Docker build, volume layout, and troubleshooting, see [`docs/DOCKER.md`](docs/DOCKER.md).
```

---

## Shared Patterns

These constraints apply to multiple Phase 9 artifacts:

### Cross-platform docker-CLI argument parity (start scripts)

**Apply to:** `scripts/start_mac.sh`, `scripts/start_windows.ps1` (and stop variants).

The `docker run` argument list MUST be IDENTICAL across the bash and PowerShell scripts. Only the shell-specific syntax (line continuation: `\` vs backtick, redirection: `>/dev/null 2>&1` vs `2>$null | Out-Null`) differs:

| Argument | Value | Why |
|----------|-------|-----|
| `-d` | (flag) | Detached so the script returns | 
| `--name` | `finally-app` | Stable name → `stop_*` scripts can target it |
| `-v` | `finally-data:/app/db` | Named volume, mirrors PLAN.md §11 |
| `-p` | `8000:8000` | Single-port contract |
| `--env-file` | `.env` | D-06: env mounted, not baked |
| (image) | `finally:latest` | D-09 build tag |

Drift between bash and PowerShell args = bug. The planner should write one plan-level checklist that asserts both scripts use the same six args.

### `.env` mirror invariant

**Apply to:** `.env.example`, `Dockerfile` (must NOT `COPY .env`), `lifespan.py` (already reads via `os.environ.get`).

The keys in `.env.example` MUST be exactly the three documented in `planning/PLAN.md` §5 and consumed in `backend/app/lifespan.py` and `backend/app/market/factory.py`:
- `OPENROUTER_API_KEY`
- `MASSIVE_API_KEY`
- `LLM_MOCK`

`DB_PATH` is set by the Dockerfile via `ENV DB_PATH=/app/db/finally.db` — it is NOT in `.env.example` (it is a container-internal concern, not a user-facing setting).

### Container layout invariant

**Apply to:** `Dockerfile`.

The container path layout MUST be:
```
/app/
├── backend/        ← WORKDIR; uvicorn runs here; uv project
│   ├── app/
│   │   ├── lifespan.py   ← parents[2] resolves to /app
│   │   ├── main.py
│   │   └── ...
│   ├── pyproject.toml
│   ├── uv.lock
│   └── .venv/      ← created by `uv sync --frozen --no-dev`
├── frontend/
│   └── out/        ← Stage 1 artifact; StaticFiles mount target
└── db/             ← VOLUME; SQLite finally.db lives here
```

This is a hard requirement of D-01 — alternatives would force a `lifespan.py` change, which is explicitly out of Phase 9 scope.

### No-emojis project rule

**Apply to:** All artifacts (Dockerfile comments, script echo/Write-Host messages, docs/DOCKER.md, README update).

CLAUDE.md project rule: "No emojis in code or in print statements or logging." Carry into Dockerfile comments, shell `echo`, PowerShell `Write-Host`, and Markdown docs.

---

## No Analog Found — Files Without Match

All seven new files have no in-repo analog. Rationale per file:

| File | Why no analog |
|------|---------------|
| `Dockerfile` | First Dockerfile in repo. Use `python:3.12-slim` + multi-stage as documented in PLAN.md §11 + D-02. |
| `.dockerignore` | First `.dockerignore`. Complement `.gitignore`; do not duplicate. |
| `.env.example` | First `.env.example`. Mirror `.env` keys (sanitized), document each per PLAN.md §5. |
| `scripts/start_mac.sh` | `scripts/` doesn't exist yet. Use docker-CLI directly; no project shell-script convention. |
| `scripts/stop_mac.sh` | Same as above. |
| `scripts/start_windows.ps1` | First PowerShell script in repo. Mirror bash counterpart's args. |
| `scripts/stop_windows.ps1` | Same as above. |
| `docs/DOCKER.md` | `docs/` doesn't exist. Match `README.md` tone; concise; no emojis. |

**Planner guidance for these files:** Lean on RESEARCH.md (Phase 9) for current Dockerfile best practices (`uv` images, multi-stage tips, `--no-cache-dir`, `apt-get` caches, `.python-version` files, etc.) — but the in-repo invariants in this PATTERNS.md TAKE PRECEDENCE over generic best-practice docs.

---

## Metadata

**Analog search scope:** repo root, `backend/`, `backend/app/`, `frontend/`, `.planning/`, `planning/`, `.gitignore`.

**Files scanned (read for constraint extraction):**
- `.planning/phases/09-dockerization-packaging/09-CONTEXT.md` (decisions D-01..D-14)
- `.planning/PROJECT.md` (validated requirements)
- `.planning/REQUIREMENTS.md` (OPS-01..04 acceptance criteria)
- `.planning/ROADMAP.md` (Phase 9 SC#1..4)
- `planning/PLAN.md` §3, §4, §5, §11 (project spec)
- `backend/pyproject.toml` (Python version, deps)
- `backend/app/lifespan.py` (static_dir resolution, env var consumption)
- `backend/app/main.py` (uvicorn entrypoint, dotenv loader)
- `frontend/package.json` (Node engine, build script)
- `frontend/next.config.mjs` (output: 'export')
- `.gitignore` (complement strategy)
- `.env` (existing key shape — value redacted)
- `README.md` (existing Quick Start)
- Repo root `ls -la` (verified absence of Dockerfile, .dockerignore, .env.example, scripts/, docs/)
- `backend/uv.lock` exists (~451 KB) — confirms `uv sync --frozen` is viable
- `frontend/out/index.html` exists — confirms Stage 1 build target is the correct path

**Pattern extraction date:** 2026-04-26

**Files NOT scanned (out of scope for Phase 9 patterns):**
- `backend/app/chat/`, `backend/app/portfolio/`, `backend/app/watchlist/`, `backend/app/market/` source — these are runtime concerns; Phase 9 only cares that `app.main:app` imports cleanly inside the container and the `lifespan` reads the documented env vars.
- `frontend/src/**` — Phase 9 only cares that `npm run build` produces `frontend/out/`; the build is Phase 8's contract.
- `backend/tests/`, `frontend/src/**/*.test.ts*` — `.dockerignore` excludes them, but their content is irrelevant.
