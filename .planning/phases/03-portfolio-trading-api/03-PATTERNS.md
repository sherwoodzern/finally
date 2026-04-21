# Phase 3: Portfolio & Trading API - Pattern Map

**Mapped:** 2026-04-20
**Files analyzed:** 10 new/modified production files + 3 new test modules
**Analogs found:** 13 / 13 (all have strong in-repo matches)

## File Classification

### Production files

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/portfolio/__init__.py` (NEW) | package-init | re-export | `backend/app/db/__init__.py` / `backend/app/market/__init__.py` | exact |
| `backend/app/portfolio/models.py` (NEW) | pydantic schemas | request/response | (no prior pydantic file in repo) — use RESEARCH.md `TradeRequest` + Pydantic v2 docs | role-match |
| `backend/app/portfolio/service.py` (NEW) | pure-function service | HTTP ↔ SQLite ↔ cache | `backend/app/db/seed.py` | exact |
| `backend/app/portfolio/routes.py` (NEW) | router factory | HTTP → service | `backend/app/market/stream.py` | exact |
| `backend/app/market/interface.py` (MOD) | ABC extension | interface contract | `backend/app/market/interface.py` (self-precedent) | exact |
| `backend/app/market/simulator.py` (MOD) | async loop hook | cache → observer | `backend/app/market/simulator.py::_run_loop` (self-precedent) | exact |
| `backend/app/market/massive_client.py` (MOD) | async poll hook | poll → observer | `backend/app/market/massive_client.py::_poll_once` (self-precedent) | exact |
| `backend/app/lifespan.py` (MOD) | lifespan wiring | startup | `backend/app/lifespan.py` (self-precedent) | exact |

### Test files

| New Test File | Role | Analog | Match Quality |
|---------------|------|--------|---------------|
| `backend/tests/portfolio/test_service.py` (NEW) | service unit tests | `backend/tests/db/test_seed.py` | exact (free-function + sqlite3 fixture) |
| `backend/tests/portfolio/test_routes.py` (NEW) | HTTP integration tests | `backend/tests/test_main.py::TestHealth` | exact (`ASGITransport` + `LifespanManager` — bounded JSON, no SSE) |
| `backend/tests/portfolio/test_observer.py` (NEW) | tick-observer tests | `backend/tests/market/test_simulator_source.py` + `test_massive.py` | exact (async loop + mocked source) |
| `backend/tests/test_lifespan.py` (MOD) | lifespan additions | self-precedent | exact (add cases for router mount + `last_snapshot_at` + observer registration) |

---

## Pattern Assignments

### `backend/app/portfolio/__init__.py` (package-init, re-export)

**Analog:** `backend/app/db/__init__.py`

**Full excerpt to replicate** (entire file):

```python
"""SQLite persistence subsystem for FinAlly.

Public API:
    open_database           - Open a long-lived sqlite3.Connection.
    init_database           - Run CREATE TABLE IF NOT EXISTS for all six tables.
    seed_defaults           - Insert default user + 10-ticker watchlist (idempotent).
    get_watchlist_tickers   - Return the default user's watchlist ticker list.
"""

from __future__ import annotations

from .connection import open_database
from .seed import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)

__all__ = [
    "open_database",
    "init_database",
    "seed_defaults",
    "get_watchlist_tickers",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_USER_ID",
]
```
*(from `backend/app/db/__init__.py:1-28`)*

**What to replicate:**
- Module docstring starts `"""Portfolio + trading subsystem for FinAlly."""` then lists Public API items on indented lines.
- `from __future__ import annotations`.
- Explicit `from .service import ...` + `from .routes import ...` + `from .models import ...`.
- Explicit `__all__` list (not `*`), alphabetical-ish but grouped by category.

**Exact surface for this package** (from 03-RESEARCH.md §Recommended Project Structure):
- Router factory: `create_portfolio_router`
- Service free functions: `execute_trade`, `get_portfolio`, `get_history`, `compute_total_value`, `record_snapshot`, `make_snapshot_observer`
- Domain exceptions: `TradeValidationError`, `InsufficientCash`, `InsufficientShares`, `UnknownTicker`, `PriceUnavailable`
- Response models: `PortfolioResponse`, `PositionOut`, `TradeResponse`, `TradeRequest`, `SnapshotOut`, `HistoryResponse`

**What's new:** None. This is a pure re-export file matching the existing convention.

---

### `backend/app/portfolio/models.py` (NEW, pydantic v2 schemas)

**Analog:** No prior pydantic file in the repo. The pattern comes from Pydantic v2 docs and is specified fully in 03-RESEARCH.md §Code Examples (lines 372-432). Domain excerpts are reproduced here as the executor's reference.

**Imports + docstring pattern to replicate** (from any module in the repo):

```python
"""Pydantic v2 request/response schemas for the portfolio + trading API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
```

**`TradeRequest` pattern — strict input config** (from 03-RESEARCH.md lines 379-386):

```python
class TradeRequest(BaseModel):
    """Request body for POST /api/portfolio/trade."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
```

**Response models** — default lenient `BaseModel` (no `extra="forbid"`), PEP-604 `list[PositionOut]`, snake_case fields (see 03-RESEARCH.md lines 389-432 for the full set: `TradeResponse`, `PositionOut`, `PortfolioResponse`, `SnapshotOut`, `HistoryResponse`).

**What's new:**
- Only strict (`extra="forbid"`) on REQUEST models. Response models stay lenient so additive evolution doesn't break clients (Pitfall 4, 03-RESEARCH.md line 332-336).
- Use v2 names (`model_config`, `model_dump`, `model_validate`) — NEVER `class Config`, `dict()`, `parse_obj` (Pitfall 7).
- `Literal["buy", "sell"]` for the side enum — FastAPI produces a 422 on malformed sides before the handler runs (D-11).

---

### `backend/app/portfolio/service.py` (NEW, pure-function service)

**Analog:** `backend/app/db/seed.py`

**Imports pattern** (from `backend/app/db/seed.py:1-16`):

```python
"""Idempotent seed for users_profile + 10-ticker default watchlist."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime

from app.db.schema import SCHEMA_STATEMENTS
from app.market.seed_prices import SEED_PRICES

logger = logging.getLogger(__name__)

DEFAULT_USER_ID = "default"
DEFAULT_CASH_BALANCE = 10000.0
```

**Free-function + explicit-commit pattern** (from `backend/app/db/seed.py:26-59`):

```python
def seed_defaults(conn: sqlite3.Connection) -> None:
    """Insert the default user row and 10-ticker watchlist when missing (DB-02)."""
    now = datetime.now(UTC).isoformat()

    conn.execute(
        "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) "
        "VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH_BALANCE, now),
    )
    ...
    if existing == 0:
        for ticker in SEED_PRICES:
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) "
                "VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now),
            )
        logger.info("Seeded default watchlist with %d tickers", len(SEED_PRICES))

    conn.commit()
```

**What to replicate exactly:**
- `"""Module docstring."""` + `from __future__ import annotations`.
- `import sqlite3` + `import uuid` + `from datetime import UTC, datetime` + `import logging`.
- `logger = logging.getLogger(__name__)` at module top.
- Free functions accept `conn: sqlite3.Connection` as the first argument; state/cache (`PriceCache`) next; business args last with `user_id: str = DEFAULT_USER_ID` as an optional last kwarg.
- SQL as multi-line f-string-free strings split with implicit string concatenation (`"INSERT ... " "VALUES (...)"`).
- Parameterised queries — always `(?, ?, ?)` placeholders, never string interpolation.
- `str(uuid.uuid4())` at the INSERT site for primary keys.
- `datetime.now(UTC).isoformat()` for `*_at` columns.
- Single `conn.commit()` at the end of each write path (D-12).
- `%`-style logging: `logger.info("Trade executed: %s %s x %.4f @ %.2f (cash=%.2f)", ...)` — never f-strings (Pitfall: 03-RESEARCH.md line 291, anti-pattern noted).

**What's new (per 03-RESEARCH.md §Code Examples lines 440-601):**
- Domain exception classes at top of file: `TradeValidationError` base + `InsufficientCash`, `InsufficientShares`, `UnknownTicker`, `PriceUnavailable` with `code: str` class attributes (D-09).
- `execute_trade(conn, cache, ticker, side, quantity, user_id="default") -> TradeResponse` — validate-then-write, all writes in one implicit transaction, single `conn.commit()` at the end (D-12, D-13, D-14, D-15, D-16).
- `get_portfolio(conn, cache, user_id="default") -> PortfolioResponse` — reads cash, positions, falls back to `avg_cost` when `cache.get_price(t) is None`.
- `compute_total_value(conn, cache, user_id="default") -> float` — single shared helper used by both `get_portfolio` and the snapshot observer (A4 in assumptions log).
- `get_history(conn, limit, user_id="default") -> HistoryResponse` — `SELECT ... FROM portfolio_snapshots ORDER BY recorded_at ASC [LIMIT ?]`.
- `make_snapshot_observer(state) -> Callable[[], None]` — zero-arg closure, `time.monotonic()` for the 60s clock, `datetime.now(UTC).isoformat()` for the `recorded_at` column value (Pitfall 6).
- NO FastAPI imports anywhere in this module (D-02, D-09).

---

### `backend/app/portfolio/routes.py` (NEW, factory-closure router)

**Analog:** `backend/app/market/stream.py`

**Full factory pattern** (from `backend/app/market/stream.py:18-53`):

```python
"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    This factory pattern lets us inject the PriceCache without globals.
    A fresh APIRouter is constructed per call so repeated calls (e.g. one per
    test-spawned FastAPI app) do not accumulate duplicate /prices routes on a
    shared module-level router. ...
    """
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        ...

    return router
```

**What to replicate exactly:**
- Module docstring one-liner + `from __future__ import annotations` + `logger = logging.getLogger(__name__)`.
- Factory signature: `def create_portfolio_router(db: sqlite3.Connection, cache: PriceCache) -> APIRouter:`.
- `router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])` — fresh APIRouter per call (critical: a module-level APIRouter would accumulate duplicate routes across test-spawned apps; see `stream.py` docstring — this bit us in `test_main.py`, module docstring line 14-20).
- Handlers defined INSIDE the factory with `@router.get(...)` / `@router.post(...)` so they close over `db` and `cache` — no globals.
- `return router` on the last line.

**What's new (per 03-RESEARCH.md lines 640-725):**
- Three handlers: `@router.get("", response_model=PortfolioResponse)`, `@router.post("/trade", response_model=TradeResponse)`, `@router.get("/history", response_model=HistoryResponse)`.
- Handler bodies are one-liners that delegate to `service.*` — no SQL, no business logic.
- Trade handler catches `service.TradeValidationError` and re-raises as `HTTPException(status_code=400, detail={"error": exc.code, "message": str(exc)})` (D-10).
- Trade handler resets the 60s clock at the route level after a successful service call (D-07, 03-RESEARCH.md lines 707-725): `request.app.state.last_snapshot_at = time.monotonic()`. Must take `request: Request` as a handler parameter to access `request.app.state`.
- History handler accepts `limit: int | None = Query(default=None, ge=1, le=10_000)` (Open Question #2 recommendation).
- Imports: `import sqlite3`, `import time`, `from fastapi import APIRouter, HTTPException, Query, Request`, `from app.market import PriceCache`, `from . import service`, `from .models import ...`.

---

### `backend/app/market/interface.py` (MODIFIED, ABC extension)

**Analog:** The existing file itself (self-precedent).

**Current full file** (from `backend/app/market/interface.py:1-58`):

```python
"""Abstract interface for market data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    """Contract for market data providers. ..."""

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates ..."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task and release resources. ..."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. ..."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove a ticker from the active set. ..."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

**Exact insertion point:** after `get_tickers` (end of class, currently line 58). Add one new abstract method — typing import goes in the imports block at the top.

**New method signature** (per 03-RESEARCH.md §Pattern 5, lines 269-284):

```python
from collections.abc import Callable

...
    @abstractmethod
    def register_tick_observer(self, callback: Callable[[], None]) -> None:
        """Register a zero-arg callable invoked after each tick/poll.

        Callbacks must be fast and non-raising. The source wraps each
        invocation in try/except + logger.exception so a broken observer
        does not kill the tick loop. Callbacks always fire on the asyncio
        event loop thread (NOT the Massive worker thread) — see
        CONTEXT.md D-04 and RESEARCH.md Pitfall 2.
        """
```

**What's new:** one new `@abstractmethod` — nothing else in this file changes.

**What to replicate:** docstring style matches the existing ABC docstrings (one-line summary, blank line, expanded behaviour). Non-async `def` (matches `get_tickers`, the only other sync method). `Callable[[], None]` uses `collections.abc.Callable` (Python 3.9+ stdlib, NOT `typing.Callable`).

---

### `backend/app/market/simulator.py` (MODIFIED, observer-firing loop)

**Analog:** The existing file itself (self-precedent).

**Precise insertion points:**

1. **`__init__`** (currently `simulator.py:207-217`) — add `self._observers: list[Callable[[], None]] = []` (and `from collections.abc import Callable` in imports).

2. **`_run_loop`** — currently `simulator.py:260-270`, full body:

```python
async def _run_loop(self) -> None:
    """Core loop: step the simulation, write to cache, sleep."""
    while True:
        try:
            if self._sim:
                prices = self._sim.step()
                for ticker, price in prices.items():
                    self._cache.update(ticker=ticker, price=price)
        except Exception:
            logger.exception("Simulator step failed")
        await asyncio.sleep(self._interval)
```

Insert observer firing AFTER `for ticker, price in prices.items(): self._cache.update(...)` and BEFORE `except Exception:`. Each observer call gets its own nested narrow try/except (D-08) so one broken observer does not skip the others, nor kill the loop:

```python
                for ticker, price in prices.items():
                    self._cache.update(ticker=ticker, price=price)
                for cb in self._observers:
                    try:
                        cb()
                    except Exception:
                        logger.exception("Tick observer raised")
```

3. **New method** after `_run_loop`:

```python
def register_tick_observer(self, callback: Callable[[], None]) -> None:
    self._observers.append(callback)
```

**What to replicate exactly:**
- Narrow `try/except Exception` + `logger.exception(...)` mirrors the existing pattern at the loop body boundary (line 268 already does this). Nested try/except is a conscious narrowing — same style (CONVENTIONS.md).
- `%`-style log message: `logger.exception("Tick observer raised")`.
- No behaviour change when `self._observers` is empty: zero-iteration `for` loop is a no-op.

**Scope guard:** do NOT touch `step()`, `_rebuild_cholesky()`, `start()`, `stop()`, `add_ticker()`, `remove_ticker()`, `get_tickers()`. Only `__init__`, `_run_loop`, and the new `register_tick_observer` change.

---

### `backend/app/market/massive_client.py` (MODIFIED, observer-firing poll)

**Analog:** The existing file itself (self-precedent).

**Precise insertion points:**

1. **`__init__`** (currently `massive_client.py:28-39`) — add `self._observers: list[Callable[[], None]] = []`.

2. **`_poll_once`** — currently `massive_client.py:89-121`, critical section:

```python
async def _poll_once(self) -> None:
    """Execute one poll cycle: fetch snapshots, update cache."""
    if not self._tickers or not self._client:
        return

    try:
        snapshots = await asyncio.to_thread(self._fetch_snapshots)
        processed = 0
        for snap in snapshots:
            try:
                price = snap.last_trade.price
                timestamp = snap.last_trade.timestamp / 1000.0
                self._cache.update(
                    ticker=snap.ticker, price=price, timestamp=timestamp,
                )
                processed += 1
            except (AttributeError, TypeError) as e:
                logger.warning("Skipping snapshot for %s: %s", ..., e)
        logger.debug("Massive poll: updated %d/%d tickers", processed, len(self._tickers))
    except Exception as e:
        logger.error("Massive poll failed: %s", e)
```

Insert observer firing AFTER the `for snap in snapshots:` loop and the debug log, but BEFORE `except Exception:` (so observers only fire on a successful poll, NOT on a failed one). Same nested-try-per-callback pattern as `simulator.py`:

```python
        logger.debug("Massive poll: updated %d/%d tickers", processed, len(self._tickers))
        for cb in self._observers:
            try:
                cb()
            except Exception:
                logger.exception("Tick observer raised")
    except Exception as e:
        logger.error("Massive poll failed: %s", e)
```

3. **New method** below `_fetch_snapshots`:

```python
def register_tick_observer(self, callback: Callable[[], None]) -> None:
    self._observers.append(callback)
```

**Thread safety:** Pitfall 2 (03-RESEARCH.md lines 320-324) confirms observer invocation happens on the asyncio event loop thread — only `_fetch_snapshots` runs via `asyncio.to_thread`, and the code after `await asyncio.to_thread(...)` is back on the loop. The snapshot observer writes to SQLite from the event loop thread; `check_same_thread=False` still suppresses any thread check but we do not rely on it.

---

### `backend/app/lifespan.py` (MODIFIED, startup wiring)

**Analog:** The existing file itself (self-precedent).

**Current full lifespan body** (from `backend/app/lifespan.py:37-65`):

```python
    if not os.environ.get("OPENROUTER_API_KEY"):
        logger.warning("OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5")

    db_path = os.environ.get("DB_PATH", "db/finally.db")
    conn = open_database(db_path)
    init_database(conn)
    seed_defaults(conn)

    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = get_watchlist_tickers(conn)
    await source.start(tickers)

    app.state.db = conn
    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))

    logger.info("App started: db=%s tickers=%d source=%s", ...)
    try:
        yield
    finally:
        await source.stop()
        conn.close()
        logger.info("App stopped")
```

**Exact insertion points** (per 03-RESEARCH.md lines 692-705):

1. **Imports (top of file):** add to the `.portfolio` line — currently the file only imports from `.db` and `.market`. Add:
   ```python
   from .portfolio import create_portfolio_router, make_snapshot_observer
   ```

2. **After `await source.start(tickers)` and BEFORE `app.include_router(create_stream_router(cache))`** (the current mount point at line 52):
   ```python
   app.state.db = conn
   app.state.price_cache = cache
   app.state.market_source = source
   app.state.last_snapshot_at = 0.0                                   # D-06, new
   source.register_tick_observer(make_snapshot_observer(app.state))   # D-05, new
   app.include_router(create_stream_router(cache))
   app.include_router(create_portfolio_router(conn, cache))           # new
   ```

3. **`finally:` block** — no changes (observer is dropped when `source.stop()` is awaited; no explicit deregistration needed).

**What to replicate:**
- `app.state.*` assignment style — direct attribute set, no wrapper (Phase 1 D-02 precedent).
- Factory-closure on the same line as the `include_router`, closes over `conn` and `cache`.
- `make_snapshot_observer(app.state)` — the observer factory closes over the whole `app.state` namespace (so it can both read and write `last_snapshot_at`).

**What's new:** three additions (router mount, observer registration, `last_snapshot_at` init). No other behaviour change.

---

### `backend/tests/portfolio/test_service.py` (NEW, service unit tests)

**Analog:** `backend/tests/db/test_seed.py`

**Full harness excerpt to replicate** (from `backend/tests/db/test_seed.py:1-31`):

```python
"""Tests for default seed: users_profile + 10-ticker watchlist (DB-02)."""

import sqlite3

from app.db import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    get_watchlist_tickers,
    init_database,
    seed_defaults,
)
from app.market.seed_prices import SEED_PRICES


class TestSeed:
    """Unit tests for seed_defaults + get_watchlist_tickers."""

    def _fresh(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_database(conn)
        return conn

    def test_fresh_db_gets_seeded(self):
        conn = self._fresh()
        seed_defaults(conn)
        ...
```

**What to replicate exactly:**
- Class-grouped tests (`class TestTradeExecution`, `class TestPortfolioValuation`, `class TestHistory`).
- `_fresh()` helper that opens `:memory:`, sets `row_factory = sqlite3.Row`, and runs `init_database(conn)` + `seed_defaults(conn)`. Phase 3 version also pre-warms a `PriceCache` with one `cache.update(ticker, price)` call per seed ticker (03-RESEARCH.md §Claude's Discretion: "cache-warming fixture for trade tests").
- One behaviour per `test_*` method.
- Imports from `app.portfolio import execute_trade, get_portfolio, ...` and `from app.portfolio.service import InsufficientCash, ...` — use the package facade for public surface.

**What's new:** trade-validation tests (rejects insufficient cash, rejects insufficient shares, rejects unknown ticker, rejects missing cached price), trade-write tests (updates cash, upserts position, deletes on zero, appends trade row, inserts snapshot, commits once), valuation tests (fallback to avg_cost when cache miss), history tests (ORDER BY recorded_at ASC, limit parameter).

---

### `backend/tests/portfolio/test_routes.py` (NEW, HTTP integration tests)

**Analog:** `backend/tests/test_main.py::TestHealth`

**Full harness excerpt to replicate** (from `backend/tests/test_main.py:42-107`):

```python
import httpx
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    test_app = FastAPI(lifespan=lifespan)
    @test_app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}
    return test_app


@pytest.mark.asyncio
class TestHealth:
    async def test_health_returns_ok(self, db_path):
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
```

**What to replicate exactly:**
- `_build_app()` helper returns `FastAPI(lifespan=lifespan)` — fresh app per test (the module docstring explains why).
- `@pytest.mark.asyncio class TestPortfolioRoutes:` test class (project convention).
- `db_path` fixture from `backend/tests/conftest.py:14-26` — each test gets a fresh SQLite file under `tmp_path`.
- `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` — critical: `clear=True` wipes env, `DB_PATH` must be re-inserted.
- `LifespanManager(app)` wraps the block so `app.state.db`, `app.state.price_cache`, `app.state.market_source`, AND `app.state.last_snapshot_at` are populated before the request.
- `ASGITransport(app=app)` + `AsyncClient(transport=transport, base_url="http://test")` — Phase 3 endpoints all return bounded JSON so `ASGITransport` works (Pitfall 9 explicitly says no uvicorn harness needed for Phase 3).

**What's new:** tests for GET `/api/portfolio`, POST `/api/portfolio/trade` (happy + 400s + 422 for extra keys), GET `/api/portfolio/history`. All use the same harness.

---

### `backend/tests/portfolio/test_observer.py` (NEW, tick-observer tests)

**Analog:** `backend/tests/market/test_simulator_source.py` + `backend/tests/market/test_massive.py`

**Simulator test harness** (from `backend/tests/market/test_simulator_source.py:11-40`):

```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    async def test_prices_update_over_time(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.05)
        await source.start(["AAPL"])

        initial_version = cache.version
        await asyncio.sleep(0.3)
        assert cache.version > initial_version

        await source.stop()
```

**Massive mock harness** (from `backend/tests/market/test_massive.py:22-45`):

```python
@pytest.mark.asyncio
class TestMassiveDataSource:
    async def test_poll_updates_cache(self):
        cache = PriceCache()
        source = MassiveDataSource(api_key="test-key", price_cache=cache, poll_interval=60.0)
        source._tickers = ["AAPL", "GOOGL"]
        source._client = MagicMock()

        with patch.object(source, "_fetch_snapshots", return_value=mock_snapshots):
            await source._poll_once()

        assert cache.get_price("AAPL") == 190.50
```

**What to replicate exactly:**
- `@pytest.mark.asyncio` at the class level; `asyncio_mode = "auto"` in `pyproject.toml` makes this redundant but the existing tests keep it for clarity.
- Short `update_interval=0.05` (50ms) to accelerate tick-loop tests; `asyncio.sleep(0.3)` is enough for several cycles.
- Private-attribute injection is fine in tests (`source._tickers = [...]`, `source._client = MagicMock()`) — established convention in `test_massive.py:33, 34`.
- `await source.stop()` at end of every test that called `start()`.

**What's new:**
- `test_observer_fires_on_tick` — register a counter-incrementing callback, start the simulator, assert the counter grows.
- `test_observer_exception_does_not_kill_loop` — register a callback that raises, assert the price-cache version still advances (D-08).
- `test_multiple_observers_all_fire` — register two callbacks, assert both counters grow.
- `test_snapshot_observer_writes_every_60s` — unit test `make_snapshot_observer(state)` directly by constructing a fake `state` with `db`, `price_cache`, `last_snapshot_at = 0.0`. Call the observer once (first tick → snapshot writes because `now - 0.0 >> 60`). Call again immediately (no write). Mutate `state.last_snapshot_at = 0.0` and call again (write). Pitfall 5 explicitly marks the boot snapshot as a feature.

---

### `backend/tests/test_lifespan.py` (MODIFIED, lifespan additions)

**Analog:** the existing file itself (self-precedent, shown in full above).

**New test cases (within the existing `class TestLifespan:`):**
- `test_last_snapshot_at_initialised_to_zero_on_startup` — `assert app.state.last_snapshot_at == 0.0`.
- `test_portfolio_router_mounted` — `assert "/api/portfolio" in paths` (pattern: the existing `test_includes_sse_router_during_startup` at lines 66-73).
- `test_tick_observer_registered` — `assert len(source._observers) >= 1` (or equivalent).

**What to replicate:** the exact `_build_app()` + `patch.dict(..., clear=True)` + `LifespanManager(app)` harness already in this file. No new imports.

---

## Shared Patterns (apply across multiple files)

### Module header

**Source:** every module in the repo (e.g., `backend/app/db/seed.py:1-5`)
**Apply to:** every new `.py` file in `backend/app/portfolio/` and `backend/tests/portfolio/`.

```python
"""One-line module docstring summarising the role."""

from __future__ import annotations

import logging
...

logger = logging.getLogger(__name__)
```

### Narrow exception handling at loop boundaries

**Source:** `backend/app/market/simulator.py:263-269` + `backend/app/market/massive_client.py:94-121`
**Apply to:** the two observer-firing sites (`simulator._run_loop`, `massive._poll_once`) and anywhere in `service.py` that catches an exception.

```python
try:
    cb()
except Exception:
    logger.exception("Tick observer raised")
```

Rule: catch at the boundary, log with `%`-style, do NOT re-raise. No broad `except:` silent swallow; every catch has a `logger.{warning,error,exception}(...)` call.

### Logging convention

**Source:** `backend/app/market/simulator.py:230` — `logger.info("Simulator started with %d tickers", len(tickers))`
**Apply to:** every log call in every new file.

- `%`-style ONLY. Never f-strings in log calls (lazy formatting; ruff flags f-strings in stricter configs; CLAUDE.md anti-pattern list explicit).
- No emojis. No `print()`.
- Levels: `DEBUG` for tick-level trace, `INFO` for state changes ("Trade executed ..."), `WARNING` for degraded-state conditions, `ERROR` for failed operations that keep running, `EXCEPTION` (via `logger.exception`) when re-logging a caught exception.

### SQLite idioms

**Source:** `backend/app/db/seed.py` + `backend/app/db/connection.py:20-24`
**Apply to:** `backend/app/portfolio/service.py` and the snapshot observer.

- Connection opens once at lifespan entry (`open_database`), `sqlite3.Row` row factory, `check_same_thread=False`, default isolation.
- Parameterised queries with `?` placeholders.
- `str(uuid.uuid4())` for primary keys at the INSERT site.
- `datetime.now(UTC).isoformat()` for `*_at` columns.
- Explicit `conn.commit()` at end of each write path; never inside a read path; never nested.
- NO `conn.execute("BEGIN")` — rely on stdlib implicit-transaction-on-first-write (Pitfall 8, 03-RESEARCH.md lines 355-358).

### Pydantic v2 idioms

**Source:** 03-RESEARCH.md §Pattern 3 + §Code Examples (verified in-session against 2.12.5)
**Apply to:** `backend/app/portfolio/models.py` exclusively.

- `model_config = ConfigDict(extra="forbid")` on REQUEST models only.
- `Literal["buy", "sell"]` for enums.
- `Field(gt=0, min_length=1)` for constraints.
- `model_dump()`, `model_dump_json()`, `model_validate()` — NEVER the v1 names `dict`, `json`, `parse_obj`, `parse_raw`, or a `class Config` inner class (Pitfall 7).
- PEP-604 types everywhere: `list[PositionOut]`, `int | None`, `float | None`.

### Test harness idioms

**Source:** `backend/tests/conftest.py` + `backend/tests/test_main.py` + `backend/tests/test_lifespan.py`
**Apply to:** every new test file in `backend/tests/portfolio/`.

- `db_path` fixture from `conftest.py` — each test gets a fresh sqlite file at `tmp_path / "finally.db"` and env var `DB_PATH` monkey-patched.
- `patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True)` — `clear=True` wipes everything; the `DB_PATH` entry is what keeps the lifespan pointed at the temp file.
- `_build_app()` helper that returns `FastAPI(lifespan=lifespan)` — fresh app per test.
- `LifespanManager(app)` wraps the block for integration tests that need `app.state` populated.
- `ASGITransport` + `AsyncClient` for bounded JSON endpoints. Real uvicorn harness is ONLY for SSE (Phase 3 does not need it; Pitfall 9).
- `@pytest.mark.asyncio class TestX:` — class-level marker (project convention; `asyncio_mode = "auto"` in `pyproject.toml` would make it redundant but the repo style keeps it).

---

## No Analog Found

None. Every production file and every test file in Phase 3 has a strong, concrete analog in the already-shipped Phase 1 + Phase 2 code.

---

## Metadata

**Analog search scope:** `backend/app/` (market, db, lifespan, main) + `backend/tests/` (conftest, test_main, test_lifespan, market/, db/).
**Files read:** 13 source/test files + CONTEXT.md + RESEARCH.md (targeted ranges only).
**Pattern extraction date:** 2026-04-20.
**No production files were modified.** Only this PATTERNS.md was written.
