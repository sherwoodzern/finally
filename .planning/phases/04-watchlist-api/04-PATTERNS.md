# Phase 4: Watchlist API - Pattern Map

**Mapped:** 2026-04-21
**Files analyzed:** 12 (10 new + 2 modified)
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/watchlist/__init__.py` | config / package re-export | N/A | `backend/app/portfolio/__init__.py` | exact |
| `backend/app/watchlist/models.py` | model (Pydantic v2 schemas) | request-response (validation) | `backend/app/portfolio/models.py` | exact |
| `backend/app/watchlist/service.py` | service (DB-only pure functions) | CRUD | `backend/app/portfolio/service.py` | exact |
| `backend/app/watchlist/routes.py` | controller (FastAPI router factory) | request-response | `backend/app/portfolio/routes.py` | exact |
| `backend/app/lifespan.py` (modify) | config (router mount) | startup wiring | self (Phase 3 line 66 mount) | exact |
| `backend/tests/watchlist/__init__.py` | test (package marker) | N/A | `backend/tests/portfolio/__init__.py` | exact |
| `backend/tests/watchlist/conftest.py` | test (fixtures) | N/A | `backend/tests/portfolio/conftest.py` | exact |
| `backend/tests/watchlist/test_models.py` | test (unit) | request-response validation | `backend/tests/portfolio/test_service_validation.py` | role-match |
| `backend/tests/watchlist/test_service_*.py` | test (unit) | CRUD | `backend/tests/portfolio/test_service_buy.py` + `test_service_validation.py` | exact |
| `backend/tests/watchlist/test_routes_get.py` | test (integration) | request-response | `backend/tests/portfolio/test_routes_portfolio.py` | exact |
| `backend/tests/watchlist/test_routes_post.py` | test (integration) | request-response | `backend/tests/portfolio/test_routes_trade.py::TestBuy` | exact |
| `backend/tests/watchlist/test_routes_delete.py` | test (integration) | request-response | `backend/tests/portfolio/test_routes_trade.py::TestErrors` | role-match |
| `backend/tests/test_lifespan.py` (extend) | test (integration) | startup wiring | self (lines 163-171 portfolio router assertion) | exact |

## Pattern Assignments

---

### `backend/app/watchlist/__init__.py` (config, package re-export)

**Analog:** `backend/app/portfolio/__init__.py`

**Complete template** (lines 1-57):
```python
"""Portfolio + trading subsystem for FinAlly.

Public API (filled in across Plan 03-02 and 03-03):
    Models: TradeRequest, TradeResponse, PositionOut, PortfolioResponse,
            SnapshotOut, HistoryResponse
    Service: execute_trade, get_portfolio, compute_total_value, get_history,
             make_snapshot_observer
    Exceptions: TradeValidationError, InsufficientCash, InsufficientShares,
                UnknownTicker, PriceUnavailable
    Router: create_portfolio_router
"""

from __future__ import annotations

from .models import (
    HistoryResponse,
    PortfolioResponse,
    PositionOut,
    SnapshotOut,
    TradeRequest,
    TradeResponse,
)
from .routes import create_portfolio_router
from .service import (
    DEFAULT_USER_ID,
    InsufficientCash,
    ...
)

__all__ = [
    "DEFAULT_USER_ID",
    ...
    "create_portfolio_router",
    "execute_trade",
    ...
]
```

**What to copy:**
- Module docstring summarizing the subsystem's public API
- `from __future__ import annotations`
- `from .models import (...)` barrel import
- `from .routes import create_watchlist_router`
- `from .service import (...)` barrel import
- Explicit alphabetized `__all__` list

**What to change for watchlist:**
Re-export `WatchlistAddRequest`, `WatchlistItem`, `WatchlistResponse`, `WatchlistMutationResponse`, `normalize_ticker`, `create_watchlist_router`, `get_watchlist`, `add_ticker`, `remove_ticker`, `AddResult`, `RemoveResult`, `DEFAULT_USER_ID`.

---

### `backend/app/watchlist/models.py` (model, request-response validation)

**Analog:** `backend/app/portfolio/models.py`

**Imports + module docstring** (lines 1-7):
```python
"""Pydantic v2 request/response schemas for the portfolio + trading API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
```

**Strict-config request body pattern** (lines 10-21):
```python
class TradeRequest(BaseModel):
    """Request body for POST /api/portfolio/trade (D-03).

    Strict config: unknown keys produce 422. Literal side + Field(gt=0) quantity
    guarantee malformed inputs are rejected before the handler runs.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
```

**Response model pattern** (lines 48-66):
```python
class PortfolioResponse(BaseModel):
    """Response for GET /api/portfolio."""

    cash_balance: float
    total_value: float
    positions: list[PositionOut]


class SnapshotOut(BaseModel):
    """One snapshot in HistoryResponse.snapshots."""

    total_value: float
    recorded_at: str
```

**Phase 4 additions (novel, not in Phase 3):**

- Add a `normalize_ticker(value: str) -> str` module-level helper at the top of `models.py` (above the class definitions) so both the Pydantic `field_validator` on `WatchlistAddRequest.ticker` and the DELETE path-param pre-check in `routes.py` can import it. Verified `field_validator(mode="before")` shape from RESEARCH.md Pattern 3:

```python
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")


def normalize_ticker(value: str) -> str:
    """Strip + uppercase + regex-validate a ticker symbol. Raises ValueError on mismatch."""
    v = value.strip().upper()
    if not _TICKER_RE.fullmatch(v):
        raise ValueError(f"invalid ticker: {value!r}")
    return v


class WatchlistAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)
```

- `WatchlistItem` uses `Literal["up", "down", "flat"] | None` for `direction` - copy strings verbatim from `PriceUpdate.direction` at `backend/app/market/models.py:31-37` (Pitfall 1 guard).
- `WatchlistMutationResponse` uses `status: Literal["added", "exists", "removed", "not_present"]` - novel to Phase 4 per CONTEXT D-06; no translation from HTTP status codes.

---

### `backend/app/watchlist/service.py` (service, CRUD)

**Analog:** `backend/app/portfolio/service.py`

**Imports + module docstring + constants** (lines 1-25):
```python
"""Pure-function service: trade execution, portfolio valuation, history, snapshot observer."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from app.market import PriceCache

from .models import (
    HistoryResponse,
    PortfolioResponse,
    PositionOut,
    SnapshotOut,
    TradeResponse,
)

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
```

**Phase 4 will trim this to:** `sqlite3`, `uuid`, `datetime.{UTC, datetime}`, `logging`, `Literal`. Import `PriceCache` for the GET path (Open Question #5 in RESEARCH: `get_watchlist(conn, cache)` is fine per Phase 3 precedent). No `from app.market import MarketDataSource` - the service stays source-agnostic per CONTEXT D-02.

**Pure-function-on-conn service signature** (lines 83-95):
```python
def execute_trade(
    conn: sqlite3.Connection,
    cache: PriceCache,
    ticker: str,
    side: Literal["buy", "sell"],
    quantity: float,
    user_id: str = DEFAULT_USER_ID,
) -> TradeResponse:
    """Execute a market-order trade: validate, then write cash + position + trade + snapshot.

    All writes happen inside one implicit sqlite3 transaction and commit once at the
    end (D-12). On any validation failure, zero rows are written.
    """
    ticker = ticker.strip().upper()
```

**Phase 4 service signatures (novel shapes, but same (conn, ...) discipline):**
```python
def get_watchlist(conn: sqlite3.Connection, cache: PriceCache, user_id: str = DEFAULT_USER_ID) -> WatchlistResponse:
def add_ticker(conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID) -> AddResult:
def remove_ticker(conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID) -> RemoveResult:
```

**Parameterized-query + rowcount pattern** (lines 146-156, `execute_trade` DELETE shape):
```python
if abs(new_qty) < _ZERO_QTY_EPSILON:
    conn.execute(
        "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
```

**GET with cache-cold fallback pattern** (lines 240-272, `get_portfolio`):
```python
rows = conn.execute(
    "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = ? "
    "ORDER BY ticker ASC",
    (user_id,),
).fetchall()

positions: list[PositionOut] = []
for row in rows:
    ticker = row["ticker"]
    qty = float(row["quantity"])
    avg = float(row["avg_cost"])
    cached = cache.get_price(ticker)
    current = cached if cached is not None else avg
    ...
    positions.append(PositionOut(...))

return PortfolioResponse(cash_balance=cash, total_value=round(total, 2), positions=positions)
```

**Commit + log pattern** (lines 191-200):
```python
conn.commit()

logger.info(
    "Trade executed: %s %s x %.4f @ %.2f (cash=%.2f)",
    ticker,
    side,
    quantity,
    price,
    new_cash,
)
```

- `%`-style log args only (CONVENTIONS rule).
- `conn.commit()` exactly once per write path.
- `str(uuid.uuid4())` + `datetime.now(UTC).isoformat()` for IDs + timestamps (matches `app/db/seed.py:53-55`).

**Phase 4 novel SQL (from RESEARCH.md Examples 1 + 2; no direct analog in Phase 3):**

Add:
```python
cur = conn.execute(
    "INSERT INTO watchlist (id, user_id, ticker, added_at) "
    "VALUES (?, ?, ?, ?) "
    "ON CONFLICT(user_id, ticker) DO NOTHING",
    (str(uuid.uuid4()), user_id, ticker, now),
)
if cur.rowcount == 1:
    conn.commit()
    ...
```

Remove (planner may pick `RETURNING id` or `cursor.rowcount` per Claude's Discretion; recommendation is `rowcount` for symmetry with add path):
```python
cur = conn.execute(
    "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
    (user_id, ticker),
)
if cur.rowcount == 1:
    conn.commit()
    ...
```

Get ordering from `app/db/seed.py:69-73`:
```python
rows = conn.execute(
    "SELECT ticker, added_at FROM watchlist WHERE user_id = ? "
    "ORDER BY added_at ASC, ticker ASC",
    (user_id,),
).fetchall()
```

---

### `backend/app/watchlist/routes.py` (controller, request-response)

**Analog:** `backend/app/portfolio/routes.py`

**Imports pattern** (lines 1-18):
```python
"""HTTP edge for the portfolio subsystem: GET /, POST /trade, GET /history."""

from __future__ import annotations

import sqlite3
import time

from fastapi import APIRouter, HTTPException, Query, Request

from app.market import PriceCache

from . import service
from .models import (
    HistoryResponse,
    PortfolioResponse,
    TradeRequest,
    TradeResponse,
)
```

Phase 4 adds `from app.market import MarketDataSource` (needed for the `source: MarketDataSource` factory parameter). Drop `Query` and `Request` and `time` (no query params, no app.state mutation in watchlist routes).

**Factory-closure router shell** (lines 21-32):
```python
def create_portfolio_router(
    db: sqlite3.Connection,
    cache: PriceCache,
) -> APIRouter:
    """Build an APIRouter closed over db + cache.

    A fresh router per call mirrors create_stream_router (app/market/stream.py)
    and avoids duplicate routes across test-spawned apps (01-CONTEXT.md D-04).
    Domain validation failures from the service layer map 1:1 to HTTP 400 with
    detail={"error": exc.code, "message": str(exc)} (D-03, D-09, D-10).
    """
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])
```

**Phase 4 signature:**
```python
def create_watchlist_router(
    db: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
) -> APIRouter:
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])
```

**GET handler pattern** (lines 34-36):
```python
@router.get("", response_model=PortfolioResponse)
async def get_portfolio() -> PortfolioResponse:
    return service.get_portfolio(db, cache)
```

**POST handler with response_model + service call** (lines 38-53):
```python
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
        ) from exc
    ...
    return response
```

**Phase 4 POST handler (novel DB-first-source-second + log-and-continue from RESEARCH Example 4):**
```python
@router.post("", response_model=WatchlistMutationResponse)
async def post_watchlist(req: WatchlistAddRequest) -> WatchlistMutationResponse:
    """Add a ticker to the watchlist; idempotent no-op on duplicate (D-06, D-09, D-11)."""
    result = service.add_ticker(db, req.ticker)

    if result.status == "added":
        try:
            await source.add_ticker(req.ticker)
        except Exception:
            # D-11: DB is the reconciliation anchor; next restart heals.
            logger.warning(
                "Watchlist: source.add_ticker(%s) raised after DB commit",
                req.ticker,
                exc_info=True,
            )

    return WatchlistMutationResponse(ticker=result.ticker, status=result.status)
```

**DELETE handler (novel for Phase 4; path param pre-check via `normalize_ticker`):**
```python
@router.delete("/{ticker}", response_model=WatchlistMutationResponse)
async def delete_watchlist(ticker: str) -> WatchlistMutationResponse:
    try:
        normalized = normalize_ticker(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    result = service.remove_ticker(db, normalized)

    if result.status == "removed":
        try:
            await source.remove_ticker(normalized)
        except Exception:
            logger.warning(
                "Watchlist: source.remove_ticker(%s) raised after DB commit",
                normalized,
                exc_info=True,
            )

    return WatchlistMutationResponse(ticker=result.ticker, status=result.status)
```

**Key deltas from portfolio routes:**
- No `HTTPException(400, ...)` mapping - the service does not raise; it returns `AddResult` / `RemoveResult` with a `status` discriminator (CONTEXT D-06).
- No `request: Request` injection - no `app.state` mutation (watchlist mutations do not touch snapshots).
- Add a module-level `logger = logging.getLogger(__name__)` (missing from `app/portfolio/routes.py` because that file has no logging; Phase 4 needs it for the D-11 log-and-continue warnings).

---

### `backend/app/lifespan.py` (MODIFY - one-line router mount)

**Analog:** self (existing Phase 3 line 66 mount)

**Current state at lines 60-66:**
```python
    app.state.db = conn
    app.state.price_cache = cache
    app.state.market_source = source
    app.state.last_snapshot_at = 0.0                                   # D-06
    source.register_tick_observer(make_snapshot_observer(app.state))   # D-05
    app.include_router(create_stream_router(cache))
    app.include_router(create_portfolio_router(conn, cache))
```

**Phase 4 insertion (one line after line 66):**
```python
    app.include_router(create_portfolio_router(conn, cache))
    app.include_router(create_watchlist_router(conn, cache, source))   # D-13
```

**Import line 13 extension:**
Current:
```python
from .portfolio import create_portfolio_router, make_snapshot_observer
```
Add:
```python
from .watchlist import create_watchlist_router
```

**No other changes to lifespan.py.** `app.state.market_source` is already attached (line 62); the watchlist router factory reads it via its closure parameter `source`. No new `app.state` fields.

---

### `backend/tests/watchlist/__init__.py` (test, package marker)

**Analog:** `backend/tests/portfolio/__init__.py`

Empty file. Mirrors the portfolio package marker exactly.

---

### `backend/tests/watchlist/conftest.py` (test, fixtures)

**Analog:** `backend/tests/portfolio/conftest.py`

**Complete template** (lines 1-34):
```python
"""Shared fixtures for portfolio service + route tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from app.db import init_database, seed_defaults
from app.market import PriceCache
from app.market.seed_prices import SEED_PRICES


@pytest.fixture
def fresh_db() -> Iterator[sqlite3.Connection]:
    """Yield a seeded in-memory sqlite3.Connection with sqlite3.Row row factory."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    seed_defaults(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def warmed_cache() -> PriceCache:
    """Return a PriceCache pre-populated with seed prices for the 10 default tickers."""
    cache = PriceCache()
    for ticker, price in SEED_PRICES.items():
        cache.update(ticker=ticker, price=price)
    return cache
```

**Phase 4 clone verbatim.** For route tests that need a mutable source mock, add a `mock_source` fixture that returns an `AsyncMock(spec=MarketDataSource)` - but only if the planner chooses to unit-test the route's `source.add_ticker` call independently. Integration tests use the real `LifespanManager(app)` harness (below) and read `app.state.market_source` directly.

---

### `backend/tests/watchlist/test_models.py` (test, unit)

**Analog:** `backend/tests/portfolio/test_service_validation.py` (parametrize-style class tests)

**Class-per-behavior pattern** (lines 27-37):
```python
class TestValidation:
    """Domain-exception rejection: zero DB writes on any validation failure."""

    def test_rejects_unknown_ticker_and_writes_nothing(self, fresh_db, warmed_cache):
        """ZZZZ is not in the watchlist: raises UnknownTicker, leaves DB unchanged."""
        before = _db_counts(fresh_db)

        with pytest.raises(UnknownTicker):
            execute_trade(fresh_db, warmed_cache, "ZZZZ", "buy", 1.0)

        assert _db_counts(fresh_db) == before
```

**Phase 4 adaptation:** Plain `class TestNormalize:` (no fixtures needed) calling `normalize_ticker("  aapl  ") == "AAPL"`, `normalize_ticker("BRK.B") == "BRK.B"`, `pytest.raises(ValueError, match="invalid ticker")` for `"1X"`, `"$$"`, empty string. Separate `class TestRequestModel:` that instantiates `WatchlistAddRequest(ticker="aapl")` and checks `.ticker == "AAPL"`; asserts `ValidationError` raised for `extra="forbid"` key (`WatchlistAddRequest(ticker="AAPL", extra="x")`).

---

### `backend/tests/watchlist/test_service_{get,add,remove}.py` (test, unit - CRUD)

**Analogs:**
- `backend/tests/portfolio/test_service_buy.py` (happy path + DB-state assertions)
- `backend/tests/portfolio/test_service_validation.py` (zero-writes-on-rejection)

**DB-counts snapshot helper** (`test_service_validation.py` lines 16-24):
```python
def _db_counts(conn) -> tuple[float, int, int, int]:
    """Snapshot cash + row counts for positions, trades, portfolio_snapshots."""
    cash = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ).fetchone()["cash_balance"]
    pos = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    tr = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    snap = conn.execute("SELECT COUNT(*) FROM portfolio_snapshots").fetchone()[0]
    return cash, pos, tr, snap
```

**Phase 4 adaptation:** Use a simpler `_watchlist_count(conn, user_id="default")` that returns `COUNT(*) FROM watchlist`. Assert invariants like:
- `add_ticker` on new ticker -> `status="added"`, count increases by 1.
- `add_ticker` on existing ticker -> `status="exists"`, count unchanged.
- `remove_ticker` on existing ticker -> `status="removed"`, count decreases by 1.
- `remove_ticker` on missing ticker -> `status="not_present"`, count unchanged.

**Direct-DB-row assertion pattern** (`test_service_buy.py` lines 24-29):
```python
pos = fresh_db.execute(
    "SELECT quantity, avg_cost FROM positions WHERE user_id = 'default' AND ticker = 'AAPL'"
).fetchone()
assert pos is not None
assert pos["quantity"] == 5.0
```

**GET ordering test pattern:** Use `fresh_db` (has the 10 seeded tickers). Call `get_watchlist(fresh_db, warmed_cache)` - assert `[item.ticker for item in response.items]` equals `sorted(SEED_PRICES.keys())` (since all seeds share one `added_at`, the tiebreaker is ticker ASC per CONTEXT D-08).

**Cache-cold fallback test pattern:** Make a cache with only 1 ticker warm, call `get_watchlist`, assert the 9 cold items have `price is None, previous_price is None, change_percent is None, direction is None, timestamp is None`.

---

### `backend/tests/watchlist/test_routes_get.py` (test, integration)

**Analog:** `backend/tests/portfolio/test_routes_portfolio.py`

**Integration-test harness (clone verbatim)** (lines 1-17):
```python
"""Integration tests for GET /api/portfolio (PORT-01)."""

from __future__ import annotations

import os
from unittest.mock import patch

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)
```

**Test method skeleton** (lines 24-36):
```python
@pytest.mark.asyncio
class TestGetPortfolio:
    """HTTP contract for GET /api/portfolio."""

    async def test_returns_seeded_cash_balance_and_empty_positions(self, db_path):
        """Fresh DB -> cash_balance=10000.0, total_value=10000.0, positions=[]."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/portfolio")
                    assert resp.status_code == 200
                    body = resp.json()
                    assert body["cash_balance"] == 10000.0
                    assert body["total_value"] == 10000.0
                    assert body["positions"] == []
```

**Cache manipulation inside the harness** (lines 51-54):
```python
                    # Evict the ticker so get_portfolio falls back to avg_cost.
                    app.state.price_cache.remove("AAPL")
```

**Phase 4 adaptation:**
- Clone `_build_app()` and the `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` + `LifespanManager(app)` + `ASGITransport` + `AsyncClient` sandwich.
- Assertions target `resp.json()` = `{"items": [...]}` with 10 seed tickers ordered `added_at ASC, ticker ASC` (all same added_at means alpha order).
- For cold-cache fallback: `app.state.price_cache.remove("AAPL")` inside the `async with LifespanManager` block, then GET and assert that the AAPL item has `price is None`.
- For warm-cache success: read prices back from `app.state.price_cache.get("AAPL")` and assert `body["items"][0]["price"] == app.state.price_cache.get_price("AAPL")` (don't hardcode numbers; Pitfall 5 warning).

---

### `backend/tests/watchlist/test_routes_post.py` (test, integration)

**Analog:** `backend/tests/portfolio/test_routes_trade.py::TestBuy` (lines 21-62) + `TestSchema` (lines 202-229)

**Happy-path pattern** (lines 24-48):
```python
async def test_buy_happy_path(self, db_path):
    """POST buy AAPL x1 returns 200 with TradeResponse; GET /api/portfolio reflects it."""
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/portfolio/trade",
                    json={"ticker": "AAPL", "side": "buy", "quantity": 1.0},
                )
                assert resp.status_code == 200, resp.text
                body = resp.json()
                assert body["ticker"] == "AAPL"
                assert body["side"] == "buy"
                ...
```

**422 validation pattern** (lines 202-229):
```python
@pytest.mark.asyncio
class TestSchema:
    """Pydantic 422 rejections for malformed bodies."""

    async def test_rejects_malformed_body(self, db_path):
        """Bad enum, non-positive quantity, and extra keys all return 422."""
        ...
        extra_key = await client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 1, "extra": "x"},
        )
        assert extra_key.status_code == 422
```

**Phase 4 adaptations (novel to WATCH-02 / SC#4):**
- `TestPost::test_add_new_ticker_returns_added`: POST `{"ticker": "PYPL"}` -> 200 + `{"ticker": "PYPL", "status": "added"}` + `"PYPL" in app.state.market_source.get_tickers()`.
- `TestPost::test_duplicate_returns_exists_not_error`: POST `{"ticker": "AAPL"}` (seed ticker) -> 200 + `{"ticker": "AAPL", "status": "exists"}`; NO 409, NO 500. DB row count for user_id='default' unchanged.
- `TestPost::test_add_warms_cache`: After POST with simulator, `app.state.price_cache.get("PYPL")` is non-None (simulator's `add_ticker` seeds immediately per `simulator.py:247-250`).
- `TestPost::test_source_failure_logs_but_returns_200` (D-11): monkey-patch `app.state.market_source.add_ticker` to raise; POST new ticker; assert 200 `status="added"` and DB row persists; assert warning logged with `exc_info=True`.
- `TestPostValidation::test_rejects_malformed_body`: extra keys, missing `ticker`, empty string, `"1X"`, `"lowercase123"` -> 422.

---

### `backend/tests/watchlist/test_routes_delete.py` (test, integration)

**Analog:** `backend/tests/portfolio/test_routes_trade.py::TestBuy::test_full_sell_deletes_row` (lines 92-114)

**Delete-then-assert-absence pattern** (lines 92-114):
```python
async def test_full_sell_deletes_row(self, db_path):
    """BUY 1 then SELL 1 zeros the position; the row is deleted (D-15)."""
    ...
    s = await client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "sell", "quantity": 1.0},
    )
    assert s.status_code == 200, s.text
    assert s.json()["position_quantity"] == 0.0

    p = await client.get("/api/portfolio")
    tickers = {pos["ticker"] for pos in p.json()["positions"]}
    assert "AAPL" not in tickers
```

**Phase 4 adaptations:**
- `TestDelete::test_remove_existing_ticker`: DELETE `/api/watchlist/AAPL` -> 200 + `{"ticker": "AAPL", "status": "removed"}`. Subsequent GET does not include AAPL. `app.state.price_cache.get("AAPL")` returns None (source.remove_ticker cascaded to cache per `simulator.py:256`).
- `TestDelete::test_remove_stops_source`: `"AAPL" not in app.state.market_source.get_tickers()` after DELETE.
- `TestDelete::test_missing_returns_not_present_not_error` (SC#4): DELETE `/api/watchlist/ZZZZ` (not seeded) -> 200 + `{"ticker": "ZZZZ", "status": "not_present"}`; NOT 404, NOT 500.
- `TestDeleteValidation::test_bad_path_422`: DELETE `/api/watchlist/1X`, `/api/watchlist/lowercase`, `/api/watchlist/AAPL!` -> 422. Handler pre-check calls `normalize_ticker` and maps `ValueError` to `HTTPException(422)`.

---

### `backend/tests/test_lifespan.py` (MODIFY - extend existing file)

**Analog:** self, lines 163-171 (the Phase 3 portfolio router mount assertion)

**Existing portfolio mount assertion** (lines 163-171):
```python
async def test_includes_portfolio_router_during_startup(self, db_path):
    """app.include_router(create_portfolio_router(conn, cache)) runs in lifespan."""
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            paths = {getattr(r, "path", None) for r in app.router.routes}
            assert "/api/portfolio" in paths, paths
            assert "/api/portfolio/trade" in paths, paths
            assert "/api/portfolio/history" in paths, paths
```

**Phase 4 addition (clone-and-edit):**
```python
async def test_includes_watchlist_router_during_startup(self, db_path):
    """app.include_router(create_watchlist_router(conn, cache, source)) runs in lifespan (D-13)."""
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            paths = {getattr(r, "path", None) for r in app.router.routes}
            assert "/api/watchlist" in paths, paths
            assert "/api/watchlist/{ticker}" in paths, paths
```

---

## Shared Patterns

### Authentication / Authorization
**Not applicable.** Single-user demo. `user_id = "default"` is hardcoded in every service function as a keyword-default argument (Phase 2 D-04, Phase 3 inherited). No middleware, no guards, no session.

### Module Header Convention
**Source:** Every module in `backend/app/`
**Apply to:** All new files in `backend/app/watchlist/` and `backend/tests/watchlist/`

```python
"""<one-line module docstring describing its role>."""

from __future__ import annotations

# ... stdlib imports ...
# ... third-party imports ...
# ... local imports (relative, not `from app.watchlist...`) ...
```

Verified in `backend/app/portfolio/service.py:1-4`, `backend/app/portfolio/routes.py:1-4`, `backend/app/portfolio/models.py:1-3`, `backend/app/market/simulator.py`, `backend/app/db/seed.py:1-4`.

### Logging
**Source:** `backend/app/portfolio/service.py:23`, `backend/app/db/seed.py:13`, `backend/app/market/simulator.py`
**Apply to:** `backend/app/watchlist/service.py` and `backend/app/watchlist/routes.py`

```python
import logging
logger = logging.getLogger(__name__)

# Later:
logger.info("Watchlist: added %s for user %s", ticker, user_id)
logger.warning(
    "Watchlist: source.add_ticker(%s) raised after DB commit",
    req.ticker,
    exc_info=True,
)
```

Rules:
- `%`-style args, never f-strings.
- No emojis.
- INFO for routine mutations AND idempotent no-ops (CONTEXT Claude's Discretion: match `seed_defaults` style).
- WARNING + `exc_info=True` for log-and-continue after post-commit source failures (D-11, Example 4).

### Pydantic v2 Request Body Discipline
**Source:** `backend/app/portfolio/models.py:10-21`
**Apply to:** `backend/app/watchlist/models.py::WatchlistAddRequest`

```python
class WatchlistAddRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ticker: str

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)
```

Critical: `mode="before"` runs prior to type coercion - ensures `"  aapl  "` is stripped/uppercased before the regex check. `min_length=1` is redundant once the regex is present (Pitfall 6).

### Factory-Closure Router
**Source:** `backend/app/portfolio/routes.py:21-32`, `backend/app/market/stream.py`
**Apply to:** `backend/app/watchlist/routes.py::create_watchlist_router`

```python
def create_watchlist_router(
    db: sqlite3.Connection,
    cache: PriceCache,
    source: MarketDataSource,
) -> APIRouter:
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("", response_model=WatchlistResponse)
    async def get_watchlist_route() -> WatchlistResponse:
        return service.get_watchlist(db, cache)

    # ... POST, DELETE handlers ...

    return router
```

- `prefix` + `tags` on the `APIRouter`, not per handler.
- `response_model=` on every decorator (Phase 3 parity).
- Fresh router per call (no module-level router); required for test isolation.

### Parameterized Queries
**Source:** `backend/app/portfolio/service.py:100-102, 111-114, 117-120`, `backend/app/db/seed.py:40-43, 52-56, 69-73`
**Apply to:** every SQL statement in `backend/app/watchlist/service.py`

```python
conn.execute(
    "SELECT ... FROM watchlist WHERE user_id = ? AND ticker = ?",
    (user_id, ticker),
)
```

Never string-interpolate. Never `f"...{ticker}..."`. SQL injection is mitigated both by the regex-validated ticker (ASVS V5) and by the `?` placeholder discipline.

### Integration Test Harness
**Source:** `backend/tests/portfolio/test_routes_portfolio.py:1-17, 24-36`
**Apply to:** `test_routes_get.py`, `test_routes_post.py`, `test_routes_delete.py` under `tests/watchlist/`

```python
import os
from unittest.mock import patch

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)


@pytest.mark.asyncio
class TestXxx:
    async def test_yyy(self, db_path):
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/watchlist")
                    assert resp.status_code == 200
                    ...
```

The `db_path` fixture comes from `backend/tests/conftest.py:14-26` - per-test fresh sqlite file, auto-cleanup. The `clear=True` in `patch.dict` wipes parent-process env (notably removes any `MASSIVE_API_KEY` so the factory picks `SimulatorDataSource`); `DB_PATH` must be re-set inside the dict.

### Unit Test Fixtures
**Source:** `backend/tests/portfolio/conftest.py:15-34`
**Apply to:** `backend/tests/watchlist/conftest.py`

Exact clone:
- `fresh_db` yields an in-memory `sqlite3.Connection` with `sqlite3.Row` + `init_database` + `seed_defaults`.
- `warmed_cache` returns a `PriceCache` pre-populated from `SEED_PRICES`.

## No Analog Found

None. Every file in Phase 4 has a direct Phase 3 (or Phase 2) template. The novel elements are:
- The `normalize_ticker` helper (local within `models.py`, no cross-package analog - RESEARCH Pattern 3).
- `INSERT ... ON CONFLICT(user_id, ticker) DO NOTHING` + `cursor.rowcount` discrimination (RESEARCH Example 1; no existing use in the codebase - `seed_defaults` uses `INSERT OR IGNORE` + `COUNT(*)` guard).
- The idempotent mutation response shape (`status` literal discriminator instead of 4xx on the no-op path - RESEARCH Pattern 4, CONTEXT D-06).
- Route-level DB-first-then-source choreography with log-and-continue (RESEARCH Example 4, CONTEXT D-11).

These four novel elements are fully specified by RESEARCH.md examples; planner should lift them verbatim into the implementation plan.

## Metadata

**Analog search scope:**
- `backend/app/portfolio/` (4 files) - primary analog for the sub-package
- `backend/app/market/` (cache, interface, simulator, massive_client, models) - cache/source contract references
- `backend/app/db/` (schema, seed) - SQL + DEFAULT_USER_ID constants
- `backend/app/lifespan.py` - router mount point (line 66 insertion site)
- `backend/tests/portfolio/` (7 files) - test pattern analogs
- `backend/tests/conftest.py` - shared `db_path` fixture
- `backend/tests/test_lifespan.py` - extension site for D-13 assertion

**Files scanned:** ~22 source + test files

**Pattern extraction date:** 2026-04-21

**Key insight:** Phase 4 is a near-mechanical clone of Phase 3's `app/portfolio/` with four narrowly scoped novelties (normalize_ticker helper, ON CONFLICT SQL, status-literal response, log-and-continue DB-first-source-second routing). Every other decision is "do what Phase 3 did."
