---
phase: 01-app-shell-config
verified: 2026-04-19T00:00:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
---

# Phase 1: App Shell & Config Verification Report

**Phase Goal:** A runnable FastAPI process that loads env, wires the lifespan (PriceCache + market source + SSE router), exposes `/api/health`, and has automated tests proving the end-to-end SSE flow.
**Verified:** 2026-04-19T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `uv run uvicorn app.main:app` starts a FastAPI process exposing `/api/health` returning `{"status": "ok"}` | VERIFIED | `backend/app/main.py:20` builds `app = FastAPI(lifespan=lifespan)`; `main.py:23-26` registers `/api/health` returning `{"status": "ok"}`. `from app.main import app` importable; routes list includes `/api/health`. Test `TestHealth.test_health_returns_ok` asserts HTTP 200 + body. |
| 2 | Lifespan constructs ONE PriceCache, selects+starts market source from MASSIVE_API_KEY, includes `create_stream_router(cache)` before yield | VERIFIED | `lifespan.py:36-44` — `cache = PriceCache()`, `source = create_market_data_source(cache)`, `await source.start(tickers)`, `app.state.price_cache = cache`, `app.state.market_source = source`, `app.include_router(create_stream_router(cache))` — all before `yield` on line 52. |
| 3 | Lifespan attaches cache + source to `app.state` and awaits `source.stop()` on shutdown | VERIFIED | `lifespan.py:42-43` attaches; `lifespan.py:53-54` `try/finally: await source.stop()`. Tests `test_attaches_price_cache_to_app_state`, `test_attaches_market_source_to_app_state`, `test_stops_source_on_shutdown` all pass. |
| 4 | `.env` loading drives source selection — `load_dotenv()` runs BEFORE `app = FastAPI(...)` | VERIFIED | `main.py:7` imports `load_dotenv`, `main.py:16` calls `load_dotenv()`, `main.py:20` constructs `app = FastAPI(lifespan=lifespan)`. Line order: 16 < 20. |
| 5 | Missing OPENROUTER_API_KEY logs a warning but does not raise | VERIFIED | `lifespan.py:31-34` warns via `logger.warning`. Test `test_missing_openrouter_key_logs_warning_and_proceeds` passes. |
| 6 | Simulator selected when MASSIVE_API_KEY is absent | VERIFIED | Delegated to `create_market_data_source`. Test `test_uses_simulator_when_massive_api_key_absent` asserts `isinstance(app.state.market_source, SimulatorDataSource)` — passes. |
| 7 | End-to-end SSE: `/api/stream/prices` serves `data:` frames in real time | VERIFIED | Tests `test_sse_emits_at_least_one_data_frame` and `test_sse_continues_emitting_as_cache_version_advances` pass against an in-process uvicorn server — real socket, real httpx streaming. |
| 8 | Cache seeded immediately on startup (all SEED_PRICES tickers) | VERIFIED | `lifespan.py:39-40` starts source with `list(SEED_PRICES.keys())`. Test `test_seeds_cache_immediately_on_startup` passes. |
| 9 | `/api/stream/prices` route registered on app.router during lifespan | VERIFIED | Test `test_includes_sse_router_during_startup` asserts `/api/stream/prices` in `app.router.routes` inside LifespanManager — passes. |
| 10 | No `__main__` block in main.py (D-03) | VERIFIED | grep returns no match for `if __name__ == "__main__":` in main.py. |
| 11 | No SSE router mounted in main.py (D-04) | VERIFIED | grep returns no match for `create_stream_router` in main.py. |
| 12 | Automated tests pass: 83/83 green | VERIFIED | `uv run --extra dev pytest -q` reports `83 passed, 85 warnings in 1.94s`. `uv run --extra dev ruff check app/ tests/` reports `All checks passed!`. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/lifespan.py` | @asynccontextmanager lifespan wiring PriceCache + source + SSE router | VERIFIED | 55 lines (>=25). Contains `@asynccontextmanager`, `async def lifespan(app: FastAPI)`, all required calls (`app.state.price_cache = cache`, `app.state.market_source = source`, `app.include_router(create_stream_router(cache))`, `await source.start(tickers)`, `await source.stop()`). |
| `backend/app/main.py` | FastAPI entrypoint with /api/health + lifespan wired | VERIFIED | 26 lines (>=18). Contains `from dotenv import load_dotenv`, `from .lifespan import lifespan`, `load_dotenv()` (line 16), `app = FastAPI(lifespan=lifespan)` (line 20), `@app.get("/api/health")` returning `{"status": "ok"}`. No `__main__`, no `create_stream_router`. |
| `backend/pyproject.toml` | python-dotenv runtime dep + httpx/asgi-lifespan dev deps | VERIFIED | Line 13: `"python-dotenv>=1.2.1"` in `[project].dependencies`. Lines 22-23: `"httpx>=0.28.1"` and `"asgi-lifespan>=2.1.0"` in `[project.optional-dependencies].dev`. |
| `backend/tests/test_lifespan.py` | >=7 async lifecycle tests with LifespanManager | VERIFIED | 98 lines (>=40). 7 tests in `TestLifespan` class. All pass. Uses `LifespanManager(app)`, `patch.dict(os.environ, {}, clear=True)`. |
| `backend/tests/test_main.py` | Health test + >=2 SSE tests | VERIFIED | 160 lines (>=40). `TestHealth` (1 test) + `TestSSEStream` (2 tests). All pass via real in-process uvicorn server + httpx streaming client. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `backend/app/lifespan.py` | `backend/app/market/__init__.py` | `from .market import PriceCache, create_market_data_source, create_stream_router` | WIRED | Line 11 matches pattern exactly. |
| `backend/app/lifespan.py` | `backend/app/market/seed_prices.py` | `from .market.seed_prices import SEED_PRICES` | WIRED | Line 12 matches pattern exactly. |
| `backend/app/lifespan.py` | FastAPI app instance | `app.state.price_cache =`, `app.include_router(create_stream_router(...))` | WIRED | Lines 42-44 match pattern exactly. |
| `backend/app/main.py` | `backend/app/lifespan.py` | `from .lifespan import lifespan` | WIRED | Line 10. |
| `backend/app/main.py` | `.env` | `load_dotenv()` called before `app = FastAPI(...)` | WIRED | Line 16 < line 20 — load-bearing order correct. |
| `backend/tests/test_main.py` | `/api/stream/prices` (lifespan-mounted) | `client.stream('GET', '/api/stream/prices')` via LifespanManager-equivalent uvicorn harness | WIRED | Lines 130, 152. |
| `backend/tests/test_lifespan.py` | `backend/app/lifespan.py` | `from app.lifespan import lifespan` + `LifespanManager(app)` | WIRED | Line 11, 35/42/50/61/71/84/93. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes | `uv run --extra dev pytest -q` | `83 passed, 85 warnings in 1.94s` | PASS |
| Ruff lint clean | `uv run --extra dev ruff check app/ tests/` | `All checks passed!` | PASS |
| App module importable with lifespan + health route | `uv run python -c "from app.main import app; print([r.path for r in app.routes])"` | `['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc', '/api/health']` — `/api/health` present at module import; SSE route mounts at lifespan entry (per D-04 design). | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| APP-01 | 01-01, 01-02 | FastAPI application with `lifespan` startup that constructs the shared PriceCache, selects and starts the market data source, and exposes `/api/health` | SATISFIED | `lifespan.py` constructs PriceCache + starts source; `main.py` builds `app = FastAPI(lifespan=lifespan)` + `/api/health`. Tests in `test_lifespan.py` and `test_main.py::TestHealth` pass. REQUIREMENTS.md marks `[x]`. |
| APP-03 | 01-01, 01-02 | `.env` loading at startup for OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK | SATISFIED | `python-dotenv>=1.2.1` in deps; `main.py:16` calls `load_dotenv()` before app construction; missing OPENROUTER warning path covered by test. REQUIREMENTS.md marks `[x]`. |
| APP-04 | 01-03 | Browser-consumable SSE confirmed end-to-end — real EventSource client receives ticks | SATISFIED | `test_main.py::TestSSEStream` runs an in-process uvicorn server on 127.0.0.1:<random_port>; real httpx streaming client receives >=1 and >=2 `data:` frames from `/api/stream/prices`. REQUIREMENTS.md marks `[x]`. |

No orphaned requirements. REQUIREMENTS.md traceability table marks all three (APP-01, APP-03, APP-04) complete against Phase 1.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | Scan of `lifespan.py`, `main.py`, `stream.py`, `test_lifespan.py`, `test_main.py` found no TODO/FIXME/placeholder comments, no `return {}` / `return []` / `return null` stubs, no `onClick={() => {}}`-equivalent empty handlers, no hardcoded mock data in production code, and no f-strings in logging calls. |

Code review (`01-REVIEW.md`) flagged 2 warnings + 4 info items — none block goal achievement:
- WR-01 (router re-entry risk) and WR-02 (docstring drift): noted as improvements; current behavior is correct because the lifespan runs once in production.
- IN-01..IN-04: convention drift + robustness notes; all non-blocking.

### Human Verification Required

None. All four Phase 1 success criteria are verified by automated tests:
1. `/api/health` 200 + body → `TestHealth`.
2. Lifespan wiring → 7 `TestLifespan` tests.
3. Real browser-equivalent SSE → `TestSSEStream` over real uvicorn socket.
4. Missing env vars don't crash → `test_missing_openrouter_key_logs_warning_and_proceeds` + `test_uses_simulator_when_massive_api_key_absent`.

The original plan had asked for SSE via ASGITransport; the Plan 03 executor proved that pattern cannot drain an infinite generator and substituted a real uvicorn server — this is a stronger verification, not a weaker one, because it matches what a real browser's EventSource sees on the wire.

### Gaps Summary

No gaps. Phase goal "a runnable FastAPI process that loads env, wires the lifespan (PriceCache + market source + SSE router), exposes `/api/health`, and has automated tests proving the end-to-end SSE flow" is achieved:

- Runnable FastAPI process: `uv run uvicorn app.main:app` works; `app.main:app` is a module-level FastAPI instance.
- Env loaded: `load_dotenv()` called before app construction.
- Lifespan wires everything: PriceCache built once, source selected+started from env, SSE router mounted, both attached to `app.state`, clean shutdown.
- `/api/health` exposed inline and verified.
- End-to-end SSE flow proved by a real-socket streaming test.
- Full suite: 83 passed, ruff clean.

Traceability in REQUIREMENTS.md already reflects completion (APP-01, APP-03, APP-04 checked; Phase 1 marked complete in ROADMAP.md).

---

*Verified: 2026-04-19T00:00:00Z*
*Verifier: Claude (gsd-verifier)*
