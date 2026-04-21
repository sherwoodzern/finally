---
phase: 03-portfolio-trading-api
plan: 03
subsystem: api
tags: [fastapi, apirouter, pydantic-v2, sqlite, lifespan, observer-pattern, integration-tests]

# Dependency graph
requires:
  - phase: 03-01
    provides: MarketDataSource.register_tick_observer contract (consumed by lifespan)
  - phase: 03-02
    provides: Portfolio service (execute_trade, get_portfolio, get_history, make_snapshot_observer) + 5 domain exceptions + 6 Pydantic v2 models
provides:
  - backend/app/portfolio/routes.py (create_portfolio_router factory)
  - /api/portfolio, /api/portfolio/trade, /api/portfolio/history HTTP endpoints
  - Lifespan wiring: app.state.last_snapshot_at, snapshot-observer registration, portfolio router mount
  - 24 new tests (15 route integration + 6 observer + 3 lifespan) + boot-time initial snapshot semantics
affects: [04-watchlist-api, 05-ai-chat-integration, 07-market-trading-ui, 08-portfolio-visualization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Factory-closure APIRouter mirroring create_stream_router (app/market/stream.py) - no module-level router state"
    - "Domain exception -> HTTP 400 translation at a single call site in the route handler (detail={error, message})"
    - "Route-level post-trade clock reset (request.app.state.last_snapshot_at = time.monotonic()) keeps the service FastAPI-agnostic (D-07)"
    - "FastAPI Query(default=1000, ge=1, le=1000) bounds - server-side rejection via 422 for out-of-range limit"
    - "Boot-time initial snapshot: first observer tick with last_snapshot_at == 0.0 fires unconditionally (assumption A2)"
    - "Integration test harness: asgi-lifespan.LifespanManager + httpx.ASGITransport against a fresh FastAPI(lifespan=lifespan) per test"

key-files:
  created:
    - backend/app/portfolio/routes.py
    - backend/tests/portfolio/test_routes_portfolio.py
    - backend/tests/portfolio/test_routes_trade.py
    - backend/tests/portfolio/test_routes_history.py
    - backend/tests/portfolio/test_snapshot_observer.py
    - .planning/phases/03-portfolio-trading-api/03-03-SUMMARY.md
  modified:
    - backend/app/portfolio/__init__.py
    - backend/app/portfolio/service.py
    - backend/app/lifespan.py
    - backend/tests/test_lifespan.py
    - .planning/phases/03-portfolio-trading-api/03-VALIDATION.md

key-decisions:
  - "D-03 realized: HTTPException(400, detail={error: exc.code, message: str(exc)}) at the single route catch point; same shape for all four domain codes"
  - "D-07 realized: request.app.state.last_snapshot_at = time.monotonic() AFTER service returns - observer will not double-snapshot for 60s post-trade"
  - "Boot-time initial snapshot (Rule 2 fix): make_snapshot_observer special-cases last_snapshot_at == 0.0 so the first tick always writes a snapshot; plan test_boot_time_initial_snapshot mocks monotonic=0.5 and requires a write; prior implementation gated on >=60s which would have dropped the boot snapshot in contrived test environments"
  - "FastAPI Query(ge=1, le=1000) used for /history?limit - out-of-range returns 422 via Starlette, not HTTPException(400); 400 path is reserved for business-rule violations on POST /trade only"
  - "Lifespan wiring order is load-bearing: app.state.last_snapshot_at = 0.0 MUST come before register_tick_observer(make_snapshot_observer(app.state)) because the closure reads state.last_snapshot_at on first tick"

patterns-established:
  - "APIRouter factory: create_portfolio_router(db, cache) returns a fresh router with prefix='/api/portfolio', tags=['portfolio']; no globals, no DI framework"
  - "Integration test preamble: patch.dict(os.environ, {'DB_PATH': str(db_path)}, clear=True) + async with LifespanManager(app) + httpx.ASGITransport(app=app)"
  - "Error-path assertion pattern: snapshot GET /api/portfolio before and after the failing POST, assert cash_balance and positions unchanged (validate-then-write invariant)"
  - "Observer unit tests: types.SimpleNamespace(db=conn, price_cache=cache, last_snapshot_at=x) + patch('app.portfolio.service.time.monotonic', return_value=y)"

requirements-completed:
  - PORT-01
  - PORT-02
  - PORT-03
  - PORT-04
  - PORT-05

# Metrics
duration: 7m 9s
completed: 2026-04-21
---

# Phase 03 Plan 03: Portfolio Routes + Lifespan Wiring Summary

**Mounted the Phase 3 HTTP edge on top of the Plan 02 service and the Plan 01 observer hook: three REST endpoints (GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history) wired into FastAPI via a factory-closure router, plus lifespan registration of the 60-second snapshot observer - closing PORT-01 through PORT-05 end-to-end with 24 new tests (158 green total, zero regressions, 100% coverage on app/portfolio/).**

## Performance

- **Duration:** 7m 9s
- **Started:** 2026-04-21T13:23:04Z
- **Completed:** 2026-04-21T13:30:13Z
- **Tasks:** 4
- **Commits:** 3 (plus this final metadata commit)
- **Test delta:** +24 tests (134 -> 158 passing, 0 skipped, 0 failed)

## Accomplishments

- `backend/app/portfolio/routes.py` (new) — `create_portfolio_router(db, cache)` returns a fresh APIRouter with `prefix="/api/portfolio"` and three handlers: `GET ""`, `POST "/trade"`, `GET "/history"`. Domain validation failures from `execute_trade` are caught once and re-raised as `HTTPException(400, detail={"error": exc.code, "message": str(exc)})`. Successful trades reset `request.app.state.last_snapshot_at = time.monotonic()` so the snapshot observer will not double-write within 60s of the inline post-trade snapshot.
- `backend/app/portfolio/__init__.py` now re-exports `create_portfolio_router` alongside Plan 02's 13 names.
- `backend/app/lifespan.py` gains three surgical additions: `app.state.last_snapshot_at = 0.0`, `source.register_tick_observer(make_snapshot_observer(app.state))`, and `app.include_router(create_portfolio_router(conn, cache))` — all between the existing `app.state.market_source = source` line and the try/yield/finally block.
- `backend/app/portfolio/service.py` (`make_snapshot_observer`) now special-cases the boot-time first tick: when `last_snapshot_at == 0.0` the observer writes a snapshot unconditionally (assumption A2), guaranteeing `/api/portfolio/history` is non-empty after the first tick even in contrived test environments where `time.monotonic()` might be small.
- 24 new tests: 15 route integration (3 portfolio + 9 trade + 3 history), 6 observer unit/integration, 3 lifespan. Full suite 158 passed, 0 skipped, 0 failed, ruff clean, `app/portfolio/` at 100% coverage.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 route + observer test stubs** — `558549f` (test)
2. **Task 2: Portfolio router + lifespan mount + 15 integration tests** — `1d5045c` (feat)
3. **Task 3: Snapshot observer tests + lifespan registration assertions** — `4368e2c` (feat)
4. **Task 4: Phase gate (full suite + VALIDATION.md status flip + SUMMARY.md)** — this commit

## Requirement Coverage (PORT-01..PORT-05)

| Req | Representative test(s) | Status |
|-----|------------------------|--------|
| PORT-01 | `tests/portfolio/test_routes_portfolio.py::TestGetPortfolio::test_returns_seeded_cash_balance_and_empty_positions` + `test_current_price_falls_back_to_avg_cost_when_cache_empty` + `test_positions_ordered_by_ticker_asc` | green |
| PORT-02 | `tests/portfolio/test_routes_trade.py::TestBuy::test_buy_happy_path` + `test_buy_fractional` + `TestSell::test_partial_sell_keeps_avg_cost` + `test_full_sell_deletes_row` | green |
| PORT-03 | `tests/portfolio/test_routes_trade.py::TestErrors::test_insufficient_cash` + `test_insufficient_shares` + `test_unknown_ticker` + `test_price_unavailable` + `TestSchema::test_rejects_malformed_body` | green |
| PORT-04 | `tests/portfolio/test_routes_history.py::test_empty_history_on_fresh_db` + `test_snapshots_ordered_asc` + `test_limit_param` | green |
| PORT-05 | `tests/portfolio/test_snapshot_observer.py::test_60s_threshold_writes_snapshot` + `test_trade_resets_clock` + `test_raising_observer_does_not_kill_tick_loop` + `tests/test_lifespan.py::test_registers_snapshot_observer_on_market_source` | green |

## Files Created/Modified

Created:
- `backend/app/portfolio/routes.py` (62 lines) — factory-closure APIRouter
- `backend/tests/portfolio/test_routes_portfolio.py` (3 tests)
- `backend/tests/portfolio/test_routes_trade.py` (9 tests across 4 classes)
- `backend/tests/portfolio/test_routes_history.py` (3 tests)
- `backend/tests/portfolio/test_snapshot_observer.py` (6 tests)

Modified:
- `backend/app/portfolio/__init__.py` — added `create_portfolio_router` re-export
- `backend/app/portfolio/service.py` — `make_snapshot_observer` boot-time special-case
- `backend/app/lifespan.py` — imports + 3 new wiring lines
- `backend/tests/test_lifespan.py` — 3 new assertions appended to `TestLifespan`
- `.planning/phases/03-portfolio-trading-api/03-VALIDATION.md` — status columns flipped to green

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Boot-time initial snapshot**
- **Found during:** Task 3 (`test_boot_time_initial_snapshot`)
- **Issue:** Plan 02's `make_snapshot_observer` gated every write on `now - state.last_snapshot_at >= 60.0`, so a mocked `time.monotonic()` returning `0.5` produced zero snapshots even though the plan's test asserts one write (assumption A2 in 03-RESEARCH.md). The real production flow still works because `time.monotonic()` on a long-running host is far larger than 60 — but the plan's explicit test encodes the contract "first tick after boot always writes", so the observer must special-case the `last_snapshot_at == 0.0` sentinel.
- **Fix:** `make_snapshot_observer` now bypasses the 60s gate when `state.last_snapshot_at == 0.0`. Subsequent ticks use the 60s threshold as before.
- **Files modified:** `backend/app/portfolio/service.py` (2 lines)
- **Verification:** All 27 existing Plan 02 service tests still green (no regression); `test_boot_time_initial_snapshot` passes; `test_registers_snapshot_observer_on_market_source` passes (observer advances `last_snapshot_at > 0.0` after the first tick).
- **Committed in:** `4368e2c` (Task 3 commit)

**2. [Rule 3 - Blocking] Lifespan wiring landed in Task 2 not Task 3**
- **Found during:** Task 2
- **Issue:** The plan assigns all three lifespan additions (`last_snapshot_at = 0.0`, `register_tick_observer`, `include_router(create_portfolio_router)`) to Task 3 Step A. But Task 2's 15 integration tests require the portfolio router to be mounted (hitting `/api/portfolio/*`) and the route handler needs `app.state.last_snapshot_at` to exist for its post-trade reset. Tests in Task 2 cannot pass without the lifespan already wired.
- **Fix:** Performed all three lifespan additions at the start of Task 2 so the Task 2 tests work; Task 3 then only needed to fill in the observer tests and extend `test_lifespan.py` with three assertions against the already-wired behavior.
- **Impact:** No scope creep — the final outcome is identical to what the plan describes. The three lifespan code lines land in the same file, in the same place, with the same semantics.
- **Committed in:** `1d5045c` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 missing-functionality, 1 blocking-reorder). No architectural changes. No user input required.

## Issues Encountered

- Plan 03-03's `test_trade_resets_clock` asserted `app.state.last_snapshot_at == 0.0` immediately after entering the lifespan — but with the boot-time snapshot semantics (A2), the first simulator tick fires the boot snapshot before the test can issue its POST. Adjusted the test to bracket the value by `[before, after] = [time.monotonic() pre-POST, time.monotonic() post-POST]` which captures the D-07 intent without racing the simulator.
- No test flakes observed across 5+ local runs of the full suite.

## User Setup Required

None. The new endpoints are reachable immediately via:
- `curl http://localhost:8000/api/portfolio`
- `curl -X POST http://localhost:8000/api/portfolio/trade -H 'Content-Type: application/json' -d '{"ticker":"AAPL","side":"buy","quantity":1}'`
- `curl http://localhost:8000/api/portfolio/history`

once `uv run uvicorn app.main:app` is running.

## Next Phase Readiness

- **Phase 4 (Watchlist API)** is unblocked. The same APIRouter + lifespan pattern established here (factory closure, `app.include_router`, exception -> HTTP 400 translation) will apply to `/api/watchlist` GET/POST/DELETE. The market source's `add_ticker`/`remove_ticker` hooks (Plan 01 observer-interface work) are already wired via `app.state.market_source`.
- **Phase 5 (AI Chat)** can re-use `service.execute_trade` directly for LLM-driven trade auto-execution. The five domain exception classes are the spec's trade-failure surface — chat can catch `TradeValidationError` and surface `exc.code` into the structured `actions` JSON written to `chat_messages`.
- **Phase 7 (UI)** can call `/api/portfolio`, `/api/portfolio/trade`, and `/api/portfolio/history` from the Next.js client without further backend work. The `TradeResponse` shape (ticker/side/quantity/price/executed_at/cash_balance/position_quantity/position_avg_cost) is sufficient to update the positions table, header totals, and heatmap on each fill.
- No blockers. No concerns. All five Phase 3 requirements pass.

## Self-Check: PASSED

Verification of all claims:

- `backend/app/portfolio/routes.py` — FOUND (contains `def create_portfolio_router`)
- `backend/app/portfolio/__init__.py` — FOUND (contains `create_portfolio_router` in `__all__`)
- `backend/app/lifespan.py` — FOUND (contains `last_snapshot_at = 0.0`, `register_tick_observer(make_snapshot_observer`, `create_portfolio_router(conn, cache)`)
- `backend/tests/portfolio/test_routes_portfolio.py` — FOUND (3 async tests)
- `backend/tests/portfolio/test_routes_trade.py` — FOUND (9 tests across 4 classes)
- `backend/tests/portfolio/test_routes_history.py` — FOUND (3 tests)
- `backend/tests/portfolio/test_snapshot_observer.py` — FOUND (6 tests)
- `backend/tests/test_lifespan.py` — FOUND (3 new assertions appended; total 13 tests)
- Commit `558549f` (Task 1 stubs) — FOUND in git log
- Commit `1d5045c` (Task 2 routes + lifespan) — FOUND in git log
- Commit `4368e2c` (Task 3 observer tests + lifespan assertions) — FOUND in git log
- `cd backend && uv run --extra dev pytest -q` → 158 passed, 0 failed, 0 skipped, no regressions
- `cd backend && uv run --extra dev ruff check app/ tests/` → All checks passed!
- `cd backend && uv run --extra dev pytest --cov=app` → app/portfolio/* at 100% coverage; full-suite coverage 97%

---
*Phase: 03-portfolio-trading-api*
*Completed: 2026-04-21*
