---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: context exhaustion at 95% (2026-04-21)
last_updated: "2026-04-21T20:54:32.609Z"
last_activity: 2026-04-21 -- Plan 04-02 completed (routes + lifespan mount + integration tests)
progress:
  total_phases: 10
  completed_phases: 4
  total_plans: 11
  completed_plans: 11
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-19)

**Core value:** One Docker command opens a Bloomberg-style terminal where prices stream live, trades execute instantly, and an AI copilot can analyze the portfolio and execute trades on the user's behalf.
**Current focus:** Phase 04 — watchlist-api

## Current Position

Phase: 04 (watchlist-api) — COMPLETE
Plan: 2 of 2
Status: Phase 04 complete; ready for /gsd-verify-work 4; next up Phase 05 (chat-llm)
Last activity: 2026-04-21 -- Plan 04-02 completed (routes + lifespan mount + integration tests)

Progress: [#########░] 92%

## Performance Metrics

**Velocity:**

- Total plans completed: 2
- Average duration: 2.5min
- Total execution time: 0.08 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 (App Shell) | 2 | 5min | 2.5min |

**Recent Trend:**

- Last 5 plans: 01-01 (3min), 01-02 (2min)
- Trend: Stable (fine-granularity single-task plans).

*Updated after each plan completion*
| Phase 01 P03 | 60min | 3 tasks | 6 files |
| Phase 03 P01 | 4m 9s | 4 tasks | 4 files |
| Phase 03 P02 | 7m 6s | 4 tasks | 8 files |
| Phase 03 P03 | 7m 9s | 4 tasks | 10 files |
| Phase 04 P01 | 4m 14s | 3 tasks | 9 files |
| Phase 04 P02 | 6m 22s | 4 tasks | 8 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Adopt `planning/PLAN.md` wholesale as v1 scope — all 40 Active requirements mapped to 10 phases.
- Market-data subsystem (MARKET-01..06) treated as Validated and inherited — not planned.
- Granularity is "fine" (10 phases; 3–6 requirements each); workflow flags enabled: research, plan_check, verifier, nyquist_validation, ui_phase, ai_integration_phase.
- D-02 (Plan 01-01): PriceCache is constructed inside the lifespan and attached to `app.state` — no module-level singletons.
- D-04 (Plan 01-01): SSE router `create_stream_router(cache)` is mounted during lifespan startup (before `yield`) so `/api/stream/prices` is live for the app's lifetime.
- Plan 01-01: python-dotenv chosen over pydantic-settings / manual `os.environ` — smallest dependency that satisfies APP-03 and the "missing values must not crash startup" constraint.
- Plan 01-01: `.env` loading happens in Plan 02's `main.py` BEFORE the app is constructed — not in the lifespan, so the factory sees env vars at construction time.
- Plan 01-01: Missing `OPENROUTER_API_KEY` logs a single warning but does NOT raise; Phase 5 will fail loud when `/api/chat` is hit.
- D-01 (Plan 01-02): Shell split across `backend/app/main.py` + `backend/app/lifespan.py` — no `config.py` (premature for three env vars).
- D-03 (Plan 01-02): No `if __name__ == "__main__":` block in `main.py`. Canonical run is `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`; the same line becomes Phase 9's Docker `CMD`.
- D-04 (Plan 01-02): `/api/health` defined inline in `main.py` returning `{"status": "ok"}`; SSE router is mounted by the lifespan, NOT by `main.py`.
- Plan 01-02: `load_dotenv()` runs at line 16 of `main.py` BEFORE `app = FastAPI(lifespan=lifespan)` at line 20 — load order is load-bearing (factory reads `MASSIVE_API_KEY` at lifespan entry).
- Plan 01-02: Health endpoint kept trivial (no `"source"` enrichment) because source is attached to `app.state` AFTER construction; ops visibility is a deferred idea.
- [Phase ?]: D-05 (01-03): SSE tests use a real in-process uvicorn server (not ASGITransport) — httpx ASGITransport buffers the full ASGI response and cannot drain infinite SSE generators.
- [Phase ?]: D-06 (01-03): create_stream_router builds a fresh APIRouter per call — pre-existing module-level router accumulated duplicate /prices routes across factory calls (Rule 1 auto-fix).
- [Phase ?]: 01-03: httpx and asgi-lifespan declared in [project.optional-dependencies].dev (not PEP 735 [dependency-groups]) to match uv sync --extra dev.
- [Phase ?]: 01-03: Fresh FastAPI(lifespan=lifespan) per test (via _build_app helper) — avoids shared state on module-level app.main.app across tests.
- [Phase 03]: 03-01: register_tick_observer declared as zero-arg Callable on MarketDataSource ABC; per-callback nested try/except + logger.exception in Simulator._run_loop and Massive._poll_once isolates broken observers from the tick/poll loop (D-04, D-08)
- [Phase 03]: 03-02: Portfolio service is pure functions (conn + cache + business args) with zero FastAPI imports — keeps service.py easy to unit-test and lets routes in 03-03 thin-wrap it (D-02)
- [Phase 03]: 03-02: Domain exception hierarchy rooted at TradeValidationError with `code: str` class attributes (`insufficient_cash`, `insufficient_shares`, `unknown_ticker`, `price_unavailable`) — routes in 03-03 map these 1:1 to 400-level responses (D-09)
- [Phase 03]: 03-02: execute_trade uses validate-then-write with a single conn.commit() at the end — any raise leaves zero DB writes, enforced by the 6-test validation suite asserting row-count invariants (D-12)
- [Phase 03]: 03-02: Positions with `abs(new_qty) < 1e-9` are DELETEd rather than stored as zero-quantity rows, preserving the "no position" invariant for both get_portfolio and future trade math (D-15)
- [Phase 03]: 03-02: Buy updates avg_cost as weighted-average `(old_qty*old_avg + new_qty*price)/(old_qty+new_qty)`; sell leaves avg_cost unchanged — realized P&L is a reporting concern, not a position-row concern (D-16)
- [Phase 03]: 03-02: make_snapshot_observer(state) returns a zero-arg closure checking `time.monotonic() - state.last_snapshot_at >= 60.0`; observer is registered in 03-03's lifespan, keeping the observer pattern decoupled from FastAPI itself (D-05, D-06, D-07)
- [Phase 03]: 03-03: create_portfolio_router(db, cache) is a factory-closure APIRouter mirroring create_stream_router — fresh router per call, no module-level state, prefix="/api/portfolio"; TradeValidationError subclasses translate 1:1 to HTTPException(400, detail={error: code, message: str(exc)}) at a single catch site (D-03, D-09, D-10)
- [Phase 03]: 03-03: Route-level post-trade clock reset (`request.app.state.last_snapshot_at = time.monotonic()`) keeps service.execute_trade FastAPI-agnostic; the observer only double-fires if a trade and a 60s-natural-tick collide within the same moment, which is now impossible (D-07)
- [Phase 03]: 03-03: Boot-time initial snapshot — make_snapshot_observer special-cases `last_snapshot_at == 0.0` so the first observer tick writes a snapshot unconditionally; Plan 02's pure 60s gate was tightened to `!= 0.0 and delta < 60` (Rule 2 fix, assumption A2 in 03-RESEARCH.md)
- [Phase 03]: 03-03: Integration test harness = `asgi_lifespan.LifespanManager` + `httpx.ASGITransport(app=app)` + `async with httpx.AsyncClient(...)` with a fresh `FastAPI(lifespan=lifespan)` per test and `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` — established as the canonical pattern for all remaining API phases
- [Phase 04]: 04-01: Watchlist service mirrors portfolio — pure functions on `(conn, cache, *args)` with zero FastAPI imports so Phase 5 chat auto-exec can import `add_ticker`/`remove_ticker` directly (D-02)
- [Phase 04]: 04-01: `normalize_ticker(value)` is a module-level helper shared by Pydantic `WatchlistAddRequest`'s `field_validator(mode="before")` and the future Plan 04-02 `DELETE /{ticker}` path-param pre-check — regex `^[A-Z][A-Z0-9.]{0,9}$`, service trusts its input (D-04)
- [Phase 04]: 04-01: Idempotent mutations return a status-literal discriminator (`AddResult(status="added"|"exists")`, `RemoveResult(status="removed"|"not_present")`) instead of raising — 04-02 translates all four to HTTP 200 with `WatchlistMutationResponse`, never 409/404 (D-06)
- [Phase 04]: 04-01: `add_ticker` uses `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` branching (one query, atomic, race-free); `remove_ticker` uses `DELETE` + `cursor.rowcount` — commit only when rowcount==1 (D-09)
- [Phase 04]: 04-01: `get_watchlist` orders `ORDER BY added_at ASC, ticker ASC` (same as `get_watchlist_tickers`) and falls back to `None` on every price field when the cache has no tick yet — never 0, never omitted (D-05, D-08)
- [Phase 04]: 04-02: create_watchlist_router(db, cache, source) factory mirrors create_portfolio_router; mounted natively in lifespan BEFORE `yield` (line 68, `# D-13`) so `/api/watchlist` + `/api/watchlist/{ticker}` are in app.router.routes the moment LifespanManager.__aenter__ returns — no shim, no post-startup registration
- [Phase 04]: 04-02: DB-first-then-source choreography with try/except around `await source.{add,remove}_ticker` only; post-commit source failure logs WARNING with `exc_info=True` and still returns 200 (D-11). DB row-count arithmetic asserted strictly as `== before + 1` / `== before - 1`, not `>=`
- [Phase 04]: 04-02: Idempotent mutation responses always 200 with `status="added"/"exists"/"removed"/"not_present"` (SC#4); never 409/404. Uniform discriminator lets Phase 5 LLM handler branch without HTTP-code sniffing (D-06)
- [Phase 04]: 04-02: Module-scoped `app_with_lifespan` + `client` fixtures with `@pytest_asyncio.fixture(loop_scope="module", scope="module")` + `pytestmark = pytest.mark.asyncio(loop_scope="module")` + module-scoped `event_loop_policy` override in each test file — required by pytest-asyncio 1.x for module-scoped async fixtures. 21 integration tests across 3 files, exactly 1 SimulatorDataSource start per file (runtime <1s per file, well under 30s VALIDATION.md budget)

### Pending Todos

None yet.

### Blockers/Concerns

From codebase analysis (`.planning/codebase/CONCERNS.md`) — carry into Phase 1 planning:

- `PriceCache` uses `threading.Lock` because `MassiveDataSource` writes via `asyncio.to_thread`. Must not be "simplified" to `asyncio.Lock` in the app-shell wiring.
- SSE generator polls at 500 ms and emits only on cache version change — no heartbeat. Watch for proxy-idle timeouts during demo.
- Daily-change baseline is session-relative; `session_start_price` must not be persisted to SQLite.
- Default seed tickers are duplicated across `seed_prices.py` and `market_data_demo.py`; Phase 2 DB seed must pick a single source of truth.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-21T20:54:32.605Z
Stopped at: context exhaustion at 95% (2026-04-21)
Resume file: None
Resumed: 2026-04-21 — Plan 04-02 executed (4 tasks, 4 new files + 4 modified, 22 new tests; 207/207 full suite green)
