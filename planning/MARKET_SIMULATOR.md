# Market Simulator

The simulator is the default price source when `MASSIVE_API_KEY` is unset.
It produces plausible, live-looking price ticks entirely in-process — no
network, no API key, fully deterministic when seeded.

It implements the `MarketData` interface from `MARKET_INTERFACE.md` and
writes to the same `PriceCache`, so downstream code cannot tell the
difference.

## Goals

1. Look real: prices wobble with realistic drift/volatility per ticker.
2. Be correlated: tech names broadly move together (for demo drama).
3. Be dramatic: occasional 2–5 % "events" so the UI has something to flash.
4. Be cheap: one asyncio task, ~500 ms cadence, O(N) per tick.
5. Onboard tickers dynamically: adding a ticker to the watchlist seeds a
   price and starts generating the next tick — no restart.

## Price model: geometric Brownian motion

For each ticker, each tick:

```
dt         = 0.5 s / (252 * 6.5 * 3600)       # half-second as fraction of a trading year
shock      = mu*dt + sigma*sqrt(dt) * (rho*Z_market + sqrt(1-rho^2)*Z_ticker)
price     *= exp(shock)
```

- `mu` (annual drift): small, per-ticker (e.g. 0.08 for blue chips, 0.20 for
  NVDA, -0.05 for laggards).
- `sigma` (annual volatility): 0.15 – 0.60 per-ticker.
- `Z_market`, `Z_ticker`: independent standard normals. `Z_market` is shared
  across all tickers each tick — this is what produces correlation.
- `rho`: per-ticker correlation to the market factor (0.3 – 0.8). Tech names
  share a higher `rho`; `JPM`/`V` get a separate factor with lower `rho`.

Event injection: on every tick, with probability `p_event = 1/600` (roughly
one event every 5 min at 500 ms cadence), pick a random tracked ticker and
multiply its price by `1 + uniform(-0.05, 0.05)` (biased small). The event
fires once; the next tick resumes normal GBM from the new price.

## Seed prices

A small dict of realistic defaults covers the initial watchlist:

```python
SEED_PRICES = {
    "AAPL": 190.0, "GOOGL": 175.0, "MSFT": 425.0, "AMZN": 185.0,
    "TSLA": 240.0, "NVDA": 880.0, "META": 495.0, "JPM": 195.0,
    "V":    275.0, "NFLX": 620.0,
}
FALLBACK_PRICE = 100.0
```

Unknown tickers seeded on add use `FALLBACK_PRICE` with a generic profile
(`mu=0.05`, `sigma=0.25`, `rho=0.5`, tech factor).

## Code structure

```
backend/app/market/simulator.py
```

Single module, three classes:

### `TickerConfig`

```python
from dataclasses import dataclass

@dataclass
class TickerConfig:
    mu: float       # annual drift
    sigma: float    # annual volatility
    rho: float      # correlation to its factor
    factor: str     # which market factor drives it ("tech", "fin", "default")
    price: float    # current price (mutable)
```

A small registry `TICKER_CONFIGS: dict[str, TickerConfig]` holds the
defaults for the seeded tickers; unknown tickers get a copy of a generic
template.

### `GBMEngine`

Pure-math, side-effect free. One method:

```python
class GBMEngine:
    def __init__(self, dt: float, rng: random.Random) -> None: ...
    def step(self, cfgs: dict[str, TickerConfig]) -> dict[str, float]:
        """Advance every config by one dt and return the new prices."""
```

It samples one `Z` per factor per step, then one `Z_ticker` per ticker,
applies the GBM formula, updates `cfg.price`, and returns the new map.
Deterministic given its `rng`.

### `SimulatorMarketData`

Wraps the engine behind the `MarketData` interface.

```python
import asyncio, random
from .base import MarketData
from .cache import PriceCache

TICK_INTERVAL_S = 0.5
P_EVENT = 1 / 600

class SimulatorMarketData(MarketData):
    def __init__(self, cache: PriceCache, seed: int | None = None) -> None:
        self._cache = cache
        self._rng = random.Random(seed)
        self._cfgs: dict[str, TickerConfig] = {}
        self._engine = GBMEngine(dt=TICK_INTERVAL_S / (252 * 6.5 * 3600),
                                  rng=self._rng)
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self, tickers: list[str]) -> None:
        for t in tickers:
            self._seed(t)
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        async with self._lock:
            self._seed(ticker)

    async def remove_ticker(self, ticker: str) -> None:
        async with self._lock:
            self._cfgs.pop(ticker, None)

    def _seed(self, ticker: str) -> None:
        if ticker in self._cfgs:
            return
        self._cfgs[ticker] = make_config(ticker)  # uses registry or fallback

    async def _run(self) -> None:
        while True:
            async with self._lock:
                new_prices = self._engine.step(self._cfgs)
                self._maybe_event(new_prices)
            for ticker, price in new_prices.items():
                await self._cache.update(ticker, price)
            await asyncio.sleep(TICK_INTERVAL_S)

    def _maybe_event(self, prices: dict[str, float]) -> None:
        if not prices or self._rng.random() > P_EVENT:
            return
        ticker = self._rng.choice(list(prices))
        shock = self._rng.uniform(-0.05, 0.05)
        prices[ticker] *= (1 + shock)
        self._cfgs[ticker].price = prices[ticker]
```

## Determinism and testing

- Passing `seed` to the constructor makes the run fully reproducible —
  valuable for E2E tests and snapshot-based unit tests of the GBM engine.
- `LLM_MOCK=true` has no bearing on the simulator; tests that want stable
  prices pass a fixed seed.
- Unit tests cover: seed-prices load, GBM step changes prices within a
  plausible range, correlation (same-factor tickers move together more than
  cross-factor over many steps), event injection stays within ±5 %, dynamic
  add/remove round-trips.

## Correlation factors

```python
FACTORS = {
    "tech":    ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX"],
    "fin":     ["JPM", "V"],
    "default": [],  # unknown tickers
}
```

Each factor has its own shared `Z_market` draw per tick. This is a crude
two-factor model — enough to make the watchlist feel like "the market"
without modeling an actual covariance matrix.

## Why not just random walks?

A naive `price += N(0, 1)` drifts negative, violates positivity, and ignores
volatility scale. GBM is one extra line of math and gives:

- Strictly positive prices.
- Volatility that scales with price (a $900 NVDA move of $5 looks like a
  $2.50 move on a $450 stock — natural with GBM).
- Returns that look log-normal, which is how real equities behave on short
  horizons.

## Tuning knobs

All at the top of `simulator.py`:

- `TICK_INTERVAL_S` — cadence. Frontend expects ~500 ms.
- `P_EVENT` — event frequency.
- `TICKER_CONFIGS` — defaults for seeded tickers.
- `FALLBACK_PRICE` — starting price for unknown tickers.
- Seed (constructor arg) — reproducibility.

The simulator never persists anything; every process start begins a fresh
price path. `session_start_price` in the cache equals the seed price for
each ticker, which is what the UI uses for "daily change %".
