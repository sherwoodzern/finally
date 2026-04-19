# External Integrations

**Analysis Date:** 2026-04-19

> **Scope note:** Of the integrations in `planning/PLAN.md`, only **Massive/Polygon.io** is wired up today. OpenRouter/LiteLLM and SQLite are specified but unimplemented.

## Market Data

### Massive / Polygon.io (IMPLEMENTED)

- **Client:** `massive>=1.0.0` (Polygon.io SDK wrapper) imported in `backend/app/market/massive_client.py`
- **Endpoint used:** `get_snapshot_all(market_type=STOCKS, tickers=[...])` — single REST call for all watched tickers
- **Mode:** REST polling (not WebSocket). Synchronous SDK call is offloaded via `asyncio.to_thread` — `backend/app/market/massive_client.py:97`
- **Auth:** `MASSIVE_API_KEY` env var, read once in `backend/app/market/factory.py:24`
- **Selection logic:** If the env var is set and non-empty, `create_market_data_source()` returns `MassiveDataSource`; otherwise `SimulatorDataSource` (`backend/app/market/factory.py:26-31`)
- **Poll interval:** `15.0` seconds (default, constructor arg), tuned for the free 5-req/min tier — `backend/app/market/massive_client.py:32`
- **Error handling:** Failures are logged and swallowed; the loop retries on the next interval (`backend/app/market/massive_client.py:118-121`). Common failures noted in comments: 401 (bad key), 429 (rate limit), network
- **Timestamp conversion:** Massive returns Unix **milliseconds**; converted to seconds via `snap.last_trade.timestamp / 1000.0` — `backend/app/market/massive_client.py:103`

### GBM Simulator (IMPLEMENTED — no external integration)

- Local fallback when no `MASSIVE_API_KEY`. Pure numpy. No external calls.
- `backend/app/market/simulator.py`

## LLM / AI Provider (PLANNED — NOT IMPLEMENTED)

Per `planning/PLAN.md` §9:

- **Gateway:** LiteLLM → OpenRouter
- **Model:** `openrouter/openai/gpt-oss-120b`
- **Inference provider:** Cerebras (for fast inference)
- **Auth:** `OPENROUTER_API_KEY` env var
- **Pattern:** Structured Outputs (JSON) with schema covering `message`, `trades[]`, `watchlist_changes[]`
- **Mock mode:** `LLM_MOCK=true` returns deterministic responses for E2E tests
- **Skill to use:** the project-local `cerebras-inference` skill

Currently no LLM code, config, or dependency exists in the repo. `litellm` is not in `pyproject.toml`.

## Database

### SQLite (PLANNED — NOT IMPLEMENTED)

Per `planning/PLAN.md` §7:

- **File:** `db/finally.db`, volume-mounted at `/app/db` in Docker
- **Init:** Lazy — FastAPI `lifespan` startup creates schema and seeds defaults on first run if file/tables missing
- **Schema location:** `backend/db/` (directory not present today)
- **Tables:** `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`
- **Seed data:** `users_profile` row with `cash_balance=10000.0`; 10-ticker watchlist (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)

Note: the 10-ticker seed list lives today in `backend/app/market/seed_prices.py` — when the DB is implemented it will need to stay in sync (or one becomes the source of truth).

## Streaming / Transport

### Server-Sent Events (PARTIAL)

- **Endpoint:** `GET /api/stream/prices` — `backend/app/market/stream.py:17-48`
- **Wire format:** `text/event-stream`, JSON payload keyed by ticker
- **Cadence:** 500 ms loop, but only emits when the `PriceCache` version counter advances (`backend/app/market/stream.py:75-83`)
- **Reconnect:** server emits `retry: 1000` on connect (`backend/app/market/stream.py:62`); browser `EventSource` handles reconnect automatically
- **Nginx buffering disabled:** `X-Accel-Buffering: no` header set
- **Missing:** no ASGI app mounts this router. `create_stream_router(price_cache)` is defined but never called from an app entrypoint.

## Docker / Deployment (PLANNED — NOT IMPLEMENTED)

- **Dockerfile** — multi-stage (Node 20 → Python 3.12 slim) — not present
- **docker-compose.yml** — optional convenience wrapper — not present
- **test/docker-compose.test.yml** — for Playwright E2E — not present

## Summary: Integration Reality vs. Plan

| Integration | Status | Evidence |
|---|---|---|
| Polygon.io via `massive` SDK | Implemented | `backend/app/market/massive_client.py` + `test_massive.py` (13 tests) |
| GBM simulator | Implemented | `backend/app/market/simulator.py` + `seed_prices.py` |
| SSE `/api/stream/prices` | Router built, not mounted | `backend/app/market/stream.py` |
| OpenRouter / LiteLLM | Not started | No code, no dep |
| SQLite schema / init | Not started | No `backend/db/` |
| Docker multi-stage build | Not started | No `Dockerfile` |
| Start/stop scripts | Not started | No `scripts/` |

---

*Update when new integrations are wired up or auth/rate-limit behavior changes.*
