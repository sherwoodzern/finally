# Phase 3: Portfolio & Trading API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 03-portfolio-trading-api
**Areas discussed:** Module & service layout, 60s snapshot cadence hook, Trade validation & error contract, Trade preconditions & edge cases

---

## Module & Service Layout

### Q1: Where should the portfolio code live?

| Option | Description | Selected |
|--------|-------------|----------|
| app/portfolio/ sub-package | routes.py + service.py + models.py, mirrors app/market/ and app/db/. Public surface via __init__.py. | ✓ |
| Flat app/portfolio.py | Single file with everything. Will outgrow itself once Phase 5 auto-exec lands. | |
| app/portfolio/ with routes.py only | No service split. Phase 5 chat would either re-implement trade logic or import from a router closure. | |

**User's choice:** app/portfolio/ sub-package (Recommended)
**Notes:** Aligns with the Phase 1 / Phase 2 pattern — short modules, public surface via __init__.py.

### Q2: How is the trade service called from handlers (and from chat in Phase 5)?

| Option | Description | Selected |
|--------|-------------|----------|
| Pure functions on (conn, cache, ...) | execute_trade(conn, cache, ticker, side, qty) — free functions, matches db/seed.py style. Trivially reusable from Phase 5 chat. | ✓ |
| PortfolioService class on app.state | class PortfolioService(db, cache). Adds indirection without state to justify it. | |
| FastAPI Depends-injected service | def execute_trade(db = Depends(get_db)). Couples service to FastAPI; awkward for non-HTTP callers. | |

**User's choice:** Pure functions taking (conn, cache, ...) (Recommended)
**Notes:** Service stays framework-agnostic — Phase 5 chat auto-exec imports and calls directly, no HTTPException coupling.

### Q3: How are response payloads typed?

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic BaseModel response models | PortfolioResponse, TradeResponse, etc. Auto-OpenAPI, auto-validation at the edge. | ✓ |
| Plain dict returns + to_dict() | Matches PriceUpdate pattern but still needs pydantic for request validation. | |
| @dataclass + manual serialization | Immutable dataclasses with to_dict(). Duplicates two type systems. | |

**User's choice:** Pydantic BaseModel response models (Recommended)
**Notes:** Latest FastAPI best practice. Request-body validation comes for free via pydantic.

### Q4: Where does the request-body schema for POST /api/portfolio/trade live?

| Option | Description | Selected |
|--------|-------------|----------|
| Pydantic TradeRequest in app/portfolio/models.py | class TradeRequest(BaseModel): ticker, side: Literal['buy','sell'], quantity. Reused by Phase 5. | ✓ |
| TypedDict / dict in handler signature | Hand-written validation. More code, fewer deps, no auto-docs. | |

**User's choice:** Pydantic TradeRequest in app/portfolio/models.py (Recommended)
**Notes:** Same model reused by Phase 5 chat auto-exec.

---

## 60s Snapshot Cadence Hook

### Q1: How do we hook 60s portfolio snapshots to the existing price loop without a separate background task?

| Option | Description | Selected |
|--------|-------------|----------|
| Tick-observer callback on the market source | Add register_tick_observer() to MarketDataSource ABC. Both implementations invoke callbacks after each tick/poll. lifespan registers a snapshot observer. Clean module boundary. | ✓ |
| Lightweight asyncio.Task in lifespan | Spawn snapshot_loop() that sleeps 60s. Violates literal PLAN.md wording but is the simplest pattern. | |
| Hook inside PriceCache.update() | Cache calls post-update callback. Tighter coupling; thread-safety gets tricky on Massive path. | |
| Inline wall-clock check in SimulatorDataSource._run_loop | Would only work in simulator mode; breaks when MASSIVE_API_KEY is set. | |

**User's choice:** Tick-observer callback on the market source (Recommended)
**Notes:** Scoped change to already-Validated market code (adds one method to the ABC and both implementations). Explicit in CONTEXT.md D-04.

### Q2: Where does the "last snapshot timestamp" state live?

| Option | Description | Selected |
|--------|-------------|----------|
| app.state.last_snapshot_at | Float on app.state, initialized to 0.0 in lifespan startup. Matches Phase 1 D-02. | ✓ |
| Query SELECT MAX(recorded_at) every tick | 20× more DB reads than snapshots. Wasteful. | |
| Module-level variable in app/portfolio/service.py | Violates Phase 1 "no module-level singletons" rule. | |

**User's choice:** app.state.last_snapshot_at (Recommended)
**Notes:** Consistent with Phase 1 pattern.

### Q3: Does the immediate-after-trade snapshot also update the 60s clock?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — trade snapshot resets the 60s timer | After trade writes snapshot, set last_snapshot_at = now. Avoids back-to-back near-duplicates. | ✓ |
| No — 60s clock is wall-clock-only, trade snapshots are extra | History may contain two nearly identical snapshots around trade times. | |

**User's choice:** Yes — trade snapshot resets the 60s timer (Recommended)
**Notes:** Cleaner P&L series.

---

## Trade Validation & Error Contract

### Q1: What HTTP status code for trade rejections (insufficient cash / oversell)?

| Option | Description | Selected |
|--------|-------------|----------|
| 400 Bad Request | Business-rule failures. Keeps 422 for pydantic schema failures. | ✓ |
| 422 Unprocessable Entity | Conflates business-rule and schema failures. | |
| 409 Conflict | Unusual for trades. | |

**User's choice:** 400 Bad Request (Recommended)
**Notes:** Frontend switches on detail.error code, not status.

### Q2: What does the error response body look like?

| Option | Description | Selected |
|--------|-------------|----------|
| {"detail": {"error": "<code>", "message": "<human>"}} | Machine-readable code + human message. Frontend and Phase 5 LLM both served. | ✓ |
| {"detail": "<human message>"} | FastAPI default plain string. Frontend must string-match. | |
| Pydantic ErrorResponse top-level | Fights FastAPI default exception-handler contract. | |

**User's choice:** {"detail": {"error": "<code>", "message": "<human>"}} (Recommended)
**Notes:** Codes: insufficient_cash, insufficient_shares, unknown_ticker, price_unavailable.

### Q3: How does the handler surface these errors?

| Option | Description | Selected |
|--------|-------------|----------|
| Service raises domain exceptions; route translates to HTTPException | Service stays pure and FastAPI-agnostic — Phase 5 chat reuses it directly. | ✓ |
| Service raises HTTPException directly | Couples service to FastAPI. | |
| Service returns a result type (Ok \| Err) | More plumbing; not idiomatic Python. | |

**User's choice:** Service raises domain exceptions; route translates to HTTPException (Recommended)
**Notes:** Phase 5 chat catches the domain exceptions and formats failures into the chat reply instead of raising HTTP errors.

---

## Trade Preconditions & Edge Cases

### Q1: What happens if the ticker has no price in the cache yet?

| Option | Description | Selected |
|--------|-------------|----------|
| Reject the trade with 400 price_unavailable | PLAN.md says fills use the cached price. No cache tick → no fill price. | ✓ |
| Wait briefly for the first tick | Masks the edge case with async latency. | |
| Fall back to seed_prices.SEED_PRICES[ticker] | Silently prices a trade off stale seed data — demo-fragile. | |

**User's choice:** Reject with 400 price_unavailable (Recommended)
**Notes:** No silent fallbacks. Client retries if the race ever happens in practice (< 1s window).

### Q2: Can users trade tickers NOT in the watchlist?

| Option | Description | Selected |
|--------|-------------|----------|
| Reject with 400 unknown_ticker | PLAN.md §6: cache set = watchlist set. Simple rule: add it first. | ✓ |
| Allow any ticker the cache has | Decouples trade from watchlist semantically. | |
| Allow + auto-add to watchlist | Crosses into Phase 4 scope; makes /trade do two jobs. | |

**User's choice:** Reject with 400 unknown_ticker (Recommended)
**Notes:** Clean boundary between Phase 3 (trade) and Phase 4 (watchlist CRUD).

### Q3: When a sell brings quantity to 0, what happens to the positions row?

| Option | Description | Selected |
|--------|-------------|----------|
| Delete the row | Idiomatic "current holdings". Re-buy later creates fresh row with correct avg_cost. | ✓ |
| Keep the row with quantity=0 | Forces WHERE quantity > 0 filtering everywhere; preserves stale avg_cost. | |

**User's choice:** Delete the row (Recommended)
**Notes:** Epsilon-based zero check (abs(new_qty) < 1e-9) to handle float residuals on fractional sells.

### Q4: How is avg_cost computed on a BUY that adds to an existing position?

| Option | Description | Selected |
|--------|-------------|----------|
| Weighted average | (old_qty*old_avg + buy_qty*buy_price) / (old_qty + buy_qty). Standard brokerage cost basis. | ✓ |
| FIFO lot tracking | Requires new lots table not in PLAN.md §7. Overkill. | |
| Most recent buy price only | Wrong cost basis for P&L. | |

**User's choice:** Weighted average across the combined position (Recommended)
**Notes:** Sells don't alter avg_cost — only quantity.

---

## Claude's Discretion

Planner may pick the conventional answer without re-asking:
- Transaction isolation level for a trade (explicit BEGIN IMMEDIATE vs stdlib default)
- History endpoint query parameters (optional `limit` default-None)
- Position ordering in GET /api/portfolio (stable order of planner's choice)
- PositionOut field naming (snake_case, consistent across routes/models)
- Snapshot total_value fallback when a position has no cached price (reuse avg_cost rule)
- Test fixtures (extend Phase 1/2 _build_app helper + cache-warming fixture)
- Numeric formatting (2 dp, avoid Decimal)
- Pydantic request-body config (extra = "forbid" for strict input)

## Deferred Ideas

- Snapshot retention / trimming — revisit only if demo runtime grows.
- History pagination / date-range filter — v2.
- Atomicity of LLM multi-trade sequences (CONCERNS.md item 8) — Phase 5 decision.
- FIFO lot tracking / realized P&L — out of PLAN.md §7 scope.
- Trade confirmation / idempotency keys — v2.
- Decimal-precision trade math — unnecessary for simulated $10k portfolio.
- Auto-watchlist-add on trade — explicitly rejected (D-14).
