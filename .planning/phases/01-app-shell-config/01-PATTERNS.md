# Phase 1: App Shell & Config - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 5 (3 source + 2 test)
**Analogs found:** 5 / 5
**Source root:** `backend/`

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `backend/app/main.py` | entrypoint / app factory | request-response | `backend/app/market/stream.py` (factory router) + `backend/market_data_demo.py` (lifecycle script) | role-match (no existing FastAPI app yet) |
| `backend/app/lifespan.py` | startup/shutdown context | lifecycle / event-driven | `backend/market_data_demo.py` `run()` (cache + source.start/stop) | role-match |
| `backend/app/config.py` (Claude's Discretion) | config / env loader | config | `backend/app/market/factory.py` (env-driven factory) | role-match |
| `backend/tests/test_main.py` | test (HTTP / lifespan) | request-response | `backend/tests/market/test_simulator_source.py` (async lifecycle) + `backend/tests/market/test_factory.py` (env patching) | role-match |
| `backend/tests/test_lifespan.py` | test (async lifecycle) | lifecycle | `backend/tests/market/test_simulator_source.py` | exact |

## Pattern Assignments

### `backend/app/main.py` (entrypoint, request-response)

**Analog:** `backend/app/market/stream.py` (FastAPI idioms) + `backend/market_data_demo.py` (top-of-file conventions)

**Imports pattern** (from `stream.py:1-13`):
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
```

Apply for `main.py`:
- One-line module docstring first
- `from __future__ import annotations`
- `import logging` and `logger = logging.getLogger(__name__)`
- Stdlib → third-party → local import grouping
- Local imports use relative form: `from .lifespan import lifespan`

**FastAPI app construction** (no existing analog — derive from PLAN.md §3 + `stream.py:17-48`):
```python
# In stream.py the router takes a closure over PriceCache:
router = APIRouter(prefix="/api/stream", tags=["streaming"])

def create_stream_router(price_cache: PriceCache) -> APIRouter:
    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        ...
    return router
```

In `main.py`:
- Build a single module-level `app = FastAPI(lifespan=lifespan)`
- Define `/api/health` inline as `@app.get("/api/health")` returning `{"status": "ok"}` (D-04)
- Do NOT mount the SSE router here — it's attached during lifespan startup once the cache exists (D-02, D-04)
- No `if __name__ == "__main__":` block (D-03 — uvicorn invoked via CLI only)

**Logging pattern** (from `factory.py:13`, `simulator.py:25`, used everywhere):
```python
logger = logging.getLogger(__name__)
# ...
logger.info("Market data source: GBM Simulator")           # %-style, no f-strings
logger.info("Simulator started with %d tickers", len(tickers))
```

Apply: never f-strings in logging calls; always `%`-placeholders with positional args.

---

### `backend/app/lifespan.py` (lifecycle, event-driven)

**Analog:** `backend/market_data_demo.py` `run()` (lines 207-266) — only existing example of "build cache, build source, start, do work, stop" sequencing.

**Module header pattern** (from `simulator.py:1-25`):
```python
"""GBM-based market simulator."""

from __future__ import annotations

import asyncio
import logging
...

from .cache import PriceCache
from .interface import MarketDataSource
...

logger = logging.getLogger(__name__)
```

Apply identically for `lifespan.py`:
```python
"""FastAPI lifespan: PriceCache + market data source startup/shutdown."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .market import PriceCache, create_market_data_source, create_stream_router
from .market.seed_prices import SEED_PRICES

logger = logging.getLogger(__name__)
```

Note: import the public surface from `app.market` (per `backend/CLAUDE.md` "Market Data API"), not deep paths. `SEED_PRICES` is the one exception — it isn't re-exported from `app.market.__init__`, so `from .market.seed_prices import SEED_PRICES` is correct.

**Start/stop sequencing pattern** (from `market_data_demo.py:208-266`):
```python
cache = PriceCache()
source = SimulatorDataSource(price_cache=cache, update_interval=0.5)

await source.start(TICKERS)
start_time = time.time()
# ... run ...
try:
    # ... main loop ...
finally:
    await source.stop()
```

Apply in `lifespan.py` — same order, same `try/finally` shape, but as `@asynccontextmanager`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build PriceCache, start the market data source, mount SSE router.

    Cache and source are attached to app.state so handlers can reach them
    via dependency injection or request.app.state. No module-level globals
    (matches the create_stream_router factory-closure pattern).
    """
    cache = PriceCache()
    source = create_market_data_source(cache)

    tickers = list(SEED_PRICES.keys())  # single source of truth (Claude's Discretion)
    await source.start(tickers)

    app.state.price_cache = cache
    app.state.market_source = source
    app.include_router(create_stream_router(cache))

    logger.info("App started: %d tickers, source=%s", len(tickers), type(source).__name__)
    try:
        yield
    finally:
        await source.stop()
        logger.info("App stopped")
```

**Async lifecycle ownership pattern** (from `simulator.py:219-240`):
```python
async def start(self, tickers: list[str]) -> None:
    self._sim = GBMSimulator(...)
    # Seed the cache with initial prices so SSE has data immediately
    for ticker in tickers:
        ...
        self._cache.update(ticker=ticker, price=price)
    self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
    logger.info("Simulator started with %d tickers", len(tickers))

async def stop(self) -> None:
    if self._task and not self._task.done():
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
    self._task = None
    logger.info("Simulator stopped")
```

Apply: lifespan does NOT manage tasks itself — it just calls `source.start()` / `source.stop()` and lets the source own its `asyncio.Task`. Keep lifespan thin.

**Error handling — narrow only at boundaries** (from `simulator.py:262-270`):
```python
async def _run_loop(self) -> None:
    while True:
        try:
            if self._sim:
                ...
        except Exception:
            logger.exception("Simulator step failed")
        await asyncio.sleep(self._interval)
```

Apply: do NOT wrap `source.start()` in try/except in lifespan. If startup fails, FastAPI should fail loud — that's correct per project rule "no defensive programming." Internal background loops handle their own resilience.

---

### `backend/app/config.py` (config, env-driven) — Claude's Discretion

**Analog:** `backend/app/market/factory.py` (only existing example of env-driven config in this codebase).

**Env-read pattern** (from `factory.py:14-31`):
```python
"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Create the appropriate market data source based on environment variables.

    - MASSIVE_API_KEY set and non-empty → MassiveDataSource (real market data)
    - Otherwise → SimulatorDataSource (GBM simulation)
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()

    if api_key:
        logger.info("Market data source: Massive API (real data)")
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        logger.info("Market data source: GBM Simulator")
        return SimulatorDataSource(price_cache=price_cache)
```

Apply for `config.py`:
- Use stdlib `os.environ.get(NAME, default)` — same pattern factory already uses, no new dependency required
- Project does NOT currently depend on `python-dotenv` or `pydantic-settings` (verified: `dotenv` only appears in `uv.lock` as a transitive dep)
- Recommended: add `python-dotenv` via `uv add python-dotenv` — load `.env` from repo root once at app import (or lifespan startup) with `load_dotenv()`. Missing file is silent — matches CONTEXT.md hard constraint (a) "missing values must not crash startup"
- Single warning log if `OPENROUTER_API_KEY` is absent (CONTEXT.md missing-env policy):
  ```python
  if not os.environ.get("OPENROUTER_API_KEY"):
      logger.warning("OPENROUTER_API_KEY not set; chat endpoint will fail in Phase 5")
  ```
- Do NOT pre-validate `MASSIVE_API_KEY` here — `factory.create_market_data_source` already does the right thing on absent/empty/whitespace values (see `test_factory.py:24-40`)

**Where to call `load_dotenv()`:** at the top of `main.py` BEFORE `app = FastAPI(...)`, so env vars are present by the time `lifespan` runs and `factory.create_market_data_source` reads `MASSIVE_API_KEY`. Single call site, no globals, no ceremony.

---

### `backend/tests/test_main.py` (test, request-response)

**Analog:** `backend/tests/market/test_factory.py` (env patching) + `backend/tests/market/test_simulator_source.py` (async lifecycle).

**Class-grouped test pattern** (from `test_factory.py:12-21`):
```python
"""Tests for market data source factory."""

import os
from unittest.mock import patch

from app.market.cache import PriceCache
from app.market.factory import create_market_data_source
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource


class TestFactory:
    """Tests for create_market_data_source factory."""

    def test_creates_simulator_when_no_api_key(self):
        """Test that simulator is created when MASSIVE_API_KEY is not set."""
        cache = PriceCache()

        with patch.dict(os.environ, {}, clear=True):
            source = create_market_data_source(cache)

        assert isinstance(source, SimulatorDataSource)
```

Apply for `test_main.py`:
- One class per logical unit: `class TestHealth`, `class TestSSEStream`
- One behavior per `test_*` method, with a docstring stating the behavior
- Test imports use deep paths (`from app.main import app`) — matches existing convention in `test_factory.py:6-9`
- For env-dependent tests use `with patch.dict(os.environ, {...}, clear=True):` — exact pattern from `test_factory.py:19, 28, 37, 46, 55`

**HTTP test pattern** (no existing analog — `httpx.AsyncClient` is the FastAPI-recommended client as of FastAPI ≥ 0.115). Suggested shape, mirroring the async + class structure of `test_simulator_source.py`:
```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
class TestHealth:
    """Tests for GET /api/health."""

    async def test_health_returns_ok(self):
        """Health endpoint returns {'status': 'ok'} with 200."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
```

Note: `httpx` is not currently in `pyproject.toml` — planner should add via `uv add --dev httpx` (or rely on it being a transitive dep of `fastapi`/`starlette` via TestClient; prefer explicit). FastAPI's `TestClient` (sync, from `fastapi.testclient`) is also valid and requires no new dep — pick whichever the planner prefers; both are idiomatic.

**SSE smoke test pattern** (CONTEXT.md "Claude's Discretion" calls for "at least one `data:` frame arrives"). Use `AsyncClient.stream(...)` against the lifespan-mounted app. The app must be entered via `LifespanManager` (from `asgi-lifespan`) or via httpx's lifespan support so that `lifespan` actually runs and the SSE router gets mounted. Concrete test follows the "wait until version increments" pattern from `test_simulator_source.py:27-39`:
```python
async def test_sse_emits_at_least_one_frame(self):
    """Real EventSource-equivalent receives at least one data: frame."""
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            async with client.stream("GET", "/api/stream/prices", timeout=5.0) as resp:
                assert resp.status_code == 200
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        return
            pytest.fail("no data: frame within timeout")
```

Add `asgi-lifespan` via `uv add --dev asgi-lifespan` if needed. (The planner may instead use FastAPI's built-in `TestClient`, which runs the lifespan automatically via its `__enter__`.)

---

### `backend/tests/test_lifespan.py` (test, async lifecycle)

**Analog:** `backend/tests/market/test_simulator_source.py` — exact match for "build cache, await start, assert state, await stop" sequencing.

**Class-level async marker + lifecycle assertions** (from `test_simulator_source.py:11-39`):
```python
"""Integration tests for SimulatorDataSource."""

import asyncio

import pytest

from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource


@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for the SimulatorDataSource."""

    async def test_start_populates_cache(self):
        """Test that start() immediately populates the cache."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])

        # Cache should have seed prices immediately (before first loop tick)
        assert cache.get("AAPL") is not None
        assert cache.get("GOOGL") is not None

        await source.stop()
```

Apply for `test_lifespan.py`:
- `@pytest.mark.asyncio` at the class level — one decorator covers all methods
- One behavior per test
- Suggested coverage:
  - `test_lifespan_attaches_cache_to_app_state` — enter lifespan, assert `app.state.price_cache is not None` and is a `PriceCache`
  - `test_lifespan_starts_default_tickers` — assert `app.state.market_source.get_tickers()` matches `SEED_PRICES.keys()`
  - `test_lifespan_seeds_cache_immediately` — assert `cache.get("AAPL") is not None` immediately after enter (mirrors `test_start_populates_cache`)
  - `test_lifespan_stops_source_on_exit` — exit lifespan, assert source `_task` is None or done

**Direct-attribute access for assertions** (from `test_simulator_source.py:108-109`):
```python
# Task should still be running
assert source._task is not None
assert not source._task.done()
```

Acceptable pattern in this codebase — tests reach into private attributes when it sharpens the assertion. Use sparingly, as the existing tests do.

---

## Shared Patterns

### Module Header
**Source:** Every module in `backend/app/market/`
**Apply to:** All new modules in this phase
```python
"""<one-line module summary>."""

from __future__ import annotations

import logging
...

logger = logging.getLogger(__name__)
```

### Logging (`%`-style, never f-strings)
**Source:** `backend/app/market/factory.py:27`, `simulator.py:230`, `massive_client.py:49-53`
**Apply to:** All new code (main, lifespan, config)
```python
logger.info("Market data source: GBM Simulator")
logger.info("Simulator started with %d tickers", len(tickers))
logger.info(
    "Massive poller started: %d tickers, %.1fs interval",
    len(tickers),
    self._interval,
)
```
Anti-patterns to avoid (from `.planning/codebase/CONVENTIONS.md` "Anti-patterns"):
- f-strings in logging calls (breaks lazy formatting)
- Emojis anywhere in code, prints, or logs
- `print()` for diagnostics — always `logging`

### Factory-closure (no module globals for shared state)
**Source:** `backend/app/market/stream.py:20-48`
**Apply to:** `lifespan.py` — calls `create_stream_router(cache)` and passes the result to `app.include_router(...)`. The same closure pattern: shared dependency injected via constructor/factory, never via module globals.

### Narrow exception handling at boundaries only
**Source:** `backend/app/market/massive_client.py:94-121` (network), `simulator.py:262-270` (background loop)
**Apply to:** `lifespan.py` (none needed — startup must fail loud), `config.py` (none needed — missing env vars are not exceptional). Internal code trusts invariants.

### Public-API imports
**Source:** `backend/CLAUDE.md` "Market Data API"
**Apply to:** `lifespan.py`, `main.py`
```python
# Good:
from .market import PriceCache, create_market_data_source, create_stream_router

# Bad — deep imports of public surface:
from .market.cache import PriceCache
from .market.factory import create_market_data_source
```
Exception: `SEED_PRICES` is not re-exported from `app.market.__init__.py` (verified at `backend/app/market/__init__.py:11-15`) — deep import is correct: `from .market.seed_prices import SEED_PRICES`.

### Test discovery & async config
**Source:** `backend/pyproject.toml:30-36`
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```
Already configured. New tests under `backend/tests/` (not `backend/tests/market/`) will be picked up automatically. `asyncio_mode = "auto"` means `@pytest.mark.asyncio` on classes is the convention used today; keep using it explicitly for clarity.

---

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `backend/app/main.py` (the FastAPI app instance + `lifespan=` wiring) | entrypoint | request-response | No FastAPI app exists in repo today | Follow PLAN.md §3 + FastAPI ≥ 0.115 stdlib pattern: `app = FastAPI(lifespan=lifespan)`, inline `@app.get("/api/health")`. Match `stream.py` for imports/typing/logging style. |
| HTTP test client usage | test | request-response | No existing tests hit FastAPI endpoints | Use either `fastapi.testclient.TestClient` (sync, no new dep) or `httpx.AsyncClient` + `ASGITransport` (async, needs `uv add --dev httpx` and possibly `asgi-lifespan`). FastAPI's official docs (latest API as of cutoff) recommend either; planner picks. |

---

## Metadata

**Analog search scope:**
- `backend/app/__init__.py`
- `backend/app/market/*.py` (all 9 modules)
- `backend/market_data_demo.py`
- `backend/tests/conftest.py`
- `backend/tests/market/*.py` (all 6 test modules)
- `backend/pyproject.toml`
- `backend/CLAUDE.md`

**Files scanned:** 18
**New deps the planner may need to add:**
- `python-dotenv` (recommended, runtime)
- `httpx` (test, possibly already transitive — add explicitly)
- `asgi-lifespan` (test, only if using `httpx.AsyncClient` + needing real lifespan)

**Pattern extraction date:** 2026-04-19
