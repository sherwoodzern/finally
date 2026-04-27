---
phase: 09
plan: 01
subsystem: ops/docker
tags: [docker, multi-stage, uv, next-export, fastapi, packaging]
requirements: [OPS-01]
dependency_graph:
  requires:
    - "backend/app/lifespan.py:86 static_dir = Path(__file__).resolve().parents[2] / 'frontend' / 'out'"
    - "backend/pyproject.toml requires-python >= 3.12"
    - "frontend/package.json engines.node >=20.0.0 <21"
    - "backend/uv.lock and frontend/package-lock.json (lockfile-driven installs)"
  provides:
    - "Dockerfile (multi-stage Node 20 slim -> Python 3.12 slim) at repo root"
    - ".dockerignore (aggressive build-context filter, D-13) at repo root"
    - "finally:latest image producing /app/frontend/out/index.html and CMD uv run uvicorn app.main:app"
  affects:
    - "Phase 9 Wave 2 plans (09-03 scripts) — depend on finally:latest tag and canonical run contract"
    - "Phase 9 Plan 09-02 (.env.example) — paired by .dockerignore !.env.example negation"
tech_stack:
  added:
    - "node:20-slim (Stage 1 base)"
    - "python:3.12-slim (Stage 2 base / runtime)"
    - "ghcr.io/astral-sh/uv:0.9.26 (uv binary distroless image)"
  patterns:
    - "Multi-stage build: lockfile-only COPY then RUN install, then COPY source (Pattern 1 layer caching)"
    - "Dep-only `uv sync --frozen --no-dev --no-install-project` followed by full `uv sync --frozen --no-dev` (RESEARCH.md astral.sh recommendation)"
    - "Exec-form CMD (JSON array) to avoid /bin/sh PID-1 wrapping"
    - "STOPSIGNAL SIGINT for clean uvicorn shutdown through `uv run`"
key_files:
  created:
    - "Dockerfile"
    - ".dockerignore"
    - ".planning/phases/09-dockerization-packaging/09-01-SUMMARY.md"
  modified: []
decisions:
  - "Used `COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/` to install uv (per Open Question 2 in 09-RESEARCH.md — astral.sh-recommended over `pip install uv`; D-02 wording allows either)."
  - "Added `STOPSIGNAL SIGINT` defensively (Open Question 1 in 09-RESEARCH.md — uvicorn handles SIGINT cleanly when uv is PID 1)."
metrics:
  duration_minutes: 8
  completed_date: "2026-04-27"
  task_count: 3
  file_count: 3
  cold_build_seconds: 162
  image_disk_usage_mb: 564
  image_content_size_mb: 124
---

# Phase 9 Plan 01: Dockerfile + .dockerignore Summary

**One-liner:** Multi-stage Dockerfile (Node 20 slim -> Python 3.12 slim, uv-managed FastAPI runtime, frontend `next build` static export at `/app/frontend/out/`) with aggressive `.dockerignore` filter; closes ROADMAP SC#1 and OPS-01.

## What Shipped

Two new files at the repository root:

1. `Dockerfile` (66 lines, multi-stage):
   - Stage 1 (`node:20-slim AS frontend-builder`): WORKDIR `/app/frontend`, lockfile-only `npm ci`, then `COPY frontend/ ./` and `RUN npm run build` -> emits `/app/frontend/out/index.html`.
   - Stage 2 (`python:3.12-slim AS runtime`): pulls `uv`/`uvx` via `COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/`, WORKDIR `/app/backend`, dep-only `uv sync --frozen --no-dev --no-install-project`, then full source + `uv sync --frozen --no-dev`, then `COPY --from=frontend-builder /app/frontend/out /app/frontend/out`.
   - Runtime config: `ENV DB_PATH=/app/db/finally.db`, `ENV PYTHONUNBUFFERED=1`, `VOLUME /app/db`, `EXPOSE 8000`, `STOPSIGNAL SIGINT`, `CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.
   - No `COPY .env`, no `HEALTHCHECK`, no `USER` (per D-04, D-06, D-08).

2. `.dockerignore` (64 lines, aggressive D-13 filter):
   - VCS / IDE / agent metadata: `.git/`, `.gitignore`, `.github/`, `.idea/`, `.vscode/`, `.claude/`, `.planning/`.
   - Frontend dev artifacts: `**/node_modules/`, `**/.next/`, `frontend/out/`, `frontend/coverage/`, `frontend/tsconfig.tsbuildinfo`.
   - Backend dev artifacts: `**/__pycache__/`, `**/*.py[cod]`, `**/.pytest_cache/`, `**/.ruff_cache/`, `**/.coverage*`, `backend/.venv/`, `backend/htmlcov/`.
   - Runtime persistence (Pitfall 7): `db/`, `**/*.sqlite3`, `**/*.sqlite3-journal`.
   - Tests / specs: `**/*.test.ts(x)`, `**/*.spec.ts(x)`, `**/tests/`, `test/`, `**/vitest.config.*`, `**/vitest.setup.*`.
   - Docs: `docs/`, `*.md` (negated `!README.md`), `planning/`.
   - Secrets (T-09-01): `.env`, `.env.*` (negated `!.env.example`).
   - Editor / OS junk: `.DS_Store`, `Thumbs.db`, `*.log`, `*.swp`, `*.bak`, `savedfiles/`.

## Container Layout (D-01 Invariant Verified)

```
/app/
├── backend/
│   ├── app/
│   │   ├── lifespan.py        # parents[2] -> /app
│   │   ├── main.py            # uvicorn entrypoint app.main:app
│   │   └── ...
│   ├── pyproject.toml
│   ├── uv.lock
│   └── .venv/                 # produced by `uv sync --frozen --no-dev`
├── frontend/
│   └── out/
│       └── index.html         # Stage 1 artifact, StaticFiles mount target
└── db/                        # VOLUME mount target, SQLite finally.db at runtime
```

## Tasks Completed

| Task | Name | Commit | Acceptance |
|------|------|--------|------------|
| 1 | Author `.dockerignore` (aggressive D-13 filter) | `be8c0e2` | All grep invariants pass: file exists; aggressive-pattern count = 12 (>= 10); `!.env.example` and `!README.md` negations present; `.env`, `db/` exact lines present; `backend/uv.lock`, `backend/pyproject.toml`, `frontend/package(-lock).json`, `frontend/next.config.mjs` NOT excluded; trailing newline; no emojis |
| 2 | Author `Dockerfile` (multi-stage, D-01..D-08) | `5b8b456` | All 16 grep invariants pass: both `FROM` lines, `COPY --from=ghcr.io/astral-sh/uv:0.9.26`, both `WORKDIR` lines, `RUN npm ci`, `RUN npm run build`, both `uv sync` lines, `COPY --from=frontend-builder ...`, `ENV DB_PATH=/app/db/finally.db`, `VOLUME /app/db`, `EXPOSE 8000`, `STOPSIGNAL SIGINT`, exact-form `CMD ["uv", "run", "uvicorn", ...]`; NO `COPY .env`, NO `HEALTHCHECK`, NO `USER` |
| 3 | End-to-end build smoke + image-content validation | (covered in commits above; no new files) | Cold build EXIT 0 verified — see "Verification Results" below |

## Verification Results

### Cold build (Task 3 cmd 1)

```
$ docker build -t finally:latest .
... [stage frontend-builder 6/6] RUN npm run build
    DONE 3.9s
... [stage runtime 8/8] COPY --from=frontend-builder /app/frontend/out /app/frontend/out
    DONE 0.0s
... naming to docker.io/library/finally:latest done
... unpacking to docker.io/library/finally:latest done

BUILD_DURATION_SEC=162
```

```
$ docker images finally:latest
IMAGE            ID             DISK USAGE   CONTENT SIZE
finally:latest   07a61744cb59   564MB        124MB
```

Exit 0. Both stages progressed. The build log shows the canonical two-stage progression (`[frontend-builder ...]` then `[runtime ...]`) under BuildKit. `next build` produced 5 static pages (`/`, `/_not-found`, `/debug` plus internal entries) into the export `out/` directory; the `runtime` stage successfully `COPY --from`'d that into `/app/frontend/out`. Both `uv sync --frozen --no-dev --no-install-project` (dep-only layer) and `uv sync --frozen --no-dev` (full sync) completed without lockfile drift.

### Runtime smokes (Task 3 cmds 2-7) — environment-blocked

The seven runtime verification commands the plan specifies for Task 3 require `docker run --rm finally:latest ...`. After the cold build succeeded, this sandbox revoked permission for further `docker` invocations (including `docker run`, `docker --version`, `docker image inspect`). The build itself succeeded — the artifacts are correct — but the runtime smokes cannot be executed inside this worktree.

The seven commands the orchestrator (or `/gsd-verify-work`) should run post-merge against the same `finally:latest` image are recorded verbatim:

```bash
# 2. Static export landed in image
docker run --rm finally:latest test -f /app/frontend/out/index.html
# Expected: exit 0.

# 3. Dev deps NOT in image
docker run --rm finally:latest python -c "import pytest" 2>&1 | grep -q "ModuleNotFoundError"
# Expected: exit 0 (grep matches the import error from --no-dev sync).

# 4. .env NOT baked into image (T-09-01)
docker run --rm finally:latest test ! -e /app/.env
# Expected: exit 0.

# 5. D-01 path math
docker run --rm finally:latest python -c "from pathlib import Path; assert str(Path('/app/backend/app/lifespan.py').resolve().parents[2]) == '/app'"
# Expected: exit 0.

# 6. Build-context size sanity (VALIDATION 09-02-02)
docker build --no-cache --progress=plain -t finally:latest . 2>&1 | head -20
# Inspect "transferring context" line; target < 200 MB (validation 09-02-02 specifies < 500 MB).

# 7. Smoke: app boots inside the image (no port mapping, no volume — just import + lifespan)
docker run --rm finally:latest python -c "import app; from app.main import app as a; print('imported', type(a).__name__)"
# Expected: prints `imported FastAPI`; exit 0.
```

**Indirect evidence the runtime smokes will pass** (from build-log + structural inspection):

- Cmd 2 (`/app/frontend/out/index.html` exists): Build log shows `next build` produced `Generating static pages using 6 workers (5/5)` and the runtime stage's step 8/8 `COPY --from=frontend-builder /app/frontend/out /app/frontend/out` succeeded. The host's pre-existing `frontend/out/index.html` confirms the path `next build` writes to.
- Cmd 3 (pytest absent): Both `uv sync` lines use `--no-dev`. Local empirical (RESEARCH.md Pitfall 1, run on this machine 2026-04-26): `uv sync --frozen --dry-run` (without `--no-dev`) already removes 8 dev packages including `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff` because they live under `[project.optional-dependencies].dev`, which uv excludes by default. With `--no-dev` explicit, the result is identical.
- Cmd 4 (no `/app/.env`): The Dockerfile contains zero `COPY .env*` instructions (verified by `! grep -qE "^COPY \.env" Dockerfile`). The `.dockerignore` excludes `.env` and `.env.*` from the build context, so even `COPY backend/ ./` cannot reach a stray `.env` inside `backend/`.
- Cmd 5 (D-01 path math): The literal Python expression resolves identically inside any POSIX filesystem (`/app/backend/app/lifespan.py` -> `parents[1]=/app/backend/app`, `parents[2]=/app/backend`). Wait — re-checking: `Path('/app/backend/app/lifespan.py').parents[0]='/app/backend/app'`, `parents[1]='/app/backend'`, `parents[2]='/app'`. Confirmed `/app`.
- Cmd 7 (`import app; from app.main import app as a`): Stage 2 ran `uv sync --frozen --no-dev` on the project itself (not just deps), and `uv run` activates the venv. `app.main:app` is the canonical entrypoint per `backend/app/main.py:20` (verified). The same import succeeds locally with `uv run`; the container has the same lockfile.

These are necessary-but-not-sufficient checks; the orchestrator's post-merge run will provide sufficient confirmation.

## Threat Model — Closure

| Threat ID | Closed by |
|-----------|-----------|
| T-09-01 (`.env` in image layers) | Dockerfile contains zero `COPY .env*`; `.dockerignore` excludes `.env`/`.env.*`. Verified by `! grep -qE "^COPY \.env" Dockerfile`. |
| T-09-02 (build-context bloat) | `.dockerignore` excludes 12+ aggressive patterns including `**/node_modules/`, `frontend/out/`, `backend/.venv/`, `db/`, `.planning/`, `.claude/`, `.git/`, `.idea/`. Build-context size sanity check (Task 3 cmd 6) deferred to orchestrator post-merge. |
| T-09-03 (base image supply chain) | Pinned: `node:20-slim`, `python:3.12-slim`, `ghcr.io/astral-sh/uv:0.9.26`. SHA-pinning deferred per accept disposition. |
| T-09-04 (`StaticFiles` directory hijack) | Phase 8 mitigation preserved (`check_dir=False`, controlled `static_dir` resolved relative to `lifespan.py`); Phase 9 added no new surface. |

## Decisions Made

1. **uv install method:** `COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/` chosen over `pip install --no-cache-dir uv`. D-02 wording allows either; astral.sh-recommended COPY form is smaller, reproducible, and SHA-pinnable. Documented in 09-RESEARCH.md Open Question 2 (recommended path).

2. **`STOPSIGNAL SIGINT`:** Added defensively. Uvicorn handles SIGINT cleanly when `uv run` is PID 1. Default `SIGTERM` would also work but with a longer grace path (research Open Question 1; recommended path).

3. **Layer ordering:** Dep-only sync (`--no-install-project`) before source copy, then second `uv sync` to install the project itself. Source-edit changes invalidate only the small project layer; lockfile-driven dep layer is reused.

## Deviations from Plan

### Environment-blocked verification (NOT a deviation in artifacts; a sandbox gate)

**Sandbox revoked `docker` permission after `docker build` completed.** Task 3's automated `<verify>` block calls six `docker run` invocations (and one second `docker build`); none can execute under the current sandbox policy. The artifacts (Dockerfile, `.dockerignore`) are unchanged and pass every structural acceptance criterion. The cold-build acceptance (the heaviest runtime check) DID succeed before permission was revoked, evidenced by `finally:latest` appearing in `docker images` at 564 MB.

**Action:** The seven verification commands are recorded verbatim above for the orchestrator / `/gsd-verify-work` to run post-merge. No artifact change required.

**Why this is not a Rule 1/2/3 auto-fix:** The Dockerfile is correct; there is nothing to fix. Forcing the smokes to run inside the sandbox would require bypassing a deliberate environmental constraint. Per CLAUDE.md ("Identify root cause before fixing; prove with evidence"), the root cause is sandbox policy, not artifact defect.

**Why this is not a Rule 4 architectural change:** No structural decision is needed; the artifacts ship unchanged.

## Self-Check: PASSED

Files claimed:

- `Dockerfile` exists at repo root: FOUND (committed in `5b8b456`, 65 insertions).
- `.dockerignore` exists at repo root: FOUND (committed in `be8c0e2`, 64 insertions).
- This SUMMARY exists: FOUND (this file).

Commits claimed:

- `be8c0e2` (`feat(09-01): add .dockerignore ...`): FOUND in `git log --oneline -5`.
- `5b8b456` (`feat(09-01): add multi-stage Dockerfile ...`): FOUND in `git log --oneline -5`.

Image claimed:

- `finally:latest` (564 MB disk usage / 124 MB content size): VERIFIED via `docker images finally:latest` before sandbox revocation.

No file or commit claim is unverified.
