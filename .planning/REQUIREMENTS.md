# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-04-19
**Core Value:** One Docker command opens a Bloomberg-style terminal where prices stream live, trades execute instantly, and an AI copilot can analyze the portfolio and execute trades on the user's behalf.

## Inherited — Validated

These were shipped in prior work and do not need to be planned again. Listed for traceability.

### Market Data

- ✓ **MARKET-01**: Strategy-pattern market data layer — `MarketDataSource` ABC with `SimulatorDataSource` and `MassiveDataSource` implementations, selected at runtime by `MASSIVE_API_KEY`
- ✓ **MARKET-02**: Thread-safe in-memory `PriceCache` with monotonic version counter driving change-detection
- ✓ **MARKET-03**: Immutable `PriceUpdate` dataclass with derived `change`, `change_percent`, `direction` and `to_dict()` for SSE
- ✓ **MARKET-04**: `create_stream_router(cache)` FastAPI `APIRouter` factory exposing the SSE price stream (router exists; not mounted on any app yet)
- ✓ **MARKET-05**: Dynamic ticker lifecycle — idempotent `add_ticker`/`remove_ticker` with seed-price onboarding for unknown symbols
- ✓ **MARKET-06**: Market-data test suite — 73 pytest cases covering GBM math, concurrency, interface conformance, and cache semantics

## v1 Requirements

Requirements for the initial release. Each maps to a roadmap phase.

### App Shell & Integration

- [x] **APP-01**: FastAPI application with `lifespan` startup that constructs the shared `PriceCache`, selects and starts the market data source, initializes SQLite, and exposes `/api/health` _(lifespan + PriceCache + market source + SSE router wired in Plan 01-01; FastAPI `app` instance and `/api/health` landed in Plan 01-02; SQLite init comes in Phase 2)_
- [ ] **APP-02**: FastAPI serves the Next.js static export from `/` on the same port as the API (no CORS, single origin)
- [x] **APP-03**: `.env` loading at startup for `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, and `LLM_MOCK` _(python-dotenv dependency added in Plan 01-01; `load_dotenv()` call site landed in Plan 01-02 `backend/app/main.py`)_
- [ ] **APP-04**: Browser-consumable SSE confirmed end-to-end — a real `EventSource` client receives ticks from the mounted `/api/stream/prices` endpoint

### Database

- [ ] **DB-01**: SQLite schema for `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, and `chat_messages` with `user_id` columns defaulting to `"default"` and unique constraints per `planning/PLAN.md` §7
- [ ] **DB-02**: Lazy initialization on startup — creates tables and seeds the default user (`cash_balance=10000.0`) plus the 10 default watchlist tickers when the DB is empty
- [ ] **DB-03**: SQLite file at `db/finally.db` persists across container restarts via a Docker named volume

### Portfolio & Trading

- [ ] **PORT-01**: `GET /api/portfolio` returns positions, cash, total value, and per-position unrealized P&L, reading live prices from the in-memory cache with graceful fallback to `avg_cost` when a ticker has no cached tick yet
- [ ] **PORT-02**: `POST /api/portfolio/trade` executes market orders (buy/sell, fractional quantities), updates cash and `positions`, and appends an immutable `trades` row — instant fill at the cached price, no fees, no confirmation dialog
- [ ] **PORT-03**: Trade validation — reject buys without sufficient cash and sells exceeding held quantity; return structured errors
- [ ] **PORT-04**: `GET /api/portfolio/history` returns the `portfolio_snapshots` time-series used by the P&L chart
- [ ] **PORT-05**: Snapshot recording on every executed trade, plus a 60-second cadence snapshot piggybacked on the existing price-update loop — no separate background task

### Watchlist

- [ ] **WATCH-01**: `GET /api/watchlist` returns the user's watchlist with latest prices from the cache
- [ ] **WATCH-02**: `POST /api/watchlist` adds a ticker; unknown symbols are onboarded into the market data source on the next tick
- [ ] **WATCH-03**: `DELETE /api/watchlist/{ticker}` removes a ticker and stops tracking it in the cache

### AI Chat

- [ ] **CHAT-01**: `POST /api/chat` — synchronous request/response. Returns the complete assistant message plus executed actions in one JSON payload
- [ ] **CHAT-02**: LLM call via LiteLLM → OpenRouter to `openrouter/openai/gpt-oss-120b` with Cerebras as the inference provider, using structured outputs matching the schema in `planning/PLAN.md` §9
- [ ] **CHAT-03**: Prompt assembly — system prompt ("FinAlly, AI trading assistant"), live portfolio context (cash, positions with P&L, watchlist with live prices, total value), and recent conversation history from `chat_messages`
- [ ] **CHAT-04**: Auto-execution of `trades[]` and `watchlist_changes[]` from the structured response — each trade goes through the same validation path as manual trades, and failures are surfaced back in the chat reply
- [ ] **CHAT-05**: Persistence of user and assistant messages in `chat_messages`, including the executed `actions` JSON on the assistant turn
- [ ] **CHAT-06**: Deterministic mock LLM mode gated by `LLM_MOCK=true` for tests and key-less development

### Frontend

- [ ] **FE-01**: Next.js TypeScript project configured for `output: 'export'` with Tailwind and the project dark theme + accent colors (yellow `#ecad0a`, blue `#209dd7`, purple `#753991`)
- [ ] **FE-02**: `EventSource` SSE client connected to `/api/stream/prices` that updates a local ticker-keyed price store
- [ ] **FE-03**: Watchlist panel — ticker, live price with green/red flash animation on tick, daily-change % computed from each event's session-start price, and a progressive sparkline accumulated from SSE since page load (Lightweight Charts)
- [ ] **FE-04**: Main chart area showing the currently selected ticker (Lightweight Charts canvas); clicking a watchlist row selects the ticker
- [ ] **FE-05**: Portfolio heatmap — treemap where rectangles are sized by position weight and colored by P&L
- [ ] **FE-06**: P&L line chart driven by `/api/portfolio/history` (Recharts SVG)
- [ ] **FE-07**: Positions table — ticker, quantity, avg cost, current price, unrealized P&L, %
- [ ] **FE-08**: Trade bar — ticker and quantity inputs with buy/sell buttons, market-only, instant fill, no confirmation dialog
- [ ] **FE-09**: AI chat panel — docked/collapsible sidebar with scrolling history, send box, loading indicator during LLM calls, and inline confirmations for executed trades and watchlist changes
- [ ] **FE-10**: Header — live-updating total portfolio value, cash balance, and connection-status dot (green connected / yellow reconnecting / red disconnected)
- [ ] **FE-11**: Demo-grade polish — smooth transitions, loading skeletons, chat-panel micro-interactions, and visible "wow" moments when trades execute

### Packaging & Ops

- [ ] **OPS-01**: Multi-stage `Dockerfile` — Node 20 slim builds the Next.js static export; Python 3.12 slim installs the `uv`-managed backend and copies the frontend build into `static/`
- [ ] **OPS-02**: Single-container runtime — `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` works as the canonical invocation
- [ ] **OPS-03**: Idempotent start/stop scripts — `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1`
- [ ] **OPS-04**: `.env.example` committed with safe placeholder values; `.env` listed in `.gitignore`

### Testing

- [ ] **TEST-01**: Backend unit tests extending the existing pytest suite — portfolio math, trade execution, trade validation, LLM structured-output parsing, API routes, LLM mock mode
- [ ] **TEST-02**: Frontend component tests — price flash animation, watchlist CRUD, portfolio display calculations, chat rendering and loading state
- [ ] **TEST-03**: Playwright E2E harness under `test/` with its own `docker-compose.test.yml` running the app container (`LLM_MOCK=true`) alongside a Playwright container
- [ ] **TEST-04**: All E2E scenarios from `planning/PLAN.md` §12 — fresh start, watchlist add/remove, buy/sell, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnection

## v2 Requirements

Deferred. Tracked but not in the current roadmap.

### Authentication & Multi-User

- **AUTH-01**: Login with email/password or magic-link, sessions, and per-user data isolation (schema is already `user_id`-keyed, so no migration is needed)

### Chat Experience

- **CHAT-07**: Token-by-token streaming of LLM responses (current v1 is non-streaming because Cerebras inference is fast enough)

### Deploy

- **DEPLOY-01**: Cloud deploy of the same container to AWS App Runner / Render / Fly.io, with the Docker volume swapped for managed persistence

### History & Visibility

- **HIST-01**: Dedicated trade-history view backed by the already-persisted `trades` table

### Polish

- **POLISH-01**: Production-grade responsive layout (tablet + phone) and a11y pass (keyboard shortcuts, ARIA, contrast)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep and re-litigation.

| Feature | Reason |
|---------|--------|
| Limit orders, stop orders, partial fills, order book | Massive complexity (matching, persistence) with no demo value; market orders only. |
| Fees, commissions, slippage, borrow costs | Simulated portfolio; instant fill at cached mid price. |
| Real-money brokerage integration | Fake money by design — the whole point is a safe playground. |
| WebSockets for price streaming | SSE is one-way server→client push, which is all the price stream needs. |
| Postgres or external DB server | Single-file SQLite with a Docker volume is enough for single-user localhost. No DB service to run. |
| Trade confirmation dialogs | Deliberately omitted — AI-driven trade execution must feel immediate and agentic. |

## Traceability

Which phases cover which requirements. Populated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| APP-01 | Phase 1 | Complete (01-01, 01-02) |
| APP-02 | Phase 8 | Pending |
| APP-03 | Phase 1 | Complete (01-01, 01-02) |
| APP-04 | Phase 1 | Pending |
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| PORT-01 | Phase 3 | Pending |
| PORT-02 | Phase 3 | Pending |
| PORT-03 | Phase 3 | Pending |
| PORT-04 | Phase 3 | Pending |
| PORT-05 | Phase 3 | Pending |
| WATCH-01 | Phase 4 | Pending |
| WATCH-02 | Phase 4 | Pending |
| WATCH-03 | Phase 4 | Pending |
| CHAT-01 | Phase 5 | Pending |
| CHAT-02 | Phase 5 | Pending |
| CHAT-03 | Phase 5 | Pending |
| CHAT-04 | Phase 5 | Pending |
| CHAT-05 | Phase 5 | Pending |
| CHAT-06 | Phase 5 | Pending |
| FE-01 | Phase 6 | Pending |
| FE-02 | Phase 6 | Pending |
| FE-03 | Phase 7 | Pending |
| FE-04 | Phase 7 | Pending |
| FE-05 | Phase 8 | Pending |
| FE-06 | Phase 8 | Pending |
| FE-07 | Phase 7 | Pending |
| FE-08 | Phase 7 | Pending |
| FE-09 | Phase 8 | Pending |
| FE-10 | Phase 7 | Pending |
| FE-11 | Phase 8 | Pending |
| OPS-01 | Phase 9 | Pending |
| OPS-02 | Phase 9 | Pending |
| OPS-03 | Phase 9 | Pending |
| OPS-04 | Phase 9 | Pending |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 8 | Pending |
| TEST-03 | Phase 10 | Pending |
| TEST-04 | Phase 10 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-04-19*
*Last updated: 2026-04-20 after Plan 01-02 completion (APP-01, APP-03 verified)*
