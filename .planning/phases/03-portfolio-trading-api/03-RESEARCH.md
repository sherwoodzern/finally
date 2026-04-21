# Phase 3: Portfolio & Trading API - Research

**Researched:** 2026-04-20
**Domain:** FastAPI HTTP layer + SQLite write paths + pure-function trade service + tick-observer extension to the market-data subsystem
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Module & Service Layout
- **D-01:** Portfolio code lives in `backend/app/portfolio/` sub-package with `routes.py` (FastAPI router factory), `service.py` (pure functions on `(sqlite3.Connection, PriceCache, ...)`, no FastAPI imports), `models.py` (Pydantic v2 `BaseModel`s + the `Literal['buy','sell']` side enum), and `__init__.py` with explicit `__all__` re-exporting the router factory, service functions, and response models.
- **D-02:** Trade service is a free function `execute_trade(conn, cache, ticker, side, quantity) -> TradeResponse`. FastAPI-agnostic so Phase 5 chat auto-exec can reuse it. HTTPExceptions are NOT raised from the service layer.
- **D-03:** Pydantic v2 `BaseModel` for every request and response shape. `TradeRequest.side` uses `Literal['buy','sell']` so malformed sides get a 422 from FastAPI before the handler runs.

#### 60-Second Snapshot Cadence
- **D-04:** Extend `MarketDataSource` with `register_tick_observer(callback)`. `SimulatorDataSource._run_loop` invokes registered callbacks after per-tick cache writes; `MassiveDataSource._poll_once` invokes them after each successful poll. Observers must be fast and must not raise — invocation is wrapped in a narrow try/except that logs.
- **D-05:** The portfolio snapshot observer is registered in `lifespan` after DB, cache, and source are constructed and started: `observer = make_snapshot_observer(app.state); source.register_tick_observer(observer)`. The factory closes over `conn`, `cache`, and `app.state`.
- **D-06:** "Last snapshot wall-clock" lives on `app.state.last_snapshot_at` as a `float`, initialised to `0.0` in lifespan startup. The observer reads `app.state.last_snapshot_at` and writes a new snapshot only when `now - last >= 60.0`.
- **D-07:** Immediate-after-trade snapshots reset the 60s clock — after `execute_trade()` writes its post-trade snapshot, set `app.state.last_snapshot_at = now`.
- **D-08:** Observer-callback failures are NOT fatal to the tick loop. The market source's `try/except Exception` + `logger.exception(...)` around each observer call matches the existing narrow-exception-at-loop-boundary pattern.

#### Trade Validation & Error Contract
- **D-09:** Domain exceptions defined in `app/portfolio/service.py`: `InsufficientCash`, `InsufficientShares`, `UnknownTicker`, `PriceUnavailable`, all subclassing a common `TradeValidationError` base. Service raises; it does NOT import FastAPI.
- **D-10:** Route translates each domain exception to `HTTPException(status_code=400, detail={"error": <code>, "message": <human>})`. Codes: `insufficient_cash`, `insufficient_shares`, `unknown_ticker`, `price_unavailable`. Human messages include relevant numbers (held qty, requested qty, cash balance, required cash).
- **D-11:** HTTP 400 for business-rule rejections. 422 is reserved for Pydantic-level body-validation failures (FastAPI default). The frontend switches on `detail.error` code, not on status.
- **D-12:** Validate-then-write inside a single SQLite transaction. Reads (cash, position, cached price) and math run BEFORE any writes. On success, the write sequence (update cash, upsert position, insert trade, insert snapshot) runs as one transaction with an explicit `conn.commit()` at the end. On validation failure, zero writes occur.

#### Trade Preconditions & Edge Cases
- **D-13:** Reject with `400 price_unavailable` when `cache.get_price(ticker) is None`. No fallback to `SEED_PRICES`, no wait-loop.
- **D-14:** Reject with `400 unknown_ticker` when the ticker is not in the user's `watchlist` table. Check against `watchlist`, not the cache, so the error code is semantically accurate.
- **D-15:** A sell that zeros out a position `DELETE`s the row from `positions`. Epsilon check `abs(new_qty) < 1e-9` handles float residuals.
- **D-16:** `avg_cost` on BUY: `new_avg = (old_qty * old_avg + buy_qty * fill_price) / (old_qty + buy_qty)`. On SELL, `avg_cost` unchanged; only `quantity` decreases.

### Claude's Discretion
- Transaction isolation level (explicit `BEGIN IMMEDIATE` vs stdlib default implicit transaction).
- History endpoint query params — optional `limit` (default None, cap ~10_000). No pagination / no date-range filter in v1.
- Position ordering in `GET /api/portfolio` — any stable order (ticker ASC, or updated_at DESC).
- `PositionOut` field names (snake_case, consistent between `routes.py` and `models.py`).
- Snapshot `total_value` fallback when a position has no cached price — reuse the `avg_cost` rule via a single `compute_total_value(conn, cache)` helper shared by `/api/portfolio` and the snapshot observer.
- Test fixtures — extend the Phase 1/2 `_build_app()` helper and `db_path` fixture. Add a cache-warming fixture (`cache.update(ticker, price)` for seed tickers) for trade tests.
- Numeric formatting — 2 dp in responses, avoid `Decimal`.
- Pydantic config — request bodies `extra = "forbid"`; response models default lenient.

### Deferred Ideas (OUT OF SCOPE)
- Snapshot retention / trimming (fine at 1/min).
- `GET /api/portfolio/history` pagination / date-range filter (v2).
- Atomicity of LLM multi-trade sequences — Phase 5 decides; Phase 3 stays single-trade-atomic.
- FIFO lot tracking / realized P&L accounting — PLAN.md §7 stores only `(quantity, avg_cost)`.
- Trade confirmation / idempotency keys — PLAN.md §2 explicitly says "no confirmation dialog".
- Decimal-precision trade math — floats fine for simulated $10k.
- Auto-watchlist-add on trade — intentionally rejected (D-14).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PORT-01 | `GET /api/portfolio` returns positions, cash, total value, per-position unrealized P&L; live prices from the cache with graceful fallback to `avg_cost`. | §3 `get_portfolio()` signature + `compute_total_value()` + `PortfolioResponse` shape + PLAN.md §8 "reads current prices from the in-memory price cache for efficiency" clause. |
| PORT-02 | `POST /api/portfolio/trade` executes market orders (buy/sell, fractional), updates cash + `positions`, appends to `trades`. Instant fill at cached price, no fees, no confirmation. | §3 `execute_trade()` + §4 SQL write sequence + D-12 transaction semantics + cost-basis math (D-16). |
| PORT-03 | Reject buys without sufficient cash and sells exceeding held quantity; return structured errors. | §2 `TradeErrorDetail` + §3 domain exceptions + D-10/D-11 error contract. |
| PORT-04 | `GET /api/portfolio/history` returns the `portfolio_snapshots` time series. | §3 `get_history()` + §4 history SQL + `HistoryResponse` shape. |
| PORT-05 | Snapshot on every trade + 60s cadence piggybacked on the price-update loop (no separate task). | §5 tick-observer extension + §6 snapshot observer factory + D-05, D-06, D-07 lifespan wiring. |
</phase_requirements>

## Summary

Phase 3 adds a thin HTTP/service layer on top of already-shipped infrastructure: Phase 1 gave us the FastAPI `lifespan` with `app.state.price_cache` and `app.state.market_source`; Phase 2 gave us `app.state.db` and a seeded SQLite DB with the exact tables Phase 3 reads and writes (`users_profile`, `positions`, `trades`, `portfolio_snapshots`, `watchlist`). The portfolio package is a pure-function service plus a Pydantic v2 schema layer plus a factory-closure `APIRouter` — mirroring the pattern the existing `app/market/` and `app/db/` sub-packages already use. No new runtime dependencies are required (Pydantic v2.12.5, FastAPI 0.128.7, and httpx 0.28.1 are already installed).

The single deliberate, scoped change to already-validated code is adding `register_tick_observer(callback)` to the `MarketDataSource` ABC and to both concrete implementations (`SimulatorDataSource`, `MassiveDataSource`). The observer list is held on the source instance; callbacks fire inside the existing `try/except Exception` at the loop boundary (D-08), one nested try/except per observer call so a broken observer logs and continues rather than killing price streaming. The snapshot observer reads `app.state.last_snapshot_at`, writes a snapshot only when `now - last >= 60.0`, and is registered in `lifespan` after `source.start(tickers)` so it closes over the already-started state.

**Primary recommendation:** Split Phase 3 into 3 plans:
1. **03-01: MarketDataSource tick-observer extension** — ABC method, both implementations, 100% existing-test-green before moving on.
2. **03-02: Portfolio service + models + router** — `app/portfolio/` sub-package with all pure functions, Pydantic schemas, router factory, domain exceptions, and their unit tests.
3. **03-03: Lifespan wiring + integration tests** — mount router, register snapshot observer, initialise `app.state.last_snapshot_at`, full HTTP-level and observer-cadence tests.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Portfolio valuation (cash + positions * price) | API / Backend (service.py) | Database (positions, users_profile tables) | Pure-function math over SQLite + in-memory cache; no UI or streaming involved. |
| Trade execution (validation + writes) | API / Backend (service.py) | Database (transaction: users_profile, positions, trades, portfolio_snapshots) | All-or-nothing write sequence lives in one module; owned by the service so Phase 5 chat can call it. |
| Trade validation (cash, shares, ticker, price) | API / Backend (service.py domain exceptions) | API / Backend (routes.py translates to HTTPException) | Business rules live in the service; HTTP framing lives in routes. |
| HTTP request/response framing | API / Backend (routes.py + models.py) | — | Thin adapter between Pydantic v2 schemas and the service. |
| Snapshot cadence (60s piggybacked) | API / Backend (observer closure in lifespan) | Market subsystem (fires the callback) | Observer hook is in market code; the closure reads/writes app.state and DB — belongs in the portfolio layer via lifespan wiring. |
| Tick-observer extension point | Market subsystem (interface.py + simulator.py + massive_client.py) | — | Producer-side primitive; the consumer (snapshot observer) lives outside market. |
| `GET /api/portfolio/history` read | API / Backend (service.py + routes.py) | Database (portfolio_snapshots) | Pure DB read + Pydantic serialisation. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | 2.12.5 | Request/response schemas, `Literal` enums, `Field` constraints, `ConfigDict(extra="forbid")` | [VERIFIED: `uv run python -c "import pydantic; print(pydantic.VERSION)"` reported 2.12.5]. FastAPI's native schema layer; already a transitive dependency. |
| FastAPI | 0.128.7 | `APIRouter` factories, `HTTPException`, automatic Pydantic request parsing | [VERIFIED: `uv run python -c "import fastapi; print(fastapi.__version__)"` reported 0.128.7]. Already used for the SSE router. |
| stdlib `sqlite3` | Python 3.12 | DB writes/reads for positions, trades, snapshots | [VERIFIED: `app/db/connection.py` already uses stdlib sqlite3 with `check_same_thread=False` and `sqlite3.Row`]. Project constraint: no ORM. |
| stdlib `uuid` | Python 3.12 | Primary keys for `trades`, `positions`, `portfolio_snapshots` rows | [VERIFIED: `app/db/seed.py` already uses `uuid.uuid4()` for watchlist row IDs]. Matches existing convention. |
| stdlib `datetime` | Python 3.12 | `datetime.now(UTC).isoformat()` for ISO timestamps | [VERIFIED: `app/db/seed.py:8, 37` uses exactly this pattern]. |
| stdlib `time` | Python 3.12 | `time.time()` / `time.monotonic()` for snapshot-clock math | [VERIFIED: `app/market/cache.py` uses `time.time()`]. Monotonic preferred for interval math; wall-clock preferred for timestamps. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + pytest-asyncio | 8.3+ / 0.24+ | Unit + integration tests | Already configured with `asyncio_mode = "auto"`. |
| httpx | 0.28.1 | In-process client for router tests (`httpx.ASGITransport`) and real-server lifespan tests | [VERIFIED: Phase 1 Plan 01-03 already uses httpx + asgi-lifespan. SSE required a real uvicorn server because ASGITransport buffers streams — NOT a concern for Phase 3 (no streaming endpoints)]. |
| asgi-lifespan | 2.1+ | `LifespanManager` wraps the app so `app.state` is populated before requests | [VERIFIED: `backend/tests/test_lifespan.py:8` already imports `from asgi_lifespan import LifespanManager`]. Reuse for all three Phase 3 plans' integration tests. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Free-function service on `(conn, cache)` | `PortfolioService` class on `app.state` | Rejected by D-02. Class ceremony without state to justify it. |
| Pydantic v2 `BaseModel` responses | `to_dict()` style (mirrors `PriceUpdate`) | Rejected by D-03. Gives no request validation; FastAPI would not auto-serialise. |
| HTTPException inside the service | Domain exceptions translated at the route | Rejected by D-09. Couples the service to FastAPI; Phase 5 chat reuse would need to catch HTTPException in a non-HTTP context. |
| Module-level `_last_snapshot_at` | `app.state.last_snapshot_at` | Rejected by D-06. Violates the Phase 1 D-02 "no module-level singletons" rule; hostile to test isolation. |
| `SELECT MAX(recorded_at)` on every tick | In-memory `app.state.last_snapshot_at` | Rejected by D-06. ~20x more queries than snapshots. |
| Auto-add ticker to watchlist on `/trade` | Reject with `400 unknown_ticker` | Rejected by D-14. Crosses into Phase 4 scope; makes `/trade` do two jobs. |
| FIFO lot tracking | Weighted avg_cost + no sell-side cost basis change | Rejected by D-16. Requires a new `lots` table not in PLAN.md §7. |

**Installation:** No new runtime dependencies. No new dev dependencies.

**Version verification:**
- `pydantic` — `uv run python -c "import pydantic; print(pydantic.VERSION)"` → `2.12.5` [VERIFIED in this session]
- `fastapi` — `uv run python -c "import fastapi; print(fastapi.__version__)"` → `0.128.7` [VERIFIED in this session]
- `httpx` — `uv run python -c "import httpx; print(httpx.__version__)"` → `0.28.1` [VERIFIED in this session]
- Pydantic v2 `ConfigDict(extra="forbid")` + `Literal['buy','sell']` + `Field(gt=0)` — [VERIFIED in this session by executing a sample model and catching `ValidationError` on a stray key].

## Architecture Patterns

### System Architecture Diagram

```
HTTP client
    |
    v
POST /api/portfolio/trade               GET /api/portfolio                GET /api/portfolio/history
    |                                       |                                  |
    v (Pydantic parses TradeRequest,        v                                  v
       422 on bad shape)                    |                                  |
routes.py handler                       routes.py handler                  routes.py handler
    |                                       |                                  |
    | (tries TradeValidationError)          |                                  |
    v                                       v                                  v
service.execute_trade(conn, cache, ...) service.get_portfolio(conn, cache) service.get_history(conn, limit)
    |                                       |                                  |
    | 1. SELECT watchlist -> UnknownTicker  | 1. SELECT cash                   | 1. SELECT snapshots ORDER BY
    | 2. cache.get_price -> PriceUnavail    | 2. SELECT positions              |    recorded_at
    | 3. SELECT cash -> InsufficientCash    | 3. per row: cache.get_price or   | 2. serialise into
    | 4. SELECT position -> InsufShares     |    avg_cost fallback             |    HistoryResponse
    | 5. compute avg_cost / cash delta      | 4. compute_total_value           |
    | 6. UPDATE users_profile (cash)        | 5. serialise into                |
    | 7. UPSERT positions (or DELETE on 0)  |    PortfolioResponse             |
    | 8. INSERT trades                      |                                  |
    | 9. INSERT portfolio_snapshots         |                                  |
    |10. conn.commit()                      |                                  |
    |11. app.state.last_snapshot_at = now   |                                  |
    v                                       v                                  v
sqlite3.Connection (app.state.db)       sqlite3.Connection + PriceCache    sqlite3.Connection
    ^                                       ^
    |                                       |
    |                                       +--- PriceCache (app.state.price_cache)
    |                                               ^
    |                                               | (writes)
    |                                               |
    |                                       SimulatorDataSource._run_loop
    |                                       or MassiveDataSource._poll_once
    |                                               |
    |                                               v (after cache writes)
    |                                       for cb in observers:
    |                                           try: cb()
    |                                           except: logger.exception(...)
    |                                               |
    |                                               v (if now - last >= 60)
    |                                       snapshot_observer(state)
    |                                           |-- compute_total_value(conn, cache)
    +-------------------------------------------|-- INSERT portfolio_snapshots
                                                |-- conn.commit()
                                                +-- state.last_snapshot_at = now
```

### Recommended Project Structure
```
backend/app/portfolio/
├── __init__.py          # Public re-exports (create_portfolio_router, execute_trade,
│                        # get_portfolio, get_history, record_snapshot,
│                        # compute_total_value, make_snapshot_observer,
│                        # TradeValidationError and its four subclasses,
│                        # all response models)
├── routes.py            # create_portfolio_router(db, cache) -> APIRouter
│                        # Handlers catch TradeValidationError, translate to
│                        # HTTPException(400, detail={"error","message"}).
├── service.py           # Free functions on (conn, cache, ...).
│                        # Domain exceptions at top of file.
│                        # make_snapshot_observer(state) -> Callable[[], None].
└── models.py            # Pydantic v2 BaseModel:
                         # - TradeRequest, TradeResponse
                         # - PositionOut, PortfolioResponse
                         # - SnapshotOut, HistoryResponse
                         # - TradeErrorDetail (for documentation only)
```

### Pattern 1: Factory-closure router (BINDING from Phase 1 D-04)
**What:** A function returns a fresh `APIRouter` that closes over its dependencies. No module-level router objects.
**When to use:** Every router in this project — `create_stream_router(cache)` is the template.
**Example:**
```python
# Source: backend/app/market/stream.py:18-53 (existing code)
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        ...

    return router
```
Phase 3 mirrors this: `create_portfolio_router(db: sqlite3.Connection, cache: PriceCache) -> APIRouter` with `prefix="/api/portfolio"`, `tags=["portfolio"]`, three `@router.get`/`@router.post` handlers inside the factory.

### Pattern 2: Pure-function service on `(conn, cache, ...)` (BINDING from D-02)
**What:** Service functions accept the connection and cache as arguments. No class state, no FastAPI imports.
**When to use:** All DB+cache business logic in Phase 3 (and Phase 5 chat reuse).
**Example:**
```python
# Source: backend/app/db/seed.py:26-59 (existing code template)
def seed_defaults(conn: sqlite3.Connection) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
        "VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )
    ...
    conn.commit()
```
Phase 3 `execute_trade(conn, cache, ticker, side, quantity, user_id="default")` follows the same shape.

### Pattern 3: Pydantic v2 request schema with strict config (from D-03 + discretion)
**What:** `BaseModel` with `model_config = ConfigDict(extra="forbid")` and field-level validation via `Field`/`Literal`.
**When to use:** All request bodies. Stray keys like `{"Ticker": "AAPL"}` should 422 at the edge.
**Example:**
```python
# Source: Pydantic v2 docs (https://docs.pydantic.dev/latest/concepts/models/) [CITED]
# [VERIFIED: executed in this session against pydantic 2.12.5]
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class TradeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
```
FastAPI automatically validates `TradeRequest` against the request JSON; `side="hold"` or missing `quantity` → 422 before the handler runs, satisfying D-11.

### Pattern 4: `model_dump()` for serialisation (Pydantic v2)
**What:** Pydantic v2 replaces `dict()` with `model_dump()` and `parse_obj()` with `model_validate()`. `Config` inner class replaced by `model_config = ConfigDict(...)`.
**When to use:** Everywhere in Phase 3. Never use the v1 names.
**Example:**
```python
# Source: Pydantic v2 migration guide [CITED: docs.pydantic.dev/latest/migration/]
response = TradeResponse(...)
response.model_dump()            # v2: dict
response.model_dump_json()       # v2: JSON str
TradeResponse.model_validate(d)  # v2: from dict
```

### Pattern 5: Tick-observer callback list on the source (D-04)
**What:** `MarketDataSource.register_tick_observer(callback: Callable[[], None]) -> None`. Implementations hold a `list[Callable[[], None]]` of registered callbacks, initialised in `__init__`. Both loops fire `for cb in self._observers: try: cb() except Exception: logger.exception(...)` after cache writes.
**When to use:** This phase only. Not part of MARKET-01..06.
**Example:**
```python
# Proposed shape (to be implemented in 03-01)
class MarketDataSource(ABC):
    @abstractmethod
    def register_tick_observer(self, callback: Callable[[], None]) -> None:
        """Register a zero-arg callable invoked after each tick/poll.

        Callbacks must be fast and non-raising. The source wraps each
        invocation in try/except + logger.exception so a broken observer
        does not kill the tick loop.
        """
```
Rationale for zero-arg (`Callable[[], None]`): the snapshot observer needs the full cache + DB + app.state — passing `(ticker, price)` would fire N times per tick and force the observer to coalesce. Zero-arg fires once per tick, the observer reads the cache snapshot it needs. [ASSUMED — a justified architectural choice given the use case; planner may revise if a future observer needs per-ticker data.]

### Anti-Patterns to Avoid
- **Opening a per-request sqlite3 connection.** Phase 2 D-01 explicitly pinned one long-lived connection on `app.state.db`.
- **Using `Decimal` for trade math.** Rejected by discretion — floats are fine for simulated $10k; don't add ceremony.
- **Passing arguments to the observer callback.** Zero-arg keeps the producer side decoupled from any specific consumer.
- **Catching exceptions inside `execute_trade` around DB writes.** Validate first, write second. If a write fails after validation (it shouldn't for a well-formed request on a healthy DB), it fails loud — no silent rollback + success response.
- **Using f-strings in log calls.** `%`-style only. [VERIFIED: project convention in `app/market/simulator.py:230` — `logger.info("Simulator started with %d tickers", n)`].
- **Module-level router objects.** `create_stream_router` explicitly builds a fresh `APIRouter` per call to avoid duplicate routes across test apps — Phase 3 routers must do the same.
- **Using Pydantic v1 idioms (`dict()`, `Config` inner class, `parse_obj`, `Optional[X]`).** All deprecated in Pydantic v2.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Request body validation | Hand-rolled `if not body.get("ticker"): raise HTTPException(...)` chains | Pydantic v2 `BaseModel` with `Literal`, `Field(gt=0)`, `ConfigDict(extra="forbid")` | FastAPI auto-validates, produces RFC-7807-style 422, auto-generates OpenAPI docs. |
| ISO timestamp formatting | Custom `strftime` | `datetime.now(UTC).isoformat()` | Existing convention in `app/db/seed.py`. Lexicographically sortable and UTC-explicit. |
| Row-object JSON serialisation | Dict comprehensions over `sqlite3.Row` objects | Pydantic response model constructor + `response_model=` on the route | FastAPI handles JSON encoding, 200 status, validates the response matches the schema. |
| UUIDs for primary keys | `str(uuid.uuid4())` scattered across call sites | Consistent `str(uuid.uuid4())` calls at the point of INSERT | Already the project convention in `app/db/seed.py:54`. |
| Transaction control | Custom context manager | Stdlib sqlite3's default implicit-transaction-on-write mode with explicit `conn.commit()` at the end of each write path | Phase 2 D-03 picked this; Phase 3 stays consistent. `BEGIN IMMEDIATE` is available under discretion if write-lock-up-front is preferred. |
| Error response schema | Bare `raise HTTPException(400, detail="Insufficient cash")` (string detail) | `HTTPException(400, detail={"error": "insufficient_cash", "message": "..."})` (dict detail) | D-10 specifies dict detail so the frontend and Phase 5 LLM chat can switch on a machine-readable `error` code without string matching. |

**Key insight:** Phase 3 is gluing well-known building blocks. The service is a hundred lines of SQLite + float math; the routes are thin Pydantic adapters; the observer is a two-line closure. The only novel primitive is `register_tick_observer` on the market source — and that's deliberately tiny (one method, one list attribute, one try/except).

## Runtime State Inventory

_Skipped — Phase 3 is a greenfield additive phase (new sub-package + scoped interface extension). No rename, refactor, or migration._

## Common Pitfalls

### Pitfall 1: Float equality for zero-quantity position deletion
**What goes wrong:** After selling the full position, `new_qty` is a float residual like `-1.1e-16` or `+5e-17` instead of exactly `0.0`.
**Why it happens:** Subtracting two IEEE 754 doubles rarely gives exactly zero even when the mathematical result is zero.
**How to avoid:** Use `abs(new_qty) < 1e-9` (D-15). Do NOT use `new_qty == 0.0` or `new_qty <= 0` — the former misses near-zero residuals and the latter silently accepts negative quantities from a logic bug (defensive-programming-lite; better to assert validated-before-write math).
**Warning signs:** A "sold everything" test asserting `positions` has 0 rows after a full-sell fails intermittently.

### Pitfall 2: `check_same_thread=False` and the observer callback
**What goes wrong:** `MassiveDataSource._poll_once` runs the synchronous Polygon SDK via `asyncio.to_thread`, which runs on a worker thread. If observer callbacks are fired on the same thread, the snapshot observer writes to SQLite from a non-event-loop thread.
**Why it happens:** The `_poll_once` body runs in the event loop (only `_fetch_snapshots` is offloaded to a thread), so observers fire on the event loop thread in Massive [VERIFIED: `backend/app/market/massive_client.py:89-116` — `_poll_once` is `async def` and `await`s the thread-offload; everything after the `await` is back on the loop]. In `SimulatorDataSource._run_loop`, observers fire on the event loop thread [VERIFIED: `backend/app/market/simulator.py:260-270`]. Therefore SQLite writes from the observer are always on the event loop thread.
**How to avoid:** Fire observers after cache writes but before `await asyncio.sleep(...)` — they are already on the event loop thread in both implementations. Do NOT move observer invocation inside `asyncio.to_thread`. Document this contract in the ABC docstring.
**Warning signs:** `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread` would be the symptom; `check_same_thread=False` on the connection suppresses it, but good to understand why it's safe without relying on the flag.

### Pitfall 3: `cache.get_price` is `None` between `source.start()` and the first tick
**What goes wrong:** A client posts a trade in the tiny window between startup and the first simulator tick. `cache.get_price(ticker)` returns `None`.
**Why it happens:** `SimulatorDataSource.start` already seeds the cache immediately — [VERIFIED: `simulator.py:224-228`] — so this window is zero for simulator-mode tickers. `MassiveDataSource.start` also does an immediate first poll [VERIFIED: `massive_client.py:45-46`] before returning. Therefore in practice the window is only the first few ms of a poll cycle AND only for tickers not yet in the initial set.
**How to avoid:** D-13 explicitly rejects with `400 price_unavailable` and no fallback. Test this explicitly (`test_trade_rejects_when_cache_empty`) by calling `cache.remove(ticker)` before posting the trade, or by constructing a PriceCache with no prior writes.
**Warning signs:** A flaky "first-trade-at-startup" test that occasionally 200s and occasionally 400s. That's the race window — write a deterministic test that doesn't depend on it.

### Pitfall 4: Pydantic v2 `ConfigDict(extra="forbid")` and FastAPI request-body parsing
**What goes wrong:** A client posts `{"ticker": "AAPL", "side": "buy", "quantity": 1, "note": "for grandma"}`. With `extra="forbid"` on `TradeRequest`, FastAPI returns 422 with a `extra_forbidden` error.
**Why it happens:** That's the intent — strict inputs. Keep in mind the same rule does NOT apply by default to response models, so `PortfolioResponse` can evolve additively without breaking clients that send stale payloads back.
**How to avoid:** Only set `extra="forbid"` on request models, not on response models. Write a test (`test_trade_rejects_extra_keys_with_422`) that posts a junk key and asserts 422 + `detail[0]["type"] == "extra_forbidden"` so a future config change that loosens it is caught.
**Warning signs:** A lenient config drift (e.g., someone copy-pastes a response model config onto a request model) would silently accept stray keys.

### Pitfall 5: `app.state.last_snapshot_at = 0.0` at startup and the first tick
**What goes wrong:** At first tick, `now - 0.0 = now` (a huge number) so `now - last >= 60.0` is trivially true — the observer writes a snapshot on the very first tick.
**Why it happens:** That's actually the desired behaviour — a boot-time snapshot anchors the P&L series at t=0. But if you don't want a boot-snapshot, initialise to `time.monotonic()` (or `time.time()`) at lifespan entry instead.
**How to avoid:** Use `0.0` and treat the first-tick snapshot as a feature (a history that starts with an initial total-value snapshot). Document it in the observer docstring.
**Warning signs:** A test asserting "no snapshot before 60s" fails on the first tick — fix the assertion, not the observer.

### Pitfall 6: `time.time()` vs `time.monotonic()` for the snapshot clock
**What goes wrong:** If a machine's wall clock is adjusted (NTP step, manual change) between ticks, `time.time()` can go backwards and break `now - last >= 60.0` math.
**Why it happens:** `time.time()` is wall-clock; `time.monotonic()` is never adjusted.
**How to avoid:** Use `time.monotonic()` for the `last_snapshot_at` clock. Use `datetime.now(UTC).isoformat()` (separately) for the `recorded_at` column value — those are two different things. Do NOT reuse a `time.time()` or `time.monotonic()` value in an ISO column.
**Warning signs:** Flaky CI on a VM with clock skew.

### Pitfall 7: Pydantic v1 idiom leakage
**What goes wrong:** A planner/executor writes `response.dict()` or uses `class Config: extra = "forbid"` — both removed in Pydantic v2.
**How to avoid:** Always use `model_dump()`, `model_dump_json()`, `model_validate()`, `model_validate_json()`, and `model_config = ConfigDict(...)`. Ruff doesn't catch these — add a test that constructs a response model and asserts the v2 method names work.
**Warning signs:** `AttributeError: 'TradeResponse' object has no attribute 'dict'`.

### Pitfall 8: Transaction interleaving under the manual-commit default
**What goes wrong:** Stdlib sqlite3's default `isolation_level` is `""` (deferred). The first INSERT/UPDATE opens an implicit transaction; a second INSERT without an intervening commit extends the same transaction; `conn.commit()` closes it. If Python's sqlite3 driver is asked to `BEGIN` while one is already open, it raises `sqlite3.OperationalError: cannot start a transaction within a transaction`.
**How to avoid:** Don't call `conn.execute("BEGIN")` — rely on the implicit transaction. Call `conn.commit()` exactly once at the end of the write sequence. If the planner opts for explicit `BEGIN IMMEDIATE` (discretion), call it at the very start of `execute_trade` before any reads, and never nest. [VERIFIED: this is the idiom already used in `app/db/seed.py` — `conn.execute(...)` multiple times, `conn.commit()` once at the bottom.]
**Warning signs:** `OperationalError: cannot start a transaction within a transaction` in a test.

### Pitfall 9: httpx `ASGITransport` buffering (not applicable here, but noted)
**What goes wrong:** Phase 1 Plan 01-03 hit this for SSE — `httpx.ASGITransport` buffers the full ASGI response and cannot drain infinite SSE generators. That's why Phase 1 spun up a real in-process uvicorn server for SSE tests.
**How to avoid:** Phase 3 has no streaming endpoints — all three routes return bounded JSON. `httpx.ASGITransport` + `asgi-lifespan.LifespanManager` is the right fit. Do NOT add a uvicorn harness for Phase 3. [VERIFIED: `.planning/phases/01-app-shell-config/` SUMMARY notes confirm D-05 for SSE-only; routes returning bounded responses work fine under ASGITransport.]

### Pitfall 10: Watchlist check by DB vs by cache
**What goes wrong:** The error code `unknown_ticker` says "add it to your watchlist first" — but a naive check of `cache.get_price(ticker) is None` collapses watchlist-miss and price-unavailable into one code.
**How to avoid:** Check the `watchlist` table first (returns `unknown_ticker` if not found); only THEN check the cache (returns `price_unavailable` if watchlist-present-but-no-price-yet). This matches D-14 and gives the frontend two distinct error codes to route on.
**Warning signs:** A test that adds a ticker to the watchlist but posts a trade before the first tick — should return `price_unavailable`, not `unknown_ticker`.

## Code Examples

### Pydantic v2 schema with strict input
```python
# Source: Pydantic v2 docs (https://docs.pydantic.dev/latest/concepts/models/) [VERIFIED in session]
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TradeRequest(BaseModel):
    """Request body for POST /api/portfolio/trade."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)


class TradeResponse(BaseModel):
    """Success response for POST /api/portfolio/trade."""

    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    cash_balance: float
    position_quantity: float  # post-trade quantity; 0.0 if fully sold
    position_avg_cost: float  # post-trade avg cost; equals price on first buy
    executed_at: str  # ISO UTC


class PositionOut(BaseModel):
    """One row in PortfolioResponse.positions."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float       # falls back to avg_cost if cache miss
    unrealized_pnl: float      # (current_price - avg_cost) * quantity
    change_percent: float      # (current_price - avg_cost) / avg_cost * 100


class PortfolioResponse(BaseModel):
    """Response for GET /api/portfolio."""

    cash_balance: float
    total_value: float          # cash + sum(qty * price_or_avg_cost)
    positions: list[PositionOut]


class SnapshotOut(BaseModel):
    """One snapshot in HistoryResponse.snapshots."""

    total_value: float
    recorded_at: str  # ISO UTC


class HistoryResponse(BaseModel):
    """Response for GET /api/portfolio/history."""

    snapshots: list[SnapshotOut]
```

### Domain exceptions
```python
# Source: proposed — to be created in backend/app/portfolio/service.py
from __future__ import annotations


class TradeValidationError(Exception):
    """Base for business-rule rejections. Mapped to 400 at the route boundary."""

    code: str = "trade_validation_error"


class InsufficientCash(TradeValidationError):
    code = "insufficient_cash"


class InsufficientShares(TradeValidationError):
    code = "insufficient_shares"


class UnknownTicker(TradeValidationError):
    code = "unknown_ticker"


class PriceUnavailable(TradeValidationError):
    code = "price_unavailable"
```

### Service function skeleton
```python
# Source: proposed — matches the pattern in backend/app/db/seed.py
import logging
import sqlite3
import time
import uuid
from datetime import UTC, datetime
from typing import Literal

from app.market import PriceCache

from .models import TradeResponse

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"


def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResponse:
    """Execute a market order. Validate-then-write, single transaction, commit once.

    Raises TradeValidationError subclasses on any precondition failure. On
    success, writes cash_balance, positions (or DELETEs if zeroed), trades,
    and portfolio_snapshots atomically and commits. Does NOT touch
    app.state.last_snapshot_at — the caller (route handler) does that after
    commit so the service stays FastAPI-agnostic.
    """
    ticker = ticker.upper().strip()

    # 1. Watchlist membership -> UnknownTicker (D-14)
    row = conn.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    if row is None:
        raise UnknownTicker(f"{ticker} is not on the watchlist")

    # 2. Cached price -> PriceUnavailable (D-13)
    price = cache.get_price(ticker)
    if price is None:
        raise PriceUnavailable(f"No cached price for {ticker}")

    # 3. Read cash + existing position
    cash_row = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ).fetchone()
    cash_balance = float(cash_row["cash_balance"])

    pos_row = conn.execute(
        "SELECT id, quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    ).fetchone()
    old_qty = float(pos_row["quantity"]) if pos_row else 0.0
    old_avg = float(pos_row["avg_cost"]) if pos_row else 0.0

    # 4. Validation math
    gross = quantity * price
    if side == "buy":
        if gross > cash_balance:
            raise InsufficientCash(
                f"Need ${gross:.2f}, have ${cash_balance:.2f}"
            )
        new_qty = old_qty + quantity
        new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty  # D-16
        new_cash = cash_balance - gross
    else:  # sell
        if quantity > old_qty + 1e-9:  # D-15 epsilon, applied to validation too
            raise InsufficientShares(
                f"Requested {quantity}, held {old_qty}"
            )
        new_qty = old_qty - quantity
        new_avg = old_avg  # D-16
        new_cash = cash_balance + gross

    # 5. Write (all-or-nothing; implicit transaction; commit once) — D-12
    now_iso = datetime.now(UTC).isoformat()
    conn.execute(
        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
        (new_cash, user_id),
    )

    if abs(new_qty) < 1e-9:  # D-15 zero-position delete
        conn.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        )
        pos_qty_out, pos_avg_out = 0.0, 0.0
    elif pos_row is None:
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, ticker, new_qty, new_avg, now_iso),
        )
        pos_qty_out, pos_avg_out = new_qty, new_avg
    else:
        conn.execute(
            "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? "
            "WHERE user_id = ? AND ticker = ?",
            (new_qty, new_avg, now_iso, user_id, ticker),
        )
        pos_qty_out, pos_avg_out = new_qty, new_avg

    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, ticker, side, quantity, price, now_iso),
    )

    total_value = _compute_total_value_with(conn, cache, new_cash, user_id)
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
        "VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, total_value, now_iso),
    )

    conn.commit()
    logger.info(
        "Trade executed: %s %s x %.4f @ %.2f (cash=%.2f)",
        ticker, side, quantity, price, new_cash,
    )

    return TradeResponse(
        ticker=ticker,
        side=side,
        quantity=quantity,
        price=price,
        cash_balance=new_cash,
        position_quantity=pos_qty_out,
        position_avg_cost=pos_avg_out,
        executed_at=now_iso,
    )
```

### Snapshot observer factory
```python
# Source: proposed — matches lifespan closure pattern from 01-CONTEXT.md D-04
import time
import uuid
from datetime import UTC, datetime
from typing import Callable


def make_snapshot_observer(state) -> Callable[[], None]:
    """Build a zero-arg tick observer that writes a snapshot every 60s.

    Closes over `state` (FastAPI app.state) which carries:
      - state.db:                 sqlite3.Connection (Phase 2 D-01)
      - state.price_cache:        PriceCache (Phase 1 D-02)
      - state.last_snapshot_at:   float; initialised to 0.0 in lifespan (D-06)

    Uses time.monotonic() for the clock (immune to wall-clock adjustments).
    Writes datetime.now(UTC).isoformat() into `recorded_at`.
    """
    def observer() -> None:
        now = time.monotonic()
        if now - state.last_snapshot_at < 60.0:
            return
        total_value = compute_total_value(state.db, state.price_cache)
        state.db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), "default", total_value, datetime.now(UTC).isoformat()),
        )
        state.db.commit()
        state.last_snapshot_at = now

    return observer
```

### Router factory
```python
# Source: proposed — mirrors create_stream_router (backend/app/market/stream.py:18-53)
import sqlite3
from fastapi import APIRouter, HTTPException

from app.market import PriceCache

from . import service
from .models import (
    HistoryResponse,
    PortfolioResponse,
    TradeRequest,
    TradeResponse,
)


def create_portfolio_router(
    db: sqlite3.Connection,
    cache: PriceCache,
) -> APIRouter:
    """Factory-closure router for portfolio endpoints.

    A fresh APIRouter per call avoids duplicate routes across test-spawned
    apps (same rationale as create_stream_router).
    """
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("", response_model=PortfolioResponse)
    async def get_portfolio() -> PortfolioResponse:
        return service.get_portfolio(db, cache)

    @router.post("/trade", response_model=TradeResponse)
    async def post_trade(req: TradeRequest) -> TradeResponse:
        try:
            return service.execute_trade(
                db, cache, req.ticker, req.side, req.quantity,
            )
        except service.TradeValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail={"error": exc.code, "message": str(exc)},
            )

    @router.get("/history", response_model=HistoryResponse)
    async def get_history(limit: int | None = None) -> HistoryResponse:
        return service.get_history(db, limit=limit)

    return router
```

### Lifespan diff (surgical additions)
```python
# Source: proposed — diff against backend/app/lifespan.py (lines shown against current file)
# Imports (add):
from .portfolio import create_portfolio_router, make_snapshot_observer

# Inside lifespan(), AFTER `await source.start(tickers)` (line 47 in current file):
    app.state.db = conn
    app.state.price_cache = cache
    app.state.market_source = source
    app.state.last_snapshot_at = 0.0                                   # D-06
    source.register_tick_observer(make_snapshot_observer(app.state))   # D-05
    app.include_router(create_stream_router(cache))
    app.include_router(create_portfolio_router(conn, cache))           # NEW
```
Note: the router factory receives `conn` and `cache` directly; the observer factory receives `app.state` (needs mutable `last_snapshot_at`). Both are closure-scoped — no module-level singletons.

### Trade-time clock reset (D-07) — route-level, not service-level
```python
# Source: proposed — in routes.py, AFTER the service returns successfully
# Keeps the service FastAPI-agnostic and app.state-agnostic.
@router.post("/trade", response_model=TradeResponse)
async def post_trade(request: Request, req: TradeRequest) -> TradeResponse:
    try:
        response = service.execute_trade(
            db, cache, req.ticker, req.side, req.quantity,
        )
    except service.TradeValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": exc.code, "message": str(exc)},
        )
    # D-07: trade-time snapshot resets the 60s clock so we don't double-snapshot.
    request.app.state.last_snapshot_at = time.monotonic()
    return response
```
Alternative: pass a `state` parameter to the service and let it update `last_snapshot_at` (couples the service to FastAPI-flavoured state). Rejected — route-level reset keeps the seam clean.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `class Config: extra = "forbid"` inner class | `model_config = ConfigDict(extra="forbid")` module attribute | Pydantic 2.0 (2023) | [CITED: docs.pydantic.dev/latest/migration/] |
| `response.dict()` | `response.model_dump()` | Pydantic 2.0 | Same migration. |
| `Model.parse_obj(d)` | `Model.model_validate(d)` | Pydantic 2.0 | Same migration. |
| `Optional[X]` / `Union[X, Y]` | `X \| None` / `X \| Y` | Python 3.10 PEP 604 | Matches the existing project convention (e.g., `backend/app/market/cache.py:56`). |
| FastAPI `Depends(get_db)` | `APIRouter` factory with closure over `conn, cache` | Established Phase 1 D-04 | Not a library change — a project convention. |

**Deprecated / outdated:**
- `pydantic.BaseSettings` for env config — moved to `pydantic-settings` in v2; Phase 1 used `python-dotenv` instead (out of scope here, noted for consistency).
- Pytest-style module-level `@pytest.mark.asyncio` — the project uses `asyncio_mode = "auto"` in `pyproject.toml` so no decorators are needed on async test functions [VERIFIED: `backend/pyproject.toml:38`].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Observer callback signature is zero-arg `Callable[[], None]` | Pattern 5 / Code Examples | Low — easy to refactor to `(ticker, price)` later if a future observer needs per-ticker data. Only the snapshot observer exists in Phase 3; it needs the whole cache anyway. |
| A2 | Boot-time initial snapshot (because `last_snapshot_at = 0.0`) is desired | Pitfall 5 | Low — anchors the P&L chart at t=0 with the initial $10,000 total_value. If the planner/user wants no boot snapshot, initialise `last_snapshot_at = time.monotonic()` at lifespan entry. |
| A3 | Trade-time reset of `last_snapshot_at` happens in the route (not the service) so the service stays FastAPI-agnostic | Code Examples / D-07 | Low — an alternative is to have `execute_trade` accept a `state` or a `on_success` callback argument. Route-level reset is cleaner given D-02. |
| A4 | `compute_total_value` is a single shared helper used by both `get_portfolio` and the snapshot observer | Discretion (snapshot fallback) | Low — the "fallback to avg_cost when cache miss" rule must be identical in both call paths. A single helper is the obvious way to guarantee that. |
| A5 | Phase 3 adds no new dependencies (Pydantic, FastAPI, httpx, asgi-lifespan all already present) | Standard Stack | Low — verified in this session. |
| A6 | `position_quantity` and `position_avg_cost` are returned on the TradeResponse as `0.0` when a sell zeroed the position | Code Examples (TradeResponse) | Low — keeps the response shape uniform; frontend can branch on `position_quantity == 0.0` or re-fetch `/api/portfolio`. Planner may rename / omit these fields under discretion. |

## Open Questions

1. **Is the Phase 3 service responsible for resetting `app.state.last_snapshot_at` after its post-trade snapshot, or does the route do it?**
   - What we know: D-07 says the reset MUST happen; D-02 says the service is FastAPI-agnostic.
   - What's unclear: how the reset is plumbed without coupling `execute_trade` to FastAPI state.
   - Recommendation: route-level reset, as shown in the Code Examples. Single line of coupling, kept at the HTTP boundary. Plans should call this out explicitly.

2. **Should `GET /api/portfolio/history` accept a `limit` query param in v1?**
   - What we know: CONTEXT "Claude's Discretion" says optional, default None, cap ~10_000 if added.
   - Recommendation: add `limit: int | None = Query(default=None, ge=1, le=10_000)`. Cheap, future-proof, aligns with the P&L chart frontend needing a bounded query in Phase 8.

3. **Position ordering in `GET /api/portfolio`?**
   - What we know: any stable order is fine (discretion).
   - Recommendation: `ORDER BY ticker ASC`. Deterministic for tests; heatmap and table will re-sort anyway.

4. **Explicit `BEGIN IMMEDIATE` vs implicit transaction?**
   - What we know: stdlib sqlite3 default works; discretion to choose.
   - Recommendation: implicit. Simpler; single-user workload; consistent with `seed.py`. Flag for future revisit if Phase 5 chat multi-trade atomicity ever comes up.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | all Phase 3 code | ✓ | 3.12 | — |
| `uv` | `uv run pytest`, `uv add` | ✓ | in project | — |
| FastAPI | routes, HTTPException, APIRouter | ✓ | 0.128.7 | — |
| Pydantic | models.py | ✓ | 2.12.5 | — |
| stdlib `sqlite3` | service.py DB writes | ✓ | Python 3.12 | — |
| stdlib `uuid`, `datetime`, `time`, `logging` | service.py, lifespan | ✓ | Python 3.12 | — |
| pytest + pytest-asyncio | tests | ✓ | 8.3+/0.24+ | — |
| httpx + asgi-lifespan | integration tests | ✓ | 0.28.1 / 2.1+ | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3+ with pytest-asyncio 0.24+ (asyncio_mode = "auto") |
| Config file | `backend/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd backend && uv run --extra dev pytest tests/portfolio -x` |
| Full suite command | `cd backend && uv run --extra dev pytest` |
| Phase gate | Full suite green before `/gsd-verify-work` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-01 | GET /api/portfolio returns cash + total_value + positions[] with current_price fallback to avg_cost | integration (HTTP) | `uv run --extra dev pytest tests/portfolio/test_routes_portfolio.py -x` | ❌ Wave 0 |
| PORT-01 | PortfolioResponse total_value equals cash + sum(qty * current_price_or_avg_cost) | unit | `uv run --extra dev pytest tests/portfolio/test_service_portfolio.py::TestComputeTotalValue -x` | ❌ Wave 0 |
| PORT-02 | POST /api/portfolio/trade buy debits cash, upserts position, appends trades row | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestBuy -x` | ❌ Wave 0 |
| PORT-02 | POST /api/portfolio/trade sell credits cash, decrements position (or DELETEs on zero), appends trades row | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestSell -x` | ❌ Wave 0 |
| PORT-02 | execute_trade weighted avg_cost on add-to-existing buy (D-16) | unit | `uv run --extra dev pytest tests/portfolio/test_service_buy.py::test_weighted_avg_cost -x` | ❌ Wave 0 |
| PORT-02 | Fractional quantity supported | unit + integration | `uv run --extra dev pytest tests/portfolio/test_service_buy.py::test_fractional tests/portfolio/test_routes_trade.py::test_fractional -x` | ❌ Wave 0 |
| PORT-03 | Buy rejected with 400 insufficient_cash; DB unchanged | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestErrors::test_insufficient_cash -x` | ❌ Wave 0 |
| PORT-03 | Sell rejected with 400 insufficient_shares; DB unchanged | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestErrors::test_insufficient_shares -x` | ❌ Wave 0 |
| PORT-03 | Trade on unwatched ticker rejected with 400 unknown_ticker | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestErrors::test_unknown_ticker -x` | ❌ Wave 0 |
| PORT-03 | Trade when cache has no price rejected with 400 price_unavailable | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestErrors::test_price_unavailable -x` | ❌ Wave 0 |
| PORT-03 | Malformed body (bad side, negative qty, extra key) returns 422 | integration | `uv run --extra dev pytest tests/portfolio/test_routes_trade.py::TestSchema -x` | ❌ Wave 0 |
| PORT-04 | GET /api/portfolio/history returns time-ordered snapshots | integration | `uv run --extra dev pytest tests/portfolio/test_routes_history.py -x` | ❌ Wave 0 |
| PORT-05 | Trade writes a snapshot immediately | unit + integration | `uv run --extra dev pytest tests/portfolio/test_service_buy.py::test_writes_snapshot tests/portfolio/test_routes_trade.py::test_writes_snapshot -x` | ❌ Wave 0 |
| PORT-05 | Snapshot observer writes when now - last >= 60s | unit (with fake clock) | `uv run --extra dev pytest tests/portfolio/test_snapshot_observer.py::test_60s_threshold -x` | ❌ Wave 0 |
| PORT-05 | Snapshot observer is a no-op when now - last < 60s | unit | `uv run --extra dev pytest tests/portfolio/test_snapshot_observer.py::test_noop_under_threshold -x` | ❌ Wave 0 |
| PORT-05 | Trade resets the 60s clock (app.state.last_snapshot_at) | integration | `uv run --extra dev pytest tests/portfolio/test_snapshot_observer.py::test_trade_resets_clock -x` | ❌ Wave 0 |
| PORT-05 | Bad observer does not kill the tick loop | unit (with a raising observer) | `uv run --extra dev pytest tests/market/test_observer.py::test_observer_exception_isolation -x` | ❌ Wave 0 |
| D-04 | register_tick_observer exists on ABC + both implementations | unit | `uv run --extra dev pytest tests/market/test_observer.py::TestABC tests/market/test_observer.py::TestSimulator tests/market/test_observer.py::TestMassive -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run --extra dev pytest tests/portfolio tests/market/test_observer.py -x`
- **Per wave merge:** `uv run --extra dev pytest -x`
- **Phase gate:** Full suite green + the existing Phase 1/2 suites still pass.

### Wave 0 Gaps
- [ ] `backend/tests/portfolio/__init__.py` — package marker (matches `tests/db/__init__.py`).
- [ ] `backend/tests/portfolio/conftest.py` — `warmed_cache` fixture that calls `cache.update(ticker, price)` for each seed ticker; builds on the existing `db_path` fixture.
- [ ] `backend/tests/portfolio/test_service_buy.py` — weighted avg, cash debit, new vs existing position, fractional, snapshot-on-trade.
- [ ] `backend/tests/portfolio/test_service_sell.py` — partial sell, full sell (DELETE row), avg_cost unchanged, snapshot-on-trade.
- [ ] `backend/tests/portfolio/test_service_validation.py` — `UnknownTicker`, `PriceUnavailable`, `InsufficientCash`, `InsufficientShares`; assert zero DB writes on each.
- [ ] `backend/tests/portfolio/test_service_portfolio.py` — `get_portfolio` shape, cold-start P&L=0 fallback, `compute_total_value` helper.
- [ ] `backend/tests/portfolio/test_service_history.py` — empty history, ordering (ASC), `limit` param if added.
- [ ] `backend/tests/portfolio/test_routes_portfolio.py` — 200 OK + PortfolioResponse shape via `httpx.ASGITransport` + `LifespanManager`.
- [ ] `backend/tests/portfolio/test_routes_trade.py` — 200 on success; 400 on each error code with `detail.error` matching the enum; 422 on schema violations; response headers.
- [ ] `backend/tests/portfolio/test_routes_history.py` — 200 + HistoryResponse shape; empty history case.
- [ ] `backend/tests/portfolio/test_snapshot_observer.py` — 60s threshold (monkeypatched `time.monotonic`); no-op when under threshold; trade resets clock; observer exception is isolated (raising observer + one non-raising observer, non-raising still fires).
- [ ] `backend/tests/market/test_observer.py` — ABC requires `register_tick_observer`; `SimulatorDataSource` fires observers after tick; `MassiveDataSource` fires observers after poll; exception in one observer does not prevent the next observer from firing; exception does not kill the loop (next tick still runs). Parametrise across both source types where possible to mirror existing `test_factory.py` / `test_simulator_source.py` style.
- [ ] `backend/tests/test_lifespan.py` — extend with three new assertions: `app.state.last_snapshot_at == 0.0` on startup, `/api/portfolio` route is registered, and the portfolio router is mounted alongside the SSE router.
- [ ] Framework install: **none** — pytest, httpx, asgi-lifespan, pytest-asyncio all already present.

## Security Domain

_Phase 3 is an HTTP layer over stdlib sqlite3 on a single-user, single-container localhost app with no authentication and no external inputs beyond a trusted Pydantic-validated JSON body. Applicable ASVS controls are narrow._

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user; auth is deferred to v2 AUTH-01 per REQUIREMENTS.md. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | no | `user_id="default"` hardcoded; multi-user is v2. |
| V5 Input Validation | **yes** | Pydantic v2 `BaseModel` with `ConfigDict(extra="forbid")`, `Literal["buy","sell"]` side, `Field(gt=0, min_length=1, max_length=10)`. 422 on shape violations; 400 on business-rule violations. |
| V6 Cryptography | no | No crypto. |

### Known Threat Patterns for FastAPI + SQLite

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via `ticker` parameter | Tampering | [VERIFIED: all SQL uses `?` parameterised queries in existing `app/db/seed.py`; Phase 3 follows the same style — no string concatenation, no f-string SQL]. |
| Oversized request bodies | DoS | FastAPI uses Starlette's default body size limits; Pydantic `Field(max_length=10)` on ticker caps the one free-form field. No file uploads. |
| Float-precision exploits (quantities like `1e308`) | Tampering / logic | `Field(gt=0)` rejects zero/negative. Extremely large quantities fail the cash check naturally. No `Decimal` needed; see Pitfall 1 for epsilon comparison. |
| Rate-limiting trade endpoint | Availability | Out of scope — single-user localhost. Not called out as a Phase 3 concern in CONTEXT.md. |

## Dependencies to Add

**None.** All libraries required for Phase 3 are already declared in `backend/pyproject.toml` and resolved in `backend/uv.lock`:

- **Runtime:** `fastapi>=0.115.0`, `uvicorn[standard]>=0.32.0`, `python-dotenv>=1.2.1`, stdlib modules. Pydantic is a transitive dep of FastAPI [VERIFIED: `import pydantic` succeeds; reports 2.12.5].
- **Dev (tests):** `pytest>=8.3.0`, `pytest-asyncio>=0.24.0`, `pytest-cov>=5.0.0`, `httpx>=0.28.1`, `asgi-lifespan>=2.1.0`.

No `uv add` calls. No `pyproject.toml` diff.

## Project Constraints (from CLAUDE.md)

These constraints from `CLAUDE.md` (global + project) are binding on every Phase 3 plan and task. Planner MUST verify each plan's tasks do not violate them.

| Constraint | Source | Applies to Phase 3 |
|------------|--------|--------------------|
| No over-engineering, no defensive programming | global + project | No `try/except` wrapping DB writes in `execute_trade`. Validate first, write second, commit once. Exception managers only at loop boundaries (observer invocation — D-08). |
| Identify root cause before fixing issues | global | Already honored by the Phase 2 commit history (e.g., f47d15d, b655846). Applies during test failures — reproduce, then fix. |
| Use `uv run xxx` never `python3 xxx`; `uv add xxx` never `pip install xxx` | global | Phase 3 adds no deps. All test invocations use `uv run --extra dev pytest ...`. |
| Short modules / short functions / named clearly | project | Each portfolio module stays < ~150 lines. `execute_trade` is the largest function — split if it exceeds ~80 lines by extracting `_compute_buy_math`, `_compute_sell_math`, `_apply_position_write` helpers. |
| Clear docstrings, sparing inline comments | project | Module-level one-liner; class/function docstrings stating behavior; inline comments only for math derivations. |
| Never use emojis in code, print statements, or logging | global + project | BINDING. Ruff does not catch this — plan-checker or code review must verify. |
| Latest library APIs (Pydantic v2, FastAPI 0.115+, pytest 8) | global | All plans use v2 idioms: `model_config = ConfigDict(...)`, `model_dump()`, `model_validate()`, `X \| None` (never `Optional[X]`), PEP 604/585. |
| `from __future__ import annotations` at top of every module | project-observed pattern | [VERIFIED: every existing app module starts with this import]. All new Phase 3 modules MUST follow. |
| `logger = logging.getLogger(__name__)` + `%`-style formatting in logs | project | [VERIFIED: `app/market/simulator.py:25, 230`, `app/db/seed.py:13, 57`]. No f-strings in logging calls. |
| Start work through a GSD command | project | Phase 3 planning + execution runs through `/gsd-plan-phase` → `/gsd-execute-phase`. |
| All project documentation is in `planning/` and `.planning/` | project | Plans go under `.planning/phases/03-portfolio-trading-api/`. PLAN.md consulted but not edited. |

## Sources

### Primary (HIGH confidence)
- `backend/app/lifespan.py` — exact startup sequence Phase 3 extends. [VERIFIED by reading in this session.]
- `backend/app/main.py` — FastAPI entrypoint; no changes expected. [VERIFIED.]
- `backend/app/db/__init__.py`, `seed.py`, `schema.py`, `connection.py` — existing DB surface, seed style template, schema PLAN.md §7 verification. [VERIFIED.]
- `backend/app/market/interface.py` — ABC to extend with `register_tick_observer`. [VERIFIED.]
- `backend/app/market/simulator.py` — `_run_loop` location where observers fire. [VERIFIED.]
- `backend/app/market/massive_client.py` — `_poll_once` location where observers fire. [VERIFIED.]
- `backend/app/market/cache.py` — `get_price` shape matches Phase 3 needs. [VERIFIED.]
- `backend/app/market/stream.py` — router factory template. [VERIFIED.]
- `backend/tests/conftest.py` — existing `db_path` fixture to extend. [VERIFIED.]
- `backend/tests/test_lifespan.py` — `_build_app` + `LifespanManager` pattern for integration tests. [VERIFIED.]
- `backend/pyproject.toml` — dependency list and pytest config. [VERIFIED.]
- `.planning/phases/03-portfolio-trading-api/03-CONTEXT.md` — locked decisions D-01..D-16. [Read verbatim.]
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — D-02 (app.state), D-04 (factory routers). [Read verbatim.]
- `.planning/phases/02-database-foundation/02-CONTEXT.md` — D-01 (long-lived conn), D-02 (sqlite3.Row), D-03 (manual commit). [Read verbatim.]
- `planning/PLAN.md` §7 (schema), §8 (endpoints), §6 (cache contract). [Read verbatim via CLAUDE.md.]
- In-session verification: Pydantic 2.12.5, FastAPI 0.128.7, httpx 0.28.1 all resolved; `ConfigDict(extra="forbid")` + `Literal` + `Field(gt=0)` tested end-to-end. [VERIFIED by shell execution.]

### Secondary (MEDIUM confidence)
- Pydantic v2 migration guide — `Config` → `ConfigDict`, `dict()` → `model_dump()`, etc. [CITED: docs.pydantic.dev/latest/migration/]
- Pydantic v2 concepts — `Field` constraints. [CITED: docs.pydantic.dev/latest/concepts/fields/]

### Tertiary (LOW confidence)
- None. All claims in this document are either verified against the codebase or against a live Python session in this working directory.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library version verified in-session against the installed environment.
- Architecture: HIGH — mirrors already-shipped Phase 1 (`create_stream_router`) and Phase 2 (`seed_defaults`) patterns. No novel architecture except the `register_tick_observer` hook, which is one method and one list attribute.
- Pitfalls: HIGH — all 10 pitfalls either cross-referenced to concrete lines in the codebase or verified via a shell session in this working directory.
- Observer callback signature (zero-arg): MEDIUM — justified design choice, marked [ASSUMED] (A1). Planner may revisit if needed.
- Boot-time initial snapshot desirability: MEDIUM — marked [ASSUMED] (A2). Trivial to flip by changing one line if the user prefers no boot snapshot.

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (30 days — stable phase; no fast-moving external APIs involved)
