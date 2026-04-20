---
phase: 01-app-shell-config
plan: 02
subsystem: api
tags: [fastapi, entrypoint, env-config, health-check, dotenv, uvicorn]

# Dependency graph
requires:
  - phase: 01-app-shell-config-01
    provides: "lifespan @asynccontextmanager (backend/app/lifespan.py); python-dotenv runtime dep"
provides:
  - "backend/app/main.py — module-level `app: FastAPI` with Plan 01 lifespan attached"
  - "GET /api/health returning {\"status\": \"ok\"} inline (D-04)"
  - "load_dotenv() call site before app construction (APP-03 wiring point)"
  - "Canonical run command: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` (D-03)"
affects: [01-03-tests, 02-database, 03-portfolio, 04-watchlist, 05-chat, 08-frontend-mount, 09-docker]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "load_dotenv() BEFORE FastAPI(...) so env vars are set when lifespan reads MASSIVE_API_KEY"
    - "FastAPI ≥ 0.115 stdlib lifespan= constructor parameter (not @app.on_event)"
    - "Inline @app.get route decorator for trivial health probe (no separate module)"

key-files:
  created:
    - backend/app/main.py
  modified: []

key-decisions:
  - "D-01 honored: two-file shell (main.py + lifespan.py) — main.py is ~26 lines, just load_dotenv + app + health"
  - "D-03 honored: no `if __name__ == \"__main__\":` block — uvicorn invoked via CLI only"
  - "D-04 honored: /api/health defined inline in main.py; SSE router mounted by lifespan, not here"
  - "load_dotenv() placed at line 16, BEFORE app = FastAPI(...) at line 20 (load order is load-bearing)"
  - "Health endpoint is intentionally trivial — no `source` enrichment because source is attached AFTER construction (CONTEXT.md deferred)"

patterns-established:
  - "App module order: docstring -> future import -> stdlib -> third-party -> local -> load_dotenv() -> logger -> app -> routes"
  - "Trivial liveness probe: @app.get('/api/health') returning dict[str, str] — no DB, no I/O, constant-time"
  - "No defensive try/except around load_dotenv or FastAPI() — failures must surface via uvicorn"

requirements-completed: [APP-01, APP-03]

# Metrics
duration: 2min
completed: 2026-04-20
---

# Phase 01 Plan 02: Main App Summary

**FastAPI entrypoint (`backend/app/main.py`) that loads `.env` via `load_dotenv()` BEFORE constructing `app = FastAPI(lifespan=lifespan)`, defines `/api/health` inline returning `{"status": "ok"}`, and leaves SSE mounting to the Plan 01 lifespan — the canonical `uv run uvicorn app.main:app` command now boots the full shell.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-20T12:58:27Z
- **Completed:** 2026-04-20T13:00:31Z
- **Tasks:** 1 / 1
- **Files modified:** 1 (1 created, 0 modified)

## Accomplishments

- Created `backend/app/main.py` — a 26-line FastAPI entrypoint. `load_dotenv()` runs at import time BEFORE `app = FastAPI(lifespan=lifespan)` so `MASSIVE_API_KEY` is available when the Plan 01 lifespan enters and `factory.create_market_data_source` reads it.
- `/api/health` is registered inline (D-04) and returns `{"status": "ok"}` with HTTP 200.
- No `if __name__ == "__main__":` block (D-03). The canonical run command is `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`, and the same line will become the Phase 9 Docker `CMD`.
- No `create_stream_router` mount in `main.py` (D-04) — the SSE router is attached by `lifespan` during startup, keeping the factory-closure pattern drift-free.
- Ruff clean on the new module.
- 73 existing market-data tests still pass (no regression from the new import graph).

## Task Commits

Each task was committed atomically:

1. **Task 1: Create backend/app/main.py** — `d1ce0e8` (feat)

## Files Created/Modified

- `backend/app/main.py` (**created**) — FastAPI application entrypoint. 26 lines. Contains `load_dotenv()`, `app = FastAPI(lifespan=lifespan)`, and the `/api/health` route.

## Decisions Made

- **D-01 honored verbatim.** Shell split across two files — `main.py` (this plan) for the app instance + health probe, `lifespan.py` (Plan 01) for startup/shutdown. No `config.py` — deferred as premature for three env vars.
- **D-03 honored verbatim.** No `__main__` block; the same `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` line runs in local dev, tests, and production Docker (Phase 9).
- **D-04 honored verbatim.** `/api/health` is an inline `@app.get("/api/health")` returning `{"status": "ok"}` — no separate `health.py`. The SSE router is mounted by the lifespan during startup, not by `main.py`.
- **`load_dotenv()` placement is load-bearing.** It runs at line 16 (import time), BEFORE `app = FastAPI(lifespan=lifespan)` at line 20. When uvicorn later enters the lifespan, `os.environ` already carries `MASSIVE_API_KEY`, `OPENROUTER_API_KEY`, and `LLM_MOCK` — satisfying APP-03 and the hard constraint that missing values must not crash startup (`load_dotenv()` is silent on missing `.env`).
- **Health endpoint kept trivial.** The optional `"source": "simulator" | "massive"` enrichment was deferred — the source is attached to `app.state` AFTER construction, so reading it from a module-level decorator would require request scope, and ops visibility is a Deferred Idea in `01-CONTEXT.md`.
- **No defensive programming.** `load_dotenv()` is silent on a missing `.env`; FastAPI construction is allowed to crash loud if it ever fails. No `try/except` around either.

## Deviations from Plan

None — plan executed exactly as written. The `<action>` block was reproduced verbatim into `backend/app/main.py`.

## Issues Encountered

None.

## Verification Results

All `<acceptance_criteria>` from Task 1 pass:

- `backend/app/main.py` exists — 26 lines (>= 18 required).
- `grep -F 'from __future__ import annotations'` — line 3.
- `grep -F 'from dotenv import load_dotenv'` — line 7.
- `grep -F 'from fastapi import FastAPI'` — line 8.
- `grep -F 'from .lifespan import lifespan'` — line 10.
- `grep -nE '^load_dotenv\(\)'` — line 16.
- `grep -nE '^app\s*=\s*FastAPI\('` — line 20. **16 < 20 → load_dotenv precedes app construction.**
- `grep -F 'app = FastAPI(lifespan=lifespan)'` — matches (line 20).
- `grep -F '@app.get("/api/health")'` — matches.
- `grep -E 'return\s*\{"status":\s*"ok"\}'` — matches.
- `grep -nE 'if __name__ == .__main__.:'` — **no matches (D-03 satisfied)**.
- `grep -F 'create_stream_router'` — **no matches (D-04 satisfied; SSE router owned by lifespan)**.
- `cd backend && uv run --extra dev ruff check app/main.py` → `All checks passed!`
- `cd backend && uv run python -c "from app.main import app; print(app.title)"` → `FastAPI` (exit 0).
- `cd backend && uv run python -c "from app.main import app; routes=[r.path for r in app.routes]; assert '/api/health' in routes"` → exit 0. Routes: `['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/api/health']`.
- `cd backend && uv run --extra dev pytest -q` → `73 passed` (no regression).

Plan-level `<verification>` block also passes (ruff + importability + route assertion all green; manual `curl` smoke is Plan 03's scope).

## User Setup Required

None — no external service configuration required at this step. `.env` loading is now wired; Phase 5 will fail loud if `OPENROUTER_API_KEY` is missing at chat time.

## Next Phase Readiness

Plan 03 (`01-03-tests`) can now:

- Import `from app.main import app` and exercise the FastAPI app via `TestClient`, `httpx.AsyncClient`, or `LifespanManager` + `AsyncClient` for SSE.
- Assert `/api/health` returns `{"status": "ok"}` with HTTP 200.
- Drive the lifespan end-to-end: enter the `app` context, verify `app.state.price_cache` and `app.state.market_source` are populated, verify at least one `data:` frame arrives on `/api/stream/prices`, then exit cleanly.
- Run `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &` + `curl /api/health` as a manual smoke documented in the README.

No blockers. No concerns carried forward. APP-01 and APP-03 are now complete; APP-04 (browser-consumable SSE verified end-to-end) lands in Plan 03.

## Self-Check: PASSED

- `backend/app/main.py` exists — verified on disk (26 lines).
- Commit `d1ce0e8` (Task 1) — present in `git log` (`git log --oneline --all | grep d1ce0e8`).
- Line-order check: `load_dotenv()` at line 16 < `app = FastAPI(...)` at line 20 — load order correct.
- Ruff clean — verified.
- Import + route registration — verified via `uv run python -c ...`.
- 73 existing tests still pass — verified via `uv run --extra dev pytest -q`.
- No `__main__` block, no `create_stream_router` reference in `main.py` — verified by empty grep results.

---
*Phase: 01-app-shell-config*
*Completed: 2026-04-20*
