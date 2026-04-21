---
phase: 03-portfolio-trading-api
plan: 02
subsystem: api
tags: [portfolio, trading, pydantic-v2, sqlite, domain-exceptions]

# Dependency graph
requires:
  - phase: 02-database
    provides: SQLite schema + seed (users_profile, positions, trades, portfolio_snapshots, watchlist) accessible via app.db
  - phase: 03-01
    provides: MarketDataSource.register_tick_observer contract (consumed by make_snapshot_observer in Plan 03-03 wiring)
provides:
  - backend/app/portfolio/models.py (Pydantic v2 schemas: TradeRequest/TradeResponse/PositionOut/PortfolioResponse/SnapshotOut/HistoryResponse)
  - backend/app/portfolio/service.py (execute_trade, get_portfolio, compute_total_value, get_history, make_snapshot_observer)
  - 5 domain exceptions (TradeValidationError base + InsufficientCash/InsufficientShares/UnknownTicker/PriceUnavailable) with class-attribute codes for HTTP translation by Plan 03-03
  - 27 service unit tests (buy/sell math, validation, valuation, history)
affects: [03-03, 05-ai-chat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-function service layer: free functions taking (conn, cache, ...) - no FastAPI imports (D-02)"
    - "Domain exception hierarchy with class-attribute error codes (D-09) for framework-free raising + HTTP translation at the router boundary"
    - "Validate-then-write with single conn.commit() at end of execute_trade (D-12) - on raise, zero rows written"
    - "Epsilon-delete for zero positions (|new_qty| < 1e-9) - survives IEEE 754 residuals on fractional buy/sell arithmetic (D-15)"
    - "Snapshot observer as a closure over app.state with time.monotonic() 60s cadence (D-05, D-06, D-07)"
    - "Pydantic v2 with ConfigDict(extra=forbid) on requests only; response models stay lenient for additive evolution"

key-files:
  created:
    - backend/app/portfolio/__init__.py
    - backend/app/portfolio/models.py
    - backend/app/portfolio/service.py
    - backend/tests/portfolio/__init__.py
    - backend/tests/portfolio/conftest.py
    - backend/tests/portfolio/test_service_buy.py
    - backend/tests/portfolio/test_service_sell.py
    - backend/tests/portfolio/test_service_validation.py
    - backend/tests/portfolio/test_service_portfolio.py
    - backend/tests/portfolio/test_service_history.py
  modified: []

key-decisions:
  - "D-02 realized: service.py has zero FastAPI imports - router translation lives in Plan 03-03"
  - "D-09 realized: 5-class exception hierarchy with `code: str` class attributes (trade_validation_error, insufficient_cash, insufficient_shares, unknown_ticker, price_unavailable) - N818 suppressed per-class because the plan mandates Suffix-free names as the ABI for Phase 5 auto-exec"
  - "D-12 realized: execute_trade runs all 4 writes (cash update, position upsert/delete, trades insert, portfolio_snapshots insert) inside sqlite3's implicit transaction and commits exactly once at the end; every raise path is pre-write"
  - "D-15 realized: `abs(new_qty) < 1e-9` deletes the positions row (not leaves a ghost zero-qty row); proved by test_full_sell_epsilon_handles_float_residual which exercises 0.1 + 0.2 - 0.3"
  - "D-16 realized: sell leaves avg_cost unchanged (avg_cost reflects buys only); proved by test_partial_sell_leaves_avg_cost_unchanged"
  - "Pydantic v2 idioms locked in: ConfigDict(extra=forbid) only on TradeRequest; Literal[\"buy\",\"sell\"] + Field(gt=0); no Optional/class Config; PEP-604 list[X]"
  - "Snapshot observer closure reads state.last_snapshot_at + state.db + state.price_cache and guards with time.monotonic(); Plan 03-03 will initialize state.last_snapshot_at = 0.0 in lifespan and call reset post-trade inside the route handler"

patterns-established:
  - "Service free-function pattern: first arg conn: sqlite3.Connection, second arg cache: PriceCache, last arg user_id: str = DEFAULT_USER_ID. Mirrors backend/app/db/seed.py."
  - "Fixtures for portfolio tests: fresh_db yields a seeded :memory: sqlite3.Connection with sqlite3.Row factory; warmed_cache pre-populates a PriceCache from SEED_PRICES so get_price is never None for the 10 defaults."
  - "Post-trade snapshot write: inside execute_trade (PORT-05 immediate-on-trade half); the periodic 60s half lives in make_snapshot_observer."

requirements-completed:
  - PORT-01
  - PORT-02
  - PORT-03
  - PORT-04

# Metrics
duration: 7m 6s
completed: 2026-04-21
---

# Phase 03 Plan 02: Portfolio Service + Models + Domain Exceptions Summary

**Pure-function trade execution + portfolio valuation + snapshot observer primitives with Pydantic v2 schemas and a 5-class domain exception hierarchy - zero FastAPI coupling so Plan 03-03 can wrap them in an APIRouter and Phase 5 chat auto-exec can re-use them for LLM-driven trades.**

## Performance

- **Duration:** 7m 6s
- **Started:** 2026-04-21T13:08:12Z
- **Completed:** 2026-04-21T13:15:18Z
- **Tasks:** 4
- **Files modified:** 10 created, 0 modified

## Accomplishments

- `backend/app/portfolio/service.py` exposes `execute_trade`, `get_portfolio`, `compute_total_value`, `get_history`, `make_snapshot_observer` as free functions - all written without a single FastAPI import (D-02).
- 5-class domain exception hierarchy: `TradeValidationError` base (code `trade_validation_error`) plus `InsufficientCash`, `InsufficientShares`, `UnknownTicker`, `PriceUnavailable`, each with a stable `code: str` class attribute Plan 03-03 can translate to HTTP 400 payloads (D-09, D-10).
- `execute_trade` writes cash + position + trade + snapshot inside one implicit sqlite3 transaction, commits exactly once at the end; validation failures raise pre-write so zero rows change (D-12). Epsilon delete (`abs(new_qty) < 1e-9`) survives IEEE 754 residuals on fractional trades (D-15), proved by `0.1 + 0.2 - 0.3`.
- `get_portfolio` falls back to `avg_cost` when `cache.get_price` is `None` (cold-boot case), computes unrealized P&L and % change, and orders positions `ticker ASC`.
- `make_snapshot_observer(state)` returns a zero-arg closure that writes one `portfolio_snapshots` row per 60 monotonic seconds, ready for Plan 03-03 to register on the source via `register_tick_observer`.
- Pydantic v2 schemas in `models.py`: 6 models with `ConfigDict(extra="forbid")` on the request only, `Literal["buy","sell"]` for side, `Field(gt=0)` for quantity, PEP-604 types throughout.
- 27 service unit tests (`tests/portfolio/`): 6 buy, 6 sell, 6 validation, 6 valuation, 3 history - all pass. Full project suite: 134 passed, 0 skipped, ruff clean.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 portfolio test package + stubs** - `aab0202` (test)
2. **Task 2: Pydantic v2 schemas (models.py + package __init__.py)** - `02cebb4` (feat)
3. **Task 3: service.py with execute_trade + 5 domain exceptions + buy/sell tests** - `d4ddcd9` (feat)
4. **Task 4: valuation + history + snapshot observer + remaining tests** - `be438f1` (feat)

_Note: Plan used Wave-0 TDD - Task 1 landed 27 skipped stubs up front; Tasks 2-4 filled them in alongside the implementation (RED-via-skip, GREEN-via-implementation)._

## Files Created/Modified

- `backend/app/portfolio/__init__.py` (new) - Package facade. Re-exports 6 models + 5 exceptions + 5 service functions + DEFAULT_USER_ID constant.
- `backend/app/portfolio/models.py` (new) - Pydantic v2 schemas: TradeRequest (strict, extra=forbid), TradeResponse, PositionOut, PortfolioResponse, SnapshotOut, HistoryResponse.
- `backend/app/portfolio/service.py` (new) - `_compute_total_value_with` helper + `compute_total_value`, `get_portfolio`, `execute_trade`, `get_history`, `make_snapshot_observer` public functions + 5 exception classes. Module docstring `"Pure-function service: trade execution, portfolio valuation, history, snapshot observer."`.
- `backend/tests/portfolio/__init__.py` (new) - Package marker.
- `backend/tests/portfolio/conftest.py` (new) - `fresh_db` generator fixture (seeded :memory: connection), `warmed_cache` fixture (PriceCache pre-populated with SEED_PRICES).
- `backend/tests/portfolio/test_service_buy.py` (new) - 6 BUY tests: new position, weighted avg_cost across two buys, fractional quantity, snapshot write, trades write, commit atomicity.
- `backend/tests/portfolio/test_service_sell.py` (new) - 6 SELL tests: partial decrement, avg_cost unchanged on sell, full-sell row delete, epsilon delete for 0.1+0.2-0.3, snapshot write, trades write.
- `backend/tests/portfolio/test_service_validation.py` (new) - 6 validation tests: each of the 4 exceptions raises, DB state snapshot matches before/after, and error messages carry numeric context.
- `backend/tests/portfolio/test_service_portfolio.py` (new) - 6 valuation tests: empty positions, cache-hit current price, avg_cost fallback, total_value matches helper; compute_total_value with no positions and with mixed cache hits.
- `backend/tests/portfolio/test_service_history.py` (new) - 3 history tests: empty list, ASC ordering, limit param.

## Decisions Made

- **N818 `# noqa` per-line on the 4 domain-exception subclasses.** Ruff wants an `Error` suffix on exception class names; the plan and 03-RESEARCH.md explicitly name these `InsufficientCash`, `InsufficientShares`, `UnknownTicker`, `PriceUnavailable`. The names are ABI - Plan 03-03 uses them in `except` clauses, Phase 5 will re-raise them from chat auto-exec, and they appear verbatim in the PLAN frontmatter `artifacts.exports` list. The narrow per-line suppression keeps the project-wide ruff policy intact while honoring the plan.
- **`_compute_total_value_with(conn, cache, cash, user_id)` private helper.** Shared by the hot-path `execute_trade` snapshot write (which already has the post-trade cash in hand) and the public `compute_total_value` (which re-reads cash). Avoids redundant SQL reads inside `execute_trade` without forking the valuation math.
- **Test fixtures use class-level class naming but direct-import service functions.** Tests do not go through the `app.portfolio` facade for exception classes - they import exceptions from `app.portfolio` (the facade) but functions are also imported from the facade. All tests pass the `fresh_db` + `warmed_cache` fixtures from `conftest.py` - no local setup, no patching needed.
- **`DEFAULT_USER_ID = "default"` duplicated in `service.py` rather than imported from `app.db`.** Same value, but having it locally avoids a cross-package dependency on the DB layer for the single constant and matches the seed.py precedent of declaring its own copy. Both modules will always agree because the schema default is `'default'`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff N818 on plan-mandated exception class names**
- **Found during:** Task 3 (after adding the 4 domain exception subclasses)
- **Issue:** `uv run --extra dev ruff check app/ tests/` reports N818 on `InsufficientCash`, `InsufficientShares`, `UnknownTicker`, `PriceUnavailable` (wants `-Error` suffix). The plan mandates these exact names (see frontmatter `artifacts.exports`, 03-RESEARCH.md Code Examples lines 434-452, and the plan's `<behavior>` block).
- **Fix:** Added `# noqa: N818` per class. No project-wide ruff config change - the suppression is as narrow as possible and only covers classes explicitly enumerated by the plan.
- **Files modified:** `backend/app/portfolio/service.py` (4 class headers)
- **Verification:** `uv run --extra dev ruff check app/ tests/` → "All checks passed!"; plan's `grep -q "class InsufficientCash"` etc. acceptance criteria still match.
- **Committed in:** `d4ddcd9` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Suppression is minimal and preserves the plan-mandated ABI. No scope creep.

## Issues Encountered

None. All tests wrote correctly on the first pass; no test re-runs or debugging were needed. The hardest check was the `0.1 + 0.2 - 0.3` epsilon test, which passed because the epsilon guard `abs(new_qty) < 1e-9` is two orders of magnitude larger than the actual IEEE 754 residual (~5.5e-17).

## User Setup Required

None - this plan is a pure in-process library addition with no external services, no new dependencies, and no configuration. Pydantic v2 was already a transitive dependency via FastAPI.

## Next Phase Readiness

- **Plan 03-03 is directly unblocked.** It can import `create_portfolio_router` from `app.portfolio` (once it adds that file in its own Task 1), `execute_trade` / `get_portfolio` / `get_history` for the route bodies, `make_snapshot_observer` for the lifespan wire-up, and the 5 exception classes for the `except TradeValidationError: raise HTTPException(400, detail={"error": exc.code, "message": str(exc)})` translation (D-10).
- **Plan 03-03 contract reminders:**
  - `make_snapshot_observer(app.state)` expects `state.db`, `state.price_cache`, and `state.last_snapshot_at` attributes. Lifespan must set `app.state.last_snapshot_at = 0.0` BEFORE registering the observer, otherwise the first tick sees `time.monotonic() - None` and crashes.
  - The POST `/api/portfolio/trade` handler should reset `request.app.state.last_snapshot_at = time.monotonic()` after a successful trade - the observer's post-trade-snapshot invariant is that the per-60s clock restarts right after the inline snapshot write.
  - `execute_trade(ticker=...)` uppercases and strips its ticker argument internally; the handler can pass the ticker straight through from `TradeRequest`.
- **Phase 5 (AI Chat) reminder:** Auto-executed LLM trades should re-use `execute_trade` directly, and the 5 exception classes are the spec's trade-failure surface (`TradeValidationError` catch at the chat boundary, `exc.code` into the chat_messages.actions JSON).
- **No blockers. No concerns.**

## Self-Check: PASSED

Verification of all claims:

- `backend/app/portfolio/__init__.py` - FOUND (re-exports 13 names in `__all__`)
- `backend/app/portfolio/models.py` - FOUND (6 Pydantic v2 models, strict on TradeRequest only)
- `backend/app/portfolio/service.py` - FOUND (5 exception classes + 5 public functions + 1 private helper; `grep -c "from fastapi" service.py` → 0)
- `backend/tests/portfolio/__init__.py` - FOUND
- `backend/tests/portfolio/conftest.py` - FOUND (fresh_db + warmed_cache fixtures)
- `backend/tests/portfolio/test_service_buy.py` - FOUND (6 BUY tests pass)
- `backend/tests/portfolio/test_service_sell.py` - FOUND (6 SELL tests pass)
- `backend/tests/portfolio/test_service_validation.py` - FOUND (6 validation tests pass)
- `backend/tests/portfolio/test_service_portfolio.py` - FOUND (6 valuation tests pass)
- `backend/tests/portfolio/test_service_history.py` - FOUND (3 history tests pass)
- Commit `aab0202` (Task 1 stubs) - FOUND in git log
- Commit `02cebb4` (Task 2 models) - FOUND in git log
- Commit `d4ddcd9` (Task 3 service + buy/sell) - FOUND in git log
- Commit `be438f1` (Task 4 valuation/history/observer + tests) - FOUND in git log
- `cd backend && uv run --extra dev pytest tests/portfolio -q` → 27 passed, 0 failed, 0 skipped
- `cd backend && uv run --extra dev pytest -q` → 134 passed (107 Phase 1/2 + 27 new), no regressions
- `cd backend && uv run --extra dev ruff check app/ tests/` → All checks passed!

---
*Phase: 03-portfolio-trading-api*
*Completed: 2026-04-21*
