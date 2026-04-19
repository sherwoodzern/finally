# Architecture

**Analysis Date:** 2026-04-19

## Planned vs. Current

`planning/PLAN.md` describes a full three-tier product (Next.js static frontend served by FastAPI on port 8000, SQLite at `db/finally.db`, SSE for live prices, LiteLLM/OpenRouter for chat). Today **only the market-data subsystem in `backend/app/market/` exists** — roughly one vertical slice of the backend. There is no FastAPI app instance, no `main.py`, no database, no frontend.

This document describes the **current** architecture. Planned-but-missing components are called out inline.

## High-Level Pattern

- **Strategy pattern** for market data: a single `MarketDataSource` ABC with two concrete implementations (`SimulatorDataSource`, `MassiveDataSource`), chosen at runtime by a factory function driven by the `MASSIVE_API_KEY` env var.
- **Producer/consumer decoupling via a shared cache:** data sources push into `PriceCache`; consumers (SSE today; future portfolio/trade layers) only read the cache. Data sources and consumers never call each other directly.
- **Version counter for change detection:** `PriceCache.version` is monotonically bumped on every `update()`, letting the SSE loop avoid re-sending unchanged data.

## Layers (as implemented)

```
backend/app/market/
├── models.py         # Pure data  — PriceUpdate (frozen dataclass)
├── cache.py          # State     — PriceCache (lock-protected dict + version)
├── interface.py      # Contract  — MarketDataSource ABC
├── simulator.py      # Producer  — GBMSimulator + SimulatorDataSource
├── massive_client.py # Producer  — MassiveDataSource (Polygon REST poller)
├── factory.py        # Wiring    — create_market_data_source(cache)
├── seed_prices.py    # Config    — seed prices, GBM params, correlation groups
└── stream.py         # Edge      — create_stream_router(cache) — SSE APIRouter
```

Dependency direction:

```
stream.py ──▶ cache.py ◀── simulator.py / massive_client.py
                  ▲                ▲
                  └── factory.py ──┘
                  interface.py is imported by both producers and factory
                  models.py is leaf (imported everywhere, imports nothing)
```

No circular imports. `models.py` and `cache.py` have zero FastAPI dependency — the SSE router (`stream.py`) is the only module that touches web framework types.

## Data Flow

### Price update path (implemented)

1. Background task in `SimulatorDataSource._run_loop()` or `MassiveDataSource._poll_loop()` produces prices.
2. Each tick writes to `PriceCache.update(ticker, price, timestamp=None)`, which:
   - Looks up previous price (defaults to current for first-ever write → `direction == "flat"`)
   - Constructs an immutable `PriceUpdate`
   - Bumps `_version`
3. SSE generator `stream._generate_events` polls every 500 ms, compares `price_cache.version` to `last_version`, and yields `data: {...}\n\n` only when it changed.
4. Browser `EventSource` consumes the stream (nothing in the repo today; planned frontend).

### Ticker lifecycle

- Start: `source.start(tickers)` seeds the simulator/poller and immediately writes initial prices into the cache so SSE has data on first connect (`simulator.py:224-228`, `massive_client.py:45-46`).
- Dynamic add/remove: `add_ticker` / `remove_ticker` are idempotent no-ops when the ticker is already present/absent. The simulator rebuilds its Cholesky decomposition; Massive simply mutates the ticker list for the next poll.
- Remove also calls `cache.remove(ticker)` to purge stale data.

## Abstractions

- **`MarketDataSource` (ABC)** — `backend/app/market/interface.py`. Methods: `start`, `stop`, `add_ticker`, `remove_ticker`, `get_tickers`. All except `get_tickers` are `async`. Docstrings document lifecycle and idempotency.
- **`PriceUpdate` (frozen dataclass, slots)** — immutable snapshot with derived properties `change`, `change_percent`, `direction`, and `to_dict()` for JSON/SSE.
- **`PriceCache`** — thread-safe (`threading.Lock`) dict keyed by ticker. The lock matters because `MassiveDataSource` writes from an `asyncio.to_thread` worker, not the event loop.
- **`GBMSimulator`** — pure math engine separate from the `SimulatorDataSource` lifecycle shell. Keeps per-ticker `mu/sigma`, maintains a Cholesky decomposition of the sector correlation matrix, applies a ~0.1%/tick random shock event for visual drama.

## Entry Points

**Today:**
- `backend/market_data_demo.py` — the only runnable program. Spins up `PriceCache` + `SimulatorDataSource`, renders a live `rich` terminal dashboard for 60 seconds.
- `uv run --extra dev pytest` — runs the 73-test suite under `backend/tests/market/`.

**Missing (required by PLAN.md):**
- No FastAPI `app` instance, no `lifespan` startup, no `uvicorn` command wired up.
- No CLI/script that imports `create_stream_router` and mounts it on an app.
- No Docker entrypoint.

## Concurrency Model

- Single-process asyncio.
- `PriceCache` uses a `threading.Lock` because `MassiveDataSource._poll_once` calls the synchronous Polygon SDK via `asyncio.to_thread`, which runs the write on a worker thread. The simulator writes happen on the event loop thread, but the lock is cheap and makes the cache safe for either producer.
- Each producer owns exactly one background `asyncio.Task`. `stop()` cancels and awaits the task.

## Config / Env Flow

- `factory.create_market_data_source(cache)` reads `MASSIVE_API_KEY` directly from `os.environ` once at construction time. No config object, no `.env` loader today.
- All other env vars in `planning/PLAN.md` §5 (`OPENROUTER_API_KEY`, `LLM_MOCK`) are unused — no code reads them yet.

## Missing Architectural Pieces (per PLAN.md)

| Piece | Where it should live (per PLAN) | Status |
|---|---|---|
| FastAPI app + `lifespan` init | `backend/app/main.py` (or similar) | Missing |
| DB layer | `backend/db/` + `backend/app/db/` | Missing |
| Portfolio service | `backend/app/portfolio/` | Missing |
| Watchlist CRUD | `backend/app/watchlist/` | Missing |
| Chat/LLM service | `backend/app/chat/` | Missing |
| REST endpoints (`/api/portfolio`, `/api/watchlist`, `/api/chat`, `/api/health`) | FastAPI routers | Missing |
| Static frontend mounting | FastAPI `StaticFiles` | Missing |
| Frontend | `frontend/` | Missing |
| Docker build | `Dockerfile`, `docker-compose.yml` | Missing |

---

*Update on major layering changes — new subsystems, new entry points, or changes to the cache/streaming contract.*
