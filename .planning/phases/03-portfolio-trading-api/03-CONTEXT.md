# Phase 3: Portfolio & Trading API - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up the portfolio + trading HTTP layer against the seeded SQLite database:
`GET /api/portfolio` (cash, total value, positions with live prices + unrealized
P&L), `POST /api/portfolio/trade` (instant-fill market orders, fractional
quantities, no fees, no confirmation), `GET /api/portfolio/history` (time-ordered
`portfolio_snapshots` series). Snapshots are recorded immediately after each
trade, and every 60 seconds piggybacked on the existing market-data tick path.

**In scope:**
- `app/portfolio/` sub-package with `routes.py`, `service.py`, `models.py`.
- Mounting the portfolio router in `backend/app/lifespan.py` after the DB and
  market source are up (no change to mount order for SSE).
- Pydantic request/response models (`TradeRequest`, `PortfolioResponse`,
  `PositionOut`, `TradeResponse`, `SnapshotOut`, history response).
- Pure-function trade service: `execute_trade(conn, cache, ticker, side, qty)`
  returning a success result, raising domain exceptions on validation failure.
  Reusable from Phase 5 chat auto-exec.
- Portfolio valuation: cash + sum(qty * current_or_avg_cost_price).
- Snapshot recording: immediate-after-trade and 60s cadence via a tick-observer
  callback the lifespan registers on the market source.
- Adding a `register_tick_observer(callback)` extension point to
  `MarketDataSource` (+ both implementations) — a deliberate, scoped change to
  already-validated market code so Phase 3 can hook the price loop without
  reaching across module boundaries.

**Out of scope (belongs to later phases):**
- `/api/watchlist` CRUD and cache add/remove on mutation → Phase 4.
- `/api/chat` and LLM auto-exec of trades/watchlist changes → Phase 5
  (service is designed for reuse, but the wiring lands there).
- Any frontend rendering of the positions table, heatmap, or P&L chart
  → Phases 7–8.
- Dockerfile, `.env.example` changes, start/stop scripts → Phase 9.
- Playwright E2E for trade flows → Phase 10.

</domain>

<decisions>
## Implementation Decisions

### Module & Service Layout

- **D-01:** Portfolio code lives in `backend/app/portfolio/` sub-package mirroring
  `app/market/` and `app/db/`:
  - `routes.py` — FastAPI router factory (`create_portfolio_router(db, cache)`),
    thin handlers that parse pydantic bodies, call the service, translate
    domain exceptions to `HTTPException`.
  - `service.py` — pure functions on `(sqlite3.Connection, PriceCache, ...)`
    for trade execution, portfolio valuation, history retrieval, snapshot
    recording. No class state, no FastAPI imports.
  - `models.py` — pydantic `BaseModel`s for request/response schemas plus the
    trade-side `Literal['buy','sell']` enum.
  - `__init__.py` — explicit `__all__` re-exporting the router factory,
    service functions, and response models (matches `app/market/__init__.py`
    and `app/db/__init__.py` conventions).

- **D-02:** Trade service is a free function: `execute_trade(conn, cache,
  ticker, side, quantity) -> TradeResponse`. Matches `db/seed.py` style (free
  functions on `sqlite3.Connection`). Phase 5 chat auto-exec imports and calls
  it directly; HTTPExceptions are NOT raised from the service layer.
  Rejected: `PortfolioService` class on `app.state` (class ceremony without
  state to justify it), FastAPI `Depends`-injected service (couples service
  to FastAPI, awkward for non-HTTP callers).

- **D-03:** Pydantic v2 `BaseModel` response models for every endpoint
  (`PortfolioResponse`, `PositionOut`, `TradeResponse`, history payload).
  FastAPI auto-generates OpenAPI and validates request bodies at the edge.
  `TradeRequest` uses `Literal['buy','sell']` for `side` so malformed sides
  get a 422 from FastAPI before the handler runs. Rejected: `to_dict()` style
  (matches `PriceUpdate` but provides no request validation); split
  dataclass + pydantic (two type systems duplicated).

### 60-Second Snapshot Cadence

- **D-04:** Introduce a minimal tick-observer extension on
  `MarketDataSource`: `register_tick_observer(callback: Callable[[], None])`.
  `SimulatorDataSource._run_loop` invokes each registered callback after the
  per-tick cache writes; `MassiveDataSource._poll_once` invokes them after
  each successful poll. Observers run synchronously on the producer thread /
  event loop — they MUST be fast and must not raise (the market source wraps
  the invocation in a narrow `try/except` and logs, per
  `CONVENTIONS.md` error-handling style).

- **D-05:** The portfolio snapshot observer is registered in `lifespan` after
  the DB, cache, and source are constructed and started:
  `observer = make_snapshot_observer(app.state); source.register_tick_observer(observer)`.
  The factory closes over `conn`, `cache`, and `app.state` so observer code
  has no module-level globals (mirrors Phase 1 D-02 and Phase 2 D-01).

- **D-06:** "Last snapshot wall-clock" lives on `app.state.last_snapshot_at`
  as a `float`, initialized to `0.0` in lifespan startup. The observer reads
  `app.state.last_snapshot_at` and writes a new snapshot only when
  `now - last >= 60.0`. Matches Phase 1's `app.state` pattern; no
  module-level singletons; trivially reset per test by re-building the app.
  Rejected: `SELECT MAX(recorded_at)` on every ~500 ms tick (20× more queries
  than snapshots); module-level `_last_snapshot_at` (violates Phase 1 D-02).

- **D-07:** Immediate-after-trade snapshots reset the 60s clock:
  after `execute_trade()` writes its post-trade snapshot, the service sets
  `app.state.last_snapshot_at = now`. Prevents back-to-back snapshots a few
  seconds apart when the 60s tick fires right after a manual trade. History
  stays a clean, coarse-grained series with exact-timestamp rows only on
  genuine trade events.

- **D-08:** Observer-callback failures are NOT fatal to the tick loop. The
  market source's `try/except Exception` + `logger.exception(...)` around each
  observer call matches the existing pattern in
  `SimulatorDataSource._run_loop` (narrow exception handling at the loop
  boundary). A broken observer does not kill price streaming.

### Trade Validation & Error Contract

- **D-09:** Domain exceptions defined in `app/portfolio/service.py`:
  `InsufficientCash`, `InsufficientShares`, `UnknownTicker`,
  `PriceUnavailable`. All subclass a common `TradeValidationError` base for
  single-except catching in the handler. Service raises; it does NOT import
  FastAPI.

- **D-10:** Route translates each domain exception to
  `HTTPException(status_code=400, detail={"error": <code>, "message": <human>})`.
  Error codes (string enum): `insufficient_cash`, `insufficient_shares`,
  `unknown_ticker`, `price_unavailable`. Human messages include the
  relevant numbers (held quantity, requested quantity, cash balance,
  required cash) so the frontend and the Phase 5 LLM chat surface are both
  informative.

- **D-11:** HTTP `400 Bad Request` for business-rule rejections. `422` is
  reserved for pydantic-level body-validation failures (FastAPI default).
  The frontend switches on `detail.error` code, not on status.

- **D-12:** The trade endpoint is all-or-nothing. Validation runs BEFORE any
  DB writes (read cash balance / position, check math, read cached price);
  on success, the write sequence (update cash, upsert position, insert trade,
  insert snapshot) runs inside a single SQLite transaction with an explicit
  `conn.commit()` at the end. On validation failure, zero writes occur and
  `conn.rollback()` is not needed because nothing was staged.

### Trade Preconditions & Edge Cases

- **D-13:** Trade is rejected with `400 price_unavailable` when
  `cache.get_price(ticker)` returns `None`. PLAN.md §8 says fills use "the
  cached price" — no cached price means no fill. No fallback to `SEED_PRICES`
  (stale) and no wait-loop (hides the edge case behind latency). In practice
  this window is <1 s after onboarding a new ticker; the client simply
  retries.

- **D-14:** Trade is rejected with `400 unknown_ticker` when the ticker is
  not in the user's `watchlist` table. PLAN.md §6 guarantees the cache set
  equals the watchlist set, so cache-miss and watchlist-miss collapse to the
  same rejection — but the check is performed against `watchlist` so the
  error code is semantically accurate ("add it to your watchlist first").
  Rejected: auto-adding to watchlist as a side effect of `/trade` (crosses
  into Phase 4 scope and makes `/trade` do two jobs).

- **D-15:** A sell that zeros out a position `DELETE`s the row from
  `positions`. Uses an epsilon-based equality (`abs(new_qty) < 1e-9`) to
  handle floating-point residuals from fractional sells of the entire
  holding. A subsequent buy creates a fresh row with a fresh `avg_cost` —
  which is the correct cost-basis behavior (the prior position was closed).
  Rejected: keeping the row at `quantity = 0` (forces `WHERE quantity > 0`
  filtering everywhere and preserves a stale `avg_cost`).

- **D-16:** `avg_cost` on BUY: weighted average across the combined
  position — `new_avg = (old_qty * old_avg + buy_qty * fill_price) /
  (old_qty + buy_qty)`. On SELL, `avg_cost` is unchanged; only `quantity`
  decreases. Unrealized P&L remains meaningful. Rejected: FIFO lot tracking
  (requires a new `lots` table not in PLAN.md §7); most-recent-buy-only
  (wrong cost basis).

### Claude's Discretion

Planner may pick the conventional answer without re-asking.

- **Transaction isolation level for a trade.** Default stdlib `sqlite3`
  isolation is fine for a single-process single-user app (Phase 2 D-03
  already picked manual commit). If the planner wants explicit
  `BEGIN IMMEDIATE` to force write-lock acquisition up front, go ahead;
  otherwise the default implicit transaction on the first INSERT/UPDATE is
  acceptable.

- **History endpoint query parameters.** `GET /api/portfolio/history` defaults
  to returning all snapshots ordered by `recorded_at ASC`. If the planner
  wants a `limit` query param (default None, capped to e.g. 10_000) that's
  fine. No pagination / no date-range filter in v1 — single-user demo,
  snapshots accumulate at 1/min, so even a week of runtime is ~10k rows.

- **Position ordering in `GET /api/portfolio`.** Any stable order
  (`ticker ASC`, or `updated_at DESC`) is fine. The frontend will re-order
  for the heatmap / positions table anyway.

- **`PositionOut` fields and naming.** Must include ticker, quantity,
  avg_cost, current_price, unrealized_pnl, change_percent per ROADMAP
  Success Criterion #1. Exact snake_case names are at the planner's
  discretion; keep them consistent across `routes.py` and `models.py`.

- **Snapshot `total_value` fallback when a position has no cached price.**
  Use the same rule as `/api/portfolio`: fall back to `avg_cost` for that
  position when `cache.get_price(ticker)` is `None`. Service exposes a
  single `compute_total_value(conn, cache)` function reused by the handler
  and the snapshot observer.

- **Test fixtures.** Extend the Phase 1/2 `_build_app()` helper + `db_path`
  fixture from `backend/tests/conftest.py`. A trade-test fixture that
  pre-warms the cache (so `get_price` returns non-None) is expected.
  Mock the market source's tick-observer hook if the planner wants tight
  unit coverage on the 60s cadence logic without running the simulator.

- **Numeric formatting.** Prices already rounded to 2 dp in the cache;
  P&L/percentages rounded to 2 dp on output. Avoid `Decimal` — not worth
  the ceremony for a simulated portfolio.

- **Pydantic config.** Request bodies strict (`extra = "forbid"`) so typos
  like `{"Ticker": "AAPL"}` 422 at the edge. Response models can use the
  default lenient config.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (the source of truth)
- `planning/PLAN.md` §6 — "Set of tickers tracked by the price cache is the
  union of all tickers in the watchlist table" (backs D-14).
- `planning/PLAN.md` §7 — Schemas for `users_profile`, `positions`, `trades`,
  `portfolio_snapshots` (already live in `backend/app/db/schema.py`).
- `planning/PLAN.md` §8 — API endpoint table for
  `GET /api/portfolio`, `POST /api/portfolio/trade`,
  `GET /api/portfolio/history` — including the "reads current prices from the
  in-memory price cache for efficiency" clause and the `avg_cost` fallback on
  cold start.
- `planning/PLAN.md` §9 — LLM structured-output schema for trades (relevant
  because the Phase 3 service is the reuse target for Phase 5 auto-exec).

### Project planning
- `.planning/REQUIREMENTS.md` — PORT-01, PORT-02, PORT-03, PORT-04, PORT-05
  (the five requirements this phase delivers).
- `.planning/ROADMAP.md` — Phase 3 "Success Criteria" (all four must evaluate
  TRUE).
- `.planning/PROJECT.md` — Constraints (no over-engineering, no defensive
  programming, latest APIs, short modules).
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — `app.state` pattern
  (D-02), factory-closure routers mounted in lifespan (D-04).
- `.planning/phases/02-database-foundation/02-CONTEXT.md` — one long-lived
  `sqlite3.Connection` on `app.state.db` (D-01), `sqlite3.Row` row factory
  (D-02), manual commit (D-03).

### Codebase intel
- `.planning/codebase/CONVENTIONS.md` — module docstring, `from __future__
  import annotations`, `%`-style logging, narrow exception handling, no
  emojis, factory routers over globals.
- `.planning/codebase/CONCERNS.md` §"Architectural Risks" item 8 — LLM's
  ability to compose multi-step trades is NOT atomic across two trade calls
  (relevant to how Phase 5 uses this service, but acknowledged only in
  Phase 3 — service stays single-trade-atomic).

### Reusable code touched by Phase 3
- `backend/app/lifespan.py` — add portfolio router mount after market source
  start; register tick-observer; initialize `app.state.last_snapshot_at = 0.0`.
- `backend/app/main.py` — no changes expected (router mount happens in
  lifespan, matching Phase 1 D-04).
- `backend/app/db/__init__.py` / `seed.py` — extend surface with portfolio
  query helpers (e.g., `get_cash_balance`, `get_position`, `upsert_position`)
  OR put DB helpers inside `app/portfolio/service.py` — planner's call, but
  keep SQL near the data.
- `backend/app/market/interface.py` — add `register_tick_observer` to the
  `MarketDataSource` ABC.
- `backend/app/market/simulator.py` — invoke observers in
  `SimulatorDataSource._run_loop` after the per-tick cache writes.
- `backend/app/market/massive_client.py` — invoke observers in
  `MassiveDataSource._poll_once` after a successful poll.
- `backend/app/market/cache.py` — `cache.get_price(ticker)` is the price
  source for both trade execution and valuation; unchanged.
- `backend/tests/conftest.py` — `db_path` fixture stays; add a cache-warming
  fixture for trade tests.
- `backend/CLAUDE.md` — extend "Public imports" section with
  `from app.portfolio import create_portfolio_router, execute_trade, ...`
  after this phase lands.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`app.state.db`, `app.state.price_cache`, `app.state.market_source`** —
  already attached in `backend/app/lifespan.py` (Phase 1 + 2). Phase 3 adds
  `app.state.last_snapshot_at`.
- **`PriceCache.get_price(ticker) -> float | None`** — exact shape Phase 3
  needs for fill-price lookup and portfolio valuation.
- **`seed_defaults()` / `get_watchlist_tickers()` patterns** — free functions
  on `sqlite3.Connection` with module-level logger and explicit
  `conn.commit()`. D-02 service functions follow this shape directly.
- **`create_stream_router(cache)` factory** (`app/market/stream.py`) —
  template for `create_portfolio_router(db, cache)` in `app/portfolio/routes.py`.
- **Lifespan `try:/yield/finally:`** — extended in Phase 2 with `conn.close()`.
  Phase 3 has no new cleanup (observer is implicitly dropped when the
  `MarketDataSource` is stopped).

### Established Patterns
- Factory-closure routers, no module-level router objects
  (Phase 1 `create_stream_router`).
- One long-lived `sqlite3.Connection` with `check_same_thread=False` and
  `sqlite3.Row` rows — do NOT open per-request connections.
- Explicit `conn.commit()` after each write path (Phase 2 D-03). Trade
  execution commits exactly once at the end of the write sequence.
- `%`-style logging (`logger.info("Trade executed: %s %s x %.4f @ %.2f",
  ticker, side, qty, price)`), never f-strings in log calls.
- Narrow exception handling only at boundaries. The market-source tick loop
  already wraps its body in `try/except` + `logger.exception` — the
  observer-invocation site gets the same treatment (D-08).

### Integration Points
- `backend/app/lifespan.py` is the one runtime file that grows: add router
  mount + observer registration after `await source.start(tickers)` and
  before `yield`.
- `backend/app/market/interface.py` + the two implementations get a minimal
  `register_tick_observer` method. This is a deliberate, minimal change to
  already-validated market code — scope it tightly in planning.
- `backend/app/main.py` is untouched.
- Phase 1/2 `_build_app()` test helper and `db_path` fixture extend cleanly —
  trade tests build a fresh app, wait for one simulator tick so the cache is
  warm, then exercise `/api/portfolio/trade`.

</code_context>

<specifics>
## Specific Ideas

- User accepted all Recommended options across module layout (sub-package +
  pure-function service + pydantic models + pydantic request body) — aligned
  with Phase 1/2's "factory closures, no module-level singletons, short
  modules" pattern.
- User accepted the tick-observer extension on `MarketDataSource` as the
  cleanest way to satisfy PLAN.md's "no separate background task" rule
  without coupling market and portfolio modules. Explicit trade-off noted:
  this is a scoped change to Validated market code, not a market-data
  rewrite.
- User accepted `app.state.last_snapshot_at` as the 60s-clock location,
  consistent with Phase 1 D-02 ("no module-level singletons").
- User accepted "trade snapshot resets the 60s clock" (D-07) — cleaner
  history series, no back-to-back near-duplicate snapshots.
- User accepted the error contract as `400 + detail={"error", "message"}`
  with a fixed set of machine-readable error codes. This mirrors the shape
  Phase 5 chat will need to surface trade failures back through the LLM
  reply without string-matching.
- User accepted strict preconditions: reject trades when the cache has no
  price, reject trades on tickers not in the watchlist, delete positions
  when sells zero out quantity, weighted-average cost basis on buys. No
  silent fallbacks, no auto-create-watchlist-on-trade.

</specifics>

<deferred>
## Deferred Ideas

- **Snapshot retention / trimming.** At 1 snapshot / minute, a week of uptime
  is ~10k rows — fine for SQLite. Revisit only if demo runtime grows or
  history queries become slow.
- **`GET /api/portfolio/history` pagination / date-range filter.** Planner
  may add a `limit` query param (Claude's Discretion above); full
  pagination is v2 work.
- **Atomicity of LLM multi-trade sequences** (CONCERNS.md item 8). The
  service is single-trade-atomic; Phase 5 will decide whether to wrap a
  chat-turn's multi-trade sequence in a larger transaction or accept partial
  execution. Phase 3 stays scoped.
- **FIFO lot tracking / realized P&L accounting.** Out of scope —
  PLAN.md §7 stores only `(quantity, avg_cost)` per position.
- **Trade confirmation / idempotency keys.** PLAN.md §2 explicitly says
  "no confirmation dialog". If the chat's auto-exec ever wants idempotency
  for retries, add an `idempotency_key` column on `trades` in v2.
- **Decimal-precision trade math.** Floats are fine for a simulated
  $10k portfolio; revisit if a real-money integration is ever reconsidered
  (it's explicitly Out of Scope in PROJECT.md).
- **Auto-watchlist-add on trade.** Intentionally rejected (D-14). If a Phase
  5 UX decision wants "buy PYPL" to also add PYPL to the watchlist, that's
  a chat-layer convenience, composed from `watchlist.add` + `portfolio.trade`.

</deferred>

---

*Phase: 03-portfolio-trading-api*
*Context gathered: 2026-04-20*
