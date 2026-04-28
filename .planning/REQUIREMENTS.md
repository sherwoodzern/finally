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
- [x] **APP-02**: FastAPI serves the Next.js static export from `/` on the same port as the API (no CORS, single origin) _(StaticFiles mount registered after all `/api/*` routers in Plan 08-01; G1 dev SSE 308→307 fix via `skipTrailingSlashRedirect: true` in next.config.mjs; final `npm run build` artifact `frontend/out/index.html` produced in Plan 08-08; `test_index_html_served_at_root` PASSES)_
- [x] **APP-03**: `.env` loading at startup for `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, and `LLM_MOCK` _(python-dotenv dependency added in Plan 01-01; `load_dotenv()` call site landed in Plan 01-02 `backend/app/main.py`)_
- [x] **APP-04**: Browser-consumable SSE confirmed end-to-end — a real `EventSource` client receives ticks from the mounted `/api/stream/prices` endpoint _(Plan 01-03: httpx streaming client against an in-process uvicorn server receives `data:` frames and continues emitting as the cache version advances)_

### Database

- [ ] **DB-01**: SQLite schema for `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, and `chat_messages` with `user_id` columns defaulting to `"default"` and unique constraints per `planning/PLAN.md` §7
- [ ] **DB-02**: Lazy initialization on startup — creates tables and seeds the default user (`cash_balance=10000.0`) plus the 10 default watchlist tickers when the DB is empty
- [ ] **DB-03**: SQLite file at `db/finally.db` persists across container restarts via a Docker named volume

### Portfolio & Trading

- [x] **PORT-01**: `GET /api/portfolio` returns positions, cash, total value, and per-position unrealized P&L, reading live prices from the in-memory cache with graceful fallback to `avg_cost` when a ticker has no cached tick yet _(service layer landed in Plan 03-02; HTTP endpoint wired via create_portfolio_router in Plan 03-03 with 3 integration tests)_
- [x] **PORT-02**: `POST /api/portfolio/trade` executes market orders (buy/sell, fractional quantities), updates cash and `positions`, and appends an immutable `trades` row — instant fill at the cached price, no fees, no confirmation dialog _(service layer landed in Plan 03-02; HTTP endpoint wired in Plan 03-03 with happy-path + fractional + partial-sell + full-sell integration tests)_
- [x] **PORT-03**: Trade validation — reject buys without sufficient cash and sells exceeding held quantity; return structured errors _(domain exceptions landed in Plan 03-02; Plan 03-03 maps them to HTTP 400 with detail={error, message} and adds 4 error-case + 1 schema integration tests asserting DB state is unchanged)_
- [x] **PORT-04**: `GET /api/portfolio/history` returns the `portfolio_snapshots` time-series used by the P&L chart _(service layer landed in Plan 03-02; HTTP endpoint wired in Plan 03-03 with empty/ordering/limit tests and FastAPI Query(ge=1, le=1000) bounds)_
- [x] **PORT-05**: Snapshot recording on every executed trade, plus a 60-second cadence snapshot piggybacked on the existing price-update loop — no separate background task _(inline post-trade snapshot landed in Plan 03-02; Plan 03-03 registers make_snapshot_observer in the lifespan with boot-time initial snapshot + 60s threshold + route-level trade-reset clock, exception-isolated per Plan 01's register_tick_observer contract)_

### Watchlist

- [x] **WATCH-01**: `GET /api/watchlist` returns the user's watchlist with latest prices from the cache _(service layer `get_watchlist(conn, cache)` landed in Plan 04-01 with 4 unit tests; HTTP endpoint wired in Plan 04-02)_
- [x] **WATCH-02**: `POST /api/watchlist` adds a ticker; unknown symbols are onboarded into the market data source on the next tick _(service layer `add_ticker(conn, ticker)` with `INSERT ... ON CONFLICT DO NOTHING` + rowcount + idempotent `AddResult(status="added"|"exists")` landed in Plan 04-01; HTTP route + `source.add_ticker` hand-off wired in Plan 04-02)_
- [x] **WATCH-03**: `DELETE /api/watchlist/{ticker}` removes a ticker and stops tracking it in the cache _(service layer `remove_ticker(conn, ticker)` with idempotent `RemoveResult(status="removed"|"not_present")` landed in Plan 04-01; HTTP route + `source.remove_ticker` hand-off wired in Plan 04-02)_

### AI Chat

- [ ] **CHAT-01**: `POST /api/chat` — synchronous request/response. Returns the complete assistant message plus executed actions in one JSON payload
- [ ] **CHAT-02**: LLM call via LiteLLM → OpenRouter to `openrouter/openai/gpt-oss-120b` with Cerebras as the inference provider, using structured outputs matching the schema in `planning/PLAN.md` §9
- [ ] **CHAT-03**: Prompt assembly — system prompt ("FinAlly, AI trading assistant"), live portfolio context (cash, positions with P&L, watchlist with live prices, total value), and recent conversation history from `chat_messages`
- [ ] **CHAT-04**: Auto-execution of `trades[]` and `watchlist_changes[]` from the structured response — each trade goes through the same validation path as manual trades, and failures are surfaced back in the chat reply
- [ ] **CHAT-05**: Persistence of user and assistant messages in `chat_messages`, including the executed `actions` JSON on the assistant turn
- [ ] **CHAT-06**: Deterministic mock LLM mode gated by `LLM_MOCK=true` for tests and key-less development

### Frontend

- [x] **FE-01**: Next.js TypeScript project configured for `output: 'export'` with Tailwind and the project dark theme + accent colors (yellow `#ecad0a`, blue `#209dd7`, purple `#753991`) _(Plan 06-01 scaffolded with Next.js 16 + Tailwind v4 CSS-first @theme + :root dual-declaration; all four brand hex values verified in compiled CSS chunks — FE-01 validated 2026-04-24)_
- [x] **FE-02**: `EventSource` SSE client connected to `/api/stream/prices` that updates a local ticker-keyed price store _(Zustand price store + PriceStreamProvider landed in Plan 06-02; Vitest 8-test MockEventSource suite + /debug page delivered in Plan 06-03 — FE-02 validated 2026-04-24)_
- [ ] **FE-03**: Watchlist panel — ticker, live price with green/red flash animation on tick, daily-change % computed from each event's session-start price, and a progressive sparkline accumulated from SSE since page load (Lightweight Charts)
- [ ] **FE-04**: Main chart area showing the currently selected ticker (Lightweight Charts canvas); clicking a watchlist row selects the ticker
- [x] **FE-05**: Portfolio heatmap — treemap where rectangles are sized by position weight and colored by P&L _(Recharts `<Treemap>` with `dataKey="weight" = quantity*current_price`, binary up/down fill via `var(--color-up/down)`, neutral `var(--color-surface-alt)` for cold-cache positions, exported `handleHeatmapCellClick` dispatches `setSelectedTicker` + `setSelectedTab('chart')` — Plan 08-03; 13 Vitest tests)_
- [x] **FE-06**: P&L line chart driven by `/api/portfolio/history` (Recharts SVG) _(Recharts `<LineChart>` against real `getPortfolioHistory()` with 15s refetchInterval, dotted ReferenceLine at $10k, stroke flips at break-even, custom `<PnLTooltip />` typed via Recharts 3.x — Plan 08-04; 6 Vitest tests)_
- [ ] **FE-07**: Positions table — ticker, quantity, avg cost, current price, unrealized P&L, %
- [ ] **FE-08**: Trade bar — ticker and quantity inputs with buy/sell buttons, market-only, instant fill, no confirmation dialog
- [x] **FE-09**: AI chat panel — docked/collapsible sidebar with scrolling history, send box, loading indicator during LLM calls, and inline confirmations for executed trades and watchlist changes _(ChatDrawer collapsible shell + ChatHeader (›/‹) + ChatThread `useQuery(['chat','history'])` + ChatInput Enter/Shift+Enter contract + ThinkingBubble loading + ActionCardList rendering watchlist_changes BEFORE trades + ActionCard 6-status pulse + XSS guard via plain-text rendering — Plans 08-06 (shell) + 08-07 (orchestration); 16 Vitest tests including XSS regression)_
- [ ] **FE-10**: Header — live-updating total portfolio value, cash balance, and connection-status dot (green connected / yellow reconnecting / red disconnected)
- [x] **FE-11**: Demo-grade polish — smooth transitions, loading skeletons, chat-panel micro-interactions, and visible "wow" moments when trades execute _(SkeletonBlock primitive, TabBar with accent-blue underline, ChatDrawer 300ms width transition, action-pulse-up/down 800ms keyframes, thinking-pulse loading dots, prefers-reduced-motion guard, PositionRow 800ms trade-flash co-existing with Phase-7 500ms price-flash, TradeBar manual-trade flash parity — Plans 08-02/05/06/07/08; perceptual feel items in 08-HUMAN-UAT.md)_

### Packaging & Ops

- [x] **OPS-01**: Multi-stage `Dockerfile` — Node 20 slim builds the Next.js static export; Python 3.12 slim installs the `uv`-managed backend and copies the frontend build into `/app/frontend/out/` (Phase 9)
- [x] **OPS-02**: Single-container runtime — `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` works as the canonical invocation (Phase 9)
- [x] **OPS-03**: Idempotent start/stop scripts — `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` (Phase 9)
- [x] **OPS-04**: `.env.example` committed with safe placeholder values; `.env` listed in `.gitignore` (Phase 9)

### Testing

- [ ] **TEST-01**: Backend unit tests extending the existing pytest suite — portfolio math, trade execution, trade validation, LLM structured-output parsing, API routes, LLM mock mode
- [x] **TEST-02**: Frontend component tests — price flash animation, watchlist CRUD, portfolio display calculations, chat rendering and loading state _(111/111 Vitest tests across 19 files; Heatmap+HeatmapCell calc tests, PnLChart tooltip+stroke-flip tests, ChatThread XSS-guard test, ChatInput keyboard contract tests, PositionRow price-flash + trade-flash regression tests — Plans 08-02..08-08)_
- [x] **TEST-03**: Playwright E2E harness under `test/` with its own `docker-compose.test.yml` running the app container (`LLM_MOCK=true`) alongside a Playwright container _(test/docker-compose.test.yml + test/playwright.config.ts; appsvc Healthy + 21/21 green on canonical D-03 command across two consecutive runs — Phase 10)_
- [x] **TEST-04**: All E2E scenarios from `planning/PLAN.md` §12 — fresh start, watchlist add/remove, buy/sell, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnection _(7 specs × 3 browsers = 21 (spec, project) pairs; 0 failed / 0 flaky on two consecutive canonical runs with no inter-run cleanup — Phase 10)_

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
| APP-02 | Phase 8 | Complete (08-01 mount + G1 fix; 08-08 final build artifact) |
| APP-03 | Phase 1 | Complete (01-01, 01-02) |
| APP-04 | Phase 1 | Complete (01-03) |
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| PORT-01 | Phase 3 | Complete (03-02 service layer; 03-03 adds HTTP route) |
| PORT-02 | Phase 3 | Complete (03-02 service layer; 03-03 adds HTTP route) |
| PORT-03 | Phase 3 | Complete (03-02 service layer; 03-03 adds HTTP mapping) |
| PORT-04 | Phase 3 | Complete (03-02 service layer; 03-03 adds HTTP route) |
| PORT-05 | Phase 3 | Pending (03-03 — observer wiring) |
| WATCH-01 | Phase 4 | In progress (04-01 service layer; 04-02 adds HTTP route) |
| WATCH-02 | Phase 4 | In progress (04-01 service layer; 04-02 adds HTTP route) |
| WATCH-03 | Phase 4 | In progress (04-01 service layer; 04-02 adds HTTP route) |
| CHAT-01 | Phase 5 | Pending |
| CHAT-02 | Phase 5 | Pending |
| CHAT-03 | Phase 5 | Pending |
| CHAT-04 | Phase 5 | Pending |
| CHAT-05 | Phase 5 | Pending |
| CHAT-06 | Phase 5 | Pending |
| FE-01 | Phase 6 | Validated (06-01 scaffold + theme + static export) |
| FE-02 | Phase 6 | Validated (06-02 store + provider; 06-03 tests + /debug page) |
| FE-03 | Phase 7 | Pending |
| FE-04 | Phase 7 | Pending |
| FE-05 | Phase 8 | Complete (08-03 Heatmap + 08-05 TabBar wiring) |
| FE-06 | Phase 8 | Complete (08-04 PnLChart + 08-05 TabBar wiring) |
| FE-07 | Phase 7 | Pending |
| FE-08 | Phase 7 | Pending |
| FE-09 | Phase 8 | Complete (08-06 chat shell + 08-07 ChatThread/ChatInput orchestration) |
| FE-10 | Phase 7 | Pending |
| FE-11 | Phase 8 | Complete (08-02/05/06/07/08 motion primitives + skeletons + flash parity; HUMAN-UAT pending) |
| OPS-01 | Phase 9 | Complete (09-01 Dockerfile + .dockerignore; cold build 162s, image 124 MB) |
| OPS-02 | Phase 9 | Complete (09-03 integration test PASS; HUMAN-UAT pending for browser auto-open + visual UI) |
| OPS-03 | Phase 9 | Complete (09-03 four cross-platform scripts; HUMAN-UAT pending for Windows pwsh runtime) |
| OPS-04 | Phase 9 | Complete (09-02 .env.example with safe placeholders; .gitignore:141 preserves .env ignore) |
| TEST-01 | Phase 5 | Pending |
| TEST-02 | Phase 8 | Complete (111/111 Vitest across 19 files) |
| TEST-03 | Phase 10 | Complete (10-01 harness foundation; 10-09 closes SC#3 reproducibility gate) |
| TEST-04 | Phase 10 | Complete (10-02..10-05 spec authoring; 10-06..10-09 stabilisation; 21/21 green × 2 consecutive runs) |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-04-19*
*Last updated: 2026-04-26 after Phase 8 completion (APP-02, FE-05, FE-06, FE-09, FE-11, TEST-02 validated; 5/5 automated must-haves PASSED, 6 perceptual items deferred to 08-HUMAN-UAT.md)*
