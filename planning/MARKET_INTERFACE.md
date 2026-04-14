# Market Data Interface

A single Python interface that the rest of FinAlly talks to for prices. Two
implementations sit behind it:

- `MassiveMarketData` — polls the Massive REST API. Used when
  `MASSIVE_API_KEY` is set and non-empty.
- `SimulatorMarketData` — in-process GBM simulator. Used otherwise. See
  `MARKET_SIMULATOR.md`.

Upstream code (SSE streamer, portfolio valuation, chat context) only imports
the interface and the price cache — never a concrete implementation.

## Module layout

```
backend/app/market/
├── __init__.py           # get_market_data() factory
├── types.py              # PriceTick, PriceCacheEntry dataclasses
├── base.py               # MarketData abstract base class
├── cache.py              # PriceCache (in-memory, thread-safe)
├── massive.py            # MassiveMarketData
└── simulator.py          # SimulatorMarketData
```

## Core types

```python
# backend/app/market/types.py
from dataclasses import dataclass

@dataclass(frozen=True)
class PriceTick:
    ticker: str
    price: float
    previous_price: float         # price on the prior tick (for flash direction)
    session_start_price: float    # first price seen this process lifetime
    timestamp_ms: int             # unix ms
```

`PriceCacheEntry` is the same shape, stored per-ticker in the cache.

## The interface

```python
# backend/app/market/base.py
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from .types import PriceTick

class MarketData(ABC):
    """Source-agnostic price feed. One instance per process."""

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing ticks for the given tickers. Idempotent."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the background task. Idempotent."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Begin tracking a new ticker. Seeds it on the next tick."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker."""

    @abstractmethod
    def ticks(self) -> AsyncIterator[PriceTick]:
        """Async iterator yielding every tick produced by this source."""
```

Both implementations write every tick into the shared `PriceCache` so SSE
consumers read from one place regardless of source.

## Factory

```python
# backend/app/market/__init__.py
import os
from .base import MarketData
from .massive import MassiveMarketData
from .simulator import SimulatorMarketData
from .cache import PriceCache

_cache = PriceCache()

def get_price_cache() -> PriceCache:
    return _cache

def get_market_data() -> MarketData:
    key = os.getenv("MASSIVE_API_KEY", "").strip()
    if key:
        return MassiveMarketData(api_key=key, cache=_cache)
    return SimulatorMarketData(cache=_cache)
```

Call once from FastAPI `lifespan`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    md = get_market_data()
    app.state.market = md
    tickers = [row["ticker"] for row in db.list_watchlist()]
    await md.start(tickers)
    try:
        yield
    finally:
        await md.stop()
```

## Price cache

The cache is the single source of truth for "what is the latest price of X".

```python
# backend/app/market/cache.py
import asyncio, time
from .types import PriceTick

class PriceCache:
    def __init__(self) -> None:
        self._data: dict[str, PriceTick] = {}
        self._subscribers: set[asyncio.Queue[PriceTick]] = set()
        self._lock = asyncio.Lock()

    async def update(self, ticker: str, price: float) -> PriceTick:
        async with self._lock:
            prev = self._data.get(ticker)
            tick = PriceTick(
                ticker=ticker,
                price=price,
                previous_price=prev.price if prev else price,
                session_start_price=prev.session_start_price if prev else price,
                timestamp_ms=int(time.time() * 1000),
            )
            self._data[ticker] = tick
        for q in list(self._subscribers):
            q.put_nowait(tick)
        return tick

    def get(self, ticker: str) -> PriceTick | None:
        return self._data.get(ticker)

    def snapshot(self) -> dict[str, PriceTick]:
        return dict(self._data)

    def subscribe(self) -> asyncio.Queue[PriceTick]:
        q: asyncio.Queue[PriceTick] = asyncio.Queue(maxsize=1000)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[PriceTick]) -> None:
        self._subscribers.discard(q)
```

The SSE endpoint subscribes, drains the queue, and pushes events. The
`/api/portfolio` handler reads via `snapshot()`.

## Massive implementation (sketch)

```python
# backend/app/market/massive.py
import asyncio, httpx
from .base import MarketData
from .cache import PriceCache

POLL_INTERVAL_S = 15.0  # free tier: 5 calls/min

class MassiveMarketData(MarketData):
    def __init__(self, api_key: str, cache: PriceCache) -> None:
        self._key = api_key
        self._cache = cache
        self._tickers: set[str] = set()
        self._task: asyncio.Task | None = None
        self._client = httpx.AsyncClient(
            base_url="https://api.massive.com", timeout=10.0
        )

    async def start(self, tickers: list[str]) -> None:
        self._tickers.update(tickers)
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
        await self._client.aclose()

    async def add_ticker(self, ticker: str) -> None:
        self._tickers.add(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        self._tickers.discard(ticker)

    async def _run(self) -> None:
        backoff = POLL_INTERVAL_S
        while True:
            try:
                await self._poll_once()
                backoff = POLL_INTERVAL_S
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    backoff = min(backoff * 2, 120)
            except Exception:
                pass  # log in real code; reuse cached prices
            await asyncio.sleep(backoff)

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        r = await self._client.get(
            "/v2/snapshot/locale/us/markets/stocks/tickers",
            params={"tickers": ",".join(sorted(self._tickers)),
                    "apiKey": self._key},
        )
        r.raise_for_status()
        for t in r.json().get("tickers", []):
            price = self._extract_price(t)
            if price is not None:
                await self._cache.update(t["ticker"], price)

    @staticmethod
    def _extract_price(t: dict) -> float | None:
        last = (t.get("lastTrade") or {}).get("p")
        if last: return last
        minute = (t.get("min") or {}).get("c")
        if minute: return minute
        day = (t.get("day") or {}).get("c")
        return day
```

## Ticks async iterator

Both implementations expose `ticks()` by subscribing to the cache:

```python
async def ticks(self) -> AsyncIterator[PriceTick]:
    q = self._cache.subscribe()
    try:
        while True:
            yield await q.get()
    finally:
        self._cache.unsubscribe(q)
```

## Watchlist add/remove integration

The watchlist API handler calls `market.add_ticker(...)` /
`market.remove_ticker(...)` after the DB write. New tickers appear in the
SSE stream on the next poll/tick.

## Why this shape

- One cache, one subscribe mechanism — SSE code is source-agnostic.
- No CORS, no websockets, no shared global state beyond the cache.
- Switching implementations is a function of one env var; no code changes.
- The interface is small enough to test with a trivial fake.
