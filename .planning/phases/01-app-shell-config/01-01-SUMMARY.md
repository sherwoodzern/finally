---
phase: 01-app-shell-config
plan: 01
subsystem: api
tags: [fastapi, lifespan, asgi, env-config, market-data, python-dotenv, sse]

# Dependency graph
requires:
  - phase: inherited
    provides: PriceCache, create_market_data_source, create_stream_router, SEED_PRICES (from backend/app/market/)
provides:
  - FastAPI @asynccontextmanager lifespan wiring PriceCache + market data source + SSE router
  - python-dotenv as a runtime dependency for Phase 1 Plan 02 .env loading
  - app.state.price_cache and app.state.market_source contract for future handlers
affects: [01-02-main-app, 01-03-tests, 02-database, 03-portfolio, 04-watchlist, 05-chat]

# Tech tracking
tech-stack:
  added: [python-dotenv>=1.2.1]
  patterns: [async-contextmanager-lifespan, app-state-shared-objects, factory-closure-router-mount]

key-files:
  created:
    - backend/app/lifespan.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock

key-decisions:
  - "D-02 implemented: PriceCache constructed inside lifespan, attached to app.state, no module globals"
  - "D-04 implemented: create_stream_router(cache) mounted during lifespan startup (before yield)"
  - "Startup ticker set = list(SEED_PRICES.keys()) - single source of truth until Phase 2 DB watchlist"
  - "python-dotenv chosen over pydantic-settings/manual os.environ - smallest answer to APP-03"
  - "Missing OPENROUTER_API_KEY logs a single warning but does NOT raise (Phase 5 enforces)"
  - ".env loading deferred to Plan 02 main.py (runs BEFORE app/lifespan is constructed)"

patterns-established:
  - "Lifespan shell delegates all work to source.start()/source.stop() - owns no tasks itself"
  - "Shared objects attached to app.state instead of module-level globals (test-friendly)"
  - "Fail-loud on startup - no try/except around source.start() (only try/finally around yield)"
  - "Public-API imports from app.market; deep import only for SEED_PRICES (not re-exported)"

requirements-completed: [APP-01, APP-03]

# Metrics
duration: 3min
completed: 2026-04-19
---

# Phase 01 Plan 01: Lifespan Summary

**FastAPI `@asynccontextmanager` lifespan that builds the shared PriceCache, selects and starts the market data source from `MASSIVE_API_KEY`, mounts `create_stream_router(cache)` at startup, and stops the source cleanly on shutdown — plus python-dotenv wired as a runtime dependency for Plan 02's `.env` loading.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-19T23:55:59Z
- **Completed:** 2026-04-19T23:58:48Z
- **Tasks:** 2 / 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- Added `python-dotenv>=1.2.1` to `backend/pyproject.toml` via `uv add` (and refreshed `backend/uv.lock`) — Plan 02 will call `load_dotenv()` in `main.py` before the app is constructed.
- Created `backend/app/lifespan.py` — a 55-line async context manager that:
  - Warns (not raises) when `OPENROUTER_API_KEY` is missing (per CONTEXT.md missing-env policy).
  - Constructs one `PriceCache` and one market data source (`create_market_data_source(cache)`).
  - Starts the source with `list(SEED_PRICES.keys())` as the initial ticker set.
  - Attaches both to `app.state.price_cache` / `app.state.market_source`.
  - Calls `app.include_router(create_stream_router(cache))` BEFORE `yield` so `/api/stream/prices` is live for the app's lifetime.
  - Awaits `source.stop()` on shutdown.
- Ruff clean on the new module.
- 73 existing market-data tests still pass (no regression from the new dependency).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add python-dotenv runtime dependency via uv** — `09fed01` (chore)
2. **Task 2: Create backend/app/lifespan.py** — `25bff00` (feat)

## Files Created/Modified

- `backend/app/lifespan.py` (**created**) — FastAPI lifespan context manager wiring PriceCache + MarketDataSource + SSE router.
- `backend/pyproject.toml` (**modified**) — added `"python-dotenv>=1.2.1"` to `[project].dependencies`.
- `backend/uv.lock` (**modified**) — refreshed with python-dotenv package entry and its transitive closure.

## Decisions Made

- **D-02 honored verbatim.** `PriceCache` and the market data source are instantiated inside the lifespan and hung off `app.state`. No module-level singletons. This keeps the shell test-friendly (`LifespanManager` / `TestClient` both exercise it cleanly) and matches the factory-closure pattern already used by `create_stream_router(cache)`.
- **D-04 honored verbatim.** The SSE router is mounted during lifespan startup — `app.include_router(create_stream_router(cache))` runs before `yield`. This keeps the router's `price_cache` closure in lock-step with the single cache instance attached to `app.state`.
- **python-dotenv over alternatives.** The project did not already depend on `pydantic-settings` or hand-rolled config; python-dotenv is the smallest library that satisfies APP-03 and the hard constraint "missing values must not crash startup" (`load_dotenv()` is silent when `.env` is absent). Latest release (1.2.1, April 2026) resolved by `uv add` with no pin.
- **`.env` loading NOT performed in the lifespan.** Per the plan's `<action>` block, `load_dotenv()` belongs in `main.py` (Plan 02), BEFORE `app = FastAPI(lifespan=lifespan)` is constructed, so env vars are present when the factory reads `MASSIVE_API_KEY`.
- **Fail-loud on startup.** No `try/except` around `source.start(...)` — a startup failure must surface via uvicorn, per the project rule "no defensive programming". The only `try/finally` is the one around `yield`.

## Deviations from Plan

None — plan executed exactly as written. Every line of the `<action>` block in Task 2 was reproduced verbatim (with the only cosmetic adjustment being replacing em-dashes in two docstring sentences with ASCII hyphens to avoid any encoding surprises in subsequent file reads; substance unchanged).

## Issues Encountered

None. One minor note during verification: the plan's automated `verify` command `uv run python -c "import dotenv; print(dotenv.__version__)"` raised `AttributeError` because python-dotenv 1.2.1 no longer exposes `__version__` on the `dotenv` module. The plan's own acceptance criterion uses the canonical form `from dotenv import load_dotenv; load_dotenv()`, which does exit 0 — that criterion passed, so the task is done. No deviation: the intent (prove the dependency is installed and importable) is satisfied by the stronger acceptance check.

## Verification Results

From `backend/`:

- `grep -E '^\s*"python-dotenv' pyproject.toml` → `    "python-dotenv>=1.2.1",` (line 12)
- `uv sync --extra dev` → exit 0 (8 dev packages resolved)
- `uv run python -c "from dotenv import load_dotenv; load_dotenv()"` → exit 0
- `backend/uv.lock` line 511 → `name = "python-dotenv"`
- `wc -l app/lifespan.py` → 55 lines (>= 25 required)
- `uv run --extra dev ruff check app/lifespan.py` → `All checks passed!`
- `uv run python -c "from app.lifespan import lifespan; print(lifespan.__name__)"` → `lifespan`
- `uv run --extra dev pytest -q` → `73 passed` (no regression in existing market suite)

All `<acceptance_criteria>` blocks in the plan pass.

## User Setup Required

None — no external service configuration required. `.env` loading itself is Plan 02's job; Phase 5 will fail loud if `OPENROUTER_API_KEY` is missing at chat time.

## Next Phase Readiness

Plan 02 (`01-02-main-app`) can now:

- `from .lifespan import lifespan` and do `app = FastAPI(lifespan=lifespan)`.
- Call `load_dotenv()` once at the top of `main.py` before constructing the app — python-dotenv is already installed and locked.
- Rely on `request.app.state.price_cache` and `request.app.state.market_source` being populated by the time any route handler runs.
- Rely on `GET /api/stream/prices` being mounted automatically for the app's lifetime (no explicit router wiring needed in `main.py`).

No blockers. No concerns carried forward.

## Self-Check: PASSED

- `backend/app/lifespan.py` exists — verified on disk (55 lines).
- `backend/pyproject.toml` contains `python-dotenv>=1.2.1` — verified (line 12).
- `backend/uv.lock` contains `name = "python-dotenv"` — verified (line 511).
- Commit `09fed01` (Task 1) — present in `git log`.
- Commit `25bff00` (Task 2) — present in `git log`.
- 73 existing tests still pass — verified via `uv run --extra dev pytest -q`.
- Ruff clean on new module — verified.

---
*Phase: 01-app-shell-config*
*Completed: 2026-04-19*
