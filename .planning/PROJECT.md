# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a single-user, single-container AI trading workstation — a Bloomberg-style terminal that streams live prices, runs a simulated $10k portfolio, and pairs every screen with an LLM chat copilot that can analyze positions and execute trades on the user's behalf. It is the capstone project for an agentic AI coding course, built by orchestrated coding agents that interact through files in `.planning/`.

## Core Value

A user runs one Docker command, opens `http://localhost:8000`, and within seconds is watching live prices stream, buying shares, and asking an AI assistant to reshape the portfolio — with trades actually executing from the chat. If anything else fails, that core demo must still work.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. Inherited from prior work on this repo. -->

- ✓ **MARKET-01**: Strategy-pattern market data layer with a single `MarketDataSource` ABC and two interchangeable implementations — `SimulatorDataSource` (correlated GBM with random events) and `MassiveDataSource` (Polygon REST poller) — selected at runtime by `MASSIVE_API_KEY` — `backend/app/market/` (existing)
- ✓ **MARKET-02**: Thread-safe in-memory `PriceCache` with monotonic version counter driving change-detection for the streaming layer — `backend/app/market/cache.py` (existing)
- ✓ **MARKET-03**: Immutable `PriceUpdate` dataclass with derived `change`, `change_percent`, and `direction` — `backend/app/market/models.py` (existing)
- ✓ **MARKET-04**: FastAPI `APIRouter` factory `create_stream_router(cache)` that exposes the SSE `/api/stream/prices` generator — `backend/app/market/stream.py` (existing, not yet mounted)
- ✓ **MARKET-05**: Dynamic ticker lifecycle (`add_ticker` / `remove_ticker` idempotent) with seed-price onboarding for unknown symbols — `backend/app/market/simulator.py`, `massive_client.py` (existing)
- ✓ **MARKET-06**: Market-data test suite (73 tests, `pytest-asyncio`) covering math, concurrency, interface conformance, and cache semantics — `backend/tests/market/` (existing)

### Active

<!-- v1 scope. Hypotheses until shipped and validated. Organized by subsystem. -->

**Integration & app shell**
- [ ] **APP-01**: FastAPI application instance with `lifespan` startup that initializes `PriceCache`, selects and starts the market data source, initializes SQLite, and exposes `/api/health`
- [ ] **APP-02**: Static frontend mounting — FastAPI serves the Next.js `output: 'export'` build from `/` on the same port as the API
- [ ] **APP-03**: Unified configuration loading from `.env` (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`)
- [ ] **APP-04**: Browser-consumable SSE verified end-to-end — mounted `/api/stream/prices` delivers ticks to a real `EventSource` client

**Database & persistence**
- [ ] **DB-01**: SQLite schema for `users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages` with `user_id` columns defaulting to `"default"`
- [ ] **DB-02**: Lazy initialization on startup — creates tables and seeds the default user (`cash_balance=10000.0`) and the 10 default watchlist tickers if the DB is empty
- [ ] **DB-03**: Volume-mounted SQLite file at `db/finally.db` persists across container restarts

**Portfolio & trading**
- [ ] **PORT-01**: `GET /api/portfolio` returns positions, cash, total value, and per-position unrealized P&L, reading live prices from the in-memory cache with graceful fallback when the cache has no tick yet
- [ ] **PORT-02**: `POST /api/portfolio/trade` executes market orders (buy/sell, fractional quantities), updates cash, positions, and appends an immutable `trades` row — instant fill at the cached price, no fees, no confirmation
- [ ] **PORT-03**: Trade validation — reject buys without sufficient cash, reject sells exceeding held quantity; surface structured errors
- [ ] **PORT-04**: `GET /api/portfolio/history` returns `portfolio_snapshots` time-series for the P&L chart
- [ ] **PORT-05**: Snapshot recording on every trade, plus a 60-second cadence piggybacked on the existing price-update loop (no separate background task)

**Watchlist**
- [ ] **WATCH-01**: `GET /api/watchlist` returns current watchlist with latest prices from the cache
- [ ] **WATCH-02**: `POST /api/watchlist` adds a ticker; unknown symbols are onboarded into the market data source on the next tick
- [ ] **WATCH-03**: `DELETE /api/watchlist/{ticker}` removes a ticker and stops tracking in the cache

**AI chat**
- [ ] **CHAT-01**: `POST /api/chat` — synchronous (non-streaming) request/response flow. Returns the complete LLM reply plus executed actions in one JSON payload
- [ ] **CHAT-02**: LLM call via LiteLLM → OpenRouter to `openrouter/openai/gpt-oss-120b` with Cerebras as the inference provider, using structured outputs matching the schema in `planning/PLAN.md` §9
- [ ] **CHAT-03**: Prompt construction — system prompt ("FinAlly, AI trading assistant"), live portfolio context (cash, positions with P&L, watchlist with live prices, total value), recent chat history from `chat_messages`
- [ ] **CHAT-04**: Auto-execution of `trades[]` and `watchlist_changes[]` from the structured response, each going through the same validation path as manual trades. Failures are surfaced back to the LLM/user, not silently dropped
- [ ] **CHAT-05**: Persistence of user and assistant messages in `chat_messages`, including the executed `actions` JSON on the assistant turn
- [ ] **CHAT-06**: Deterministic mock LLM mode gated by `LLM_MOCK=true` for tests and key-less development

**Frontend (Next.js, static export)**
- [ ] **FE-01**: Next.js TypeScript project configured for `output: 'export'`, Tailwind with the project's dark theme and accent colors (yellow `#ecad0a`, blue `#209dd7`, purple `#753991`)
- [ ] **FE-02**: `EventSource`-based SSE client to `/api/stream/prices` that updates a local ticker-keyed price store
- [ ] **FE-03**: Watchlist panel — ticker, live price with green/red flash animation on tick, daily-change % computed from each event's session-start price, and a progressive sparkline accumulated from SSE since page load (Lightweight Charts)
- [ ] **FE-04**: Main chart area showing the currently selected ticker (Lightweight Charts canvas). Clicking a watchlist row selects the ticker
- [ ] **FE-05**: Portfolio heatmap / treemap — rectangles sized by position weight, colored by P&L (green profit, red loss)
- [ ] **FE-06**: P&L line chart driven by `/api/portfolio/history` (Recharts SVG)
- [ ] **FE-07**: Positions table — ticker, qty, avg cost, current price, unrealized P&L, %
- [ ] **FE-08**: Trade bar — ticker + qty + buy/sell buttons, market-only, instant fill, no confirmation dialog
- [ ] **FE-09**: AI chat panel — docked/collapsible sidebar, scrolling history, send box, loading indicator during LLM calls, inline confirmations for executed trades and watchlist changes
- [ ] **FE-10**: Header — live-updating total portfolio value, cash balance, and a connection-status dot (green connected / yellow reconnecting / red disconnected)
- [ ] **FE-11**: Demo-grade polish — smooth transitions, loading skeletons, chat-panel micro-interactions, and visible "wow" moments when trades execute

**Packaging & ops**
- [ ] **OPS-01**: Multi-stage `Dockerfile` — Node 20 slim builds the Next.js static export, Python 3.12 slim installs the `uv`-managed backend and copies the frontend build into `static/`
- [ ] **OPS-02**: Single-container run — `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally` — no docker-compose in production
- [ ] **OPS-03**: Idempotent start/stop scripts for macOS/Linux (`scripts/start_mac.sh`, `scripts/stop_mac.sh`) and Windows (`scripts/start_windows.ps1`, `scripts/stop_windows.ps1`)
- [ ] **OPS-04**: `.env.example` committed; `.env` gitignored

**Testing**
- [ ] **TEST-01**: Backend unit tests extending the existing pytest suite — portfolio math, trade execution, trade validation, LLM response parsing, API routes, LLM mock mode
- [ ] **TEST-02**: Frontend component tests — price flash, watchlist CRUD, portfolio display, chat rendering and loading state
- [ ] **TEST-03**: Playwright E2E harness in `test/` with its own `docker-compose.test.yml` running the app container with `LLM_MOCK=true` alongside a Playwright container
- [ ] **TEST-04**: All §12 E2E scenarios — fresh start, watchlist add/remove, buy/sell paths, heatmap + P&L chart rendering, mocked chat with trade execution, SSE reconnection

### Out of Scope

<!-- Explicit boundaries with reasoning. -->

- **Authentication / multi-user** — single-user, `user_id="default"` hardcoded. Schema is user-keyed so a future migration is minimal, but auth is not v1.
- **Limit orders, stop orders, order book, partial fills** — market orders only. Eliminates order-matching complexity.
- **Fees, commissions, slippage, borrow costs** — instant fill at the cached mid price.
- **Real money / brokerage integration** — simulated portfolio, fake money, no broker connectivity.
- **Token-by-token LLM streaming** — Cerebras inference is fast enough that a loading indicator suffices. The chat endpoint returns one complete JSON payload.
- **WebSockets** — SSE is one-way server→client push, which is all the price stream needs.
- **Postgres / external DB server** — single-file SQLite with a Docker volume. No database service to run.
- **Cloud deploy in v1** — localhost-Docker only. Terraform/App Runner/Render are stretch goals, not capstone requirements.
- **Production-grade responsive / accessibility pass** — desktop-first, demo-grade polish. Tablet works, phone is not a target.
- **Trade confirmation dialogs** — deliberately omitted so AI-driven trade execution feels immediate and agentic.
- **Order history UI beyond what's implied by the positions table** — `trades` is persisted but no dedicated trade-history view is in v1.

## Context

- **Capstone for an agentic AI coding course.** The product itself is the medium — the demonstration is that orchestrated coding agents (through files in `.planning/`) can produce a production-looking full-stack application.
- **Brownfield starting point.** One vertical slice exists and is solid: the market-data subsystem under `backend/app/market/` with 73 passing tests, including a ready-to-mount SSE router. The rest of the stack (FastAPI app instance, DB, portfolio/chat services, frontend, Docker) is unbuilt.
- **Pre-existing spec.** `planning/PLAN.md` is an extremely detailed specification that this project adopts wholesale as v1, with minor re-validation during the `/gsd-new-project` questioning pass (April 2026). It is the canonical reference for endpoint shapes, schema, SSE event contents, and the LLM structured-output schema.
- **User expectations for the demo.** The "one Docker command → Bloomberg terminal + AI copilot" moment is what sells the agentic-AI story, so demo-grade polish and inline AI-driven trade execution are non-negotiable. Everything else bends around that.
- **Codebase map.** Current architecture, stack, structure, conventions, testing posture, integrations, and known concerns are captured in `.planning/codebase/*.md` (analysis date 2026-04-19). Consult these before planning.
- **Known concerns to watch.** No `.env.example` yet; no FastAPI app entry point; `asyncio.to_thread` write path in `MassiveDataSource` is the reason `PriceCache` uses a `threading.Lock`; SSE generator polls at 500 ms and skips when `cache.version` is unchanged.

## Constraints

- **Tech stack (backend)**: Python 3.12+, FastAPI, `uv` for package management (project rule: `uv run xxx`, never `python3`; `uv add xxx`, never `pip install`), uvicorn, SQLite via stdlib `sqlite3`, LiteLLM, NumPy, Massive SDK.
- **Tech stack (frontend)**: Next.js with TypeScript in `output: 'export'` mode, Tailwind CSS, Lightweight Charts (main chart + sparklines), Recharts (P&L line chart).
- **Tech stack (LLM)**: LiteLLM → OpenRouter to `openrouter/openai/gpt-oss-120b` with Cerebras as inference provider. Structured outputs for trade/watchlist actions. Invoke via the `cerebras` skill.
- **Runtime**: Single Docker container on port 8000. One Python process. No compose file in production. Multi-stage Dockerfile (Node 20 → Python 3.12 slim).
- **Persistence**: SQLite file at `db/finally.db`, volume-mounted to `/app/db`. No migrations — lazy schema creation on first startup.
- **Transport**: REST under `/api/*`, SSE under `/api/stream/*`, same origin as static frontend. No CORS configuration.
- **Code style (project)**: No over-engineering, no defensive programming, exception managers only when needed. Short modules and functions. Clear docstrings, sparing comments. No emojis in code or logs. Latest library APIs.
- **Process**: Work incrementally — small steps, validate each one. For any bug or unexpected behavior, prove the root cause before fixing.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Adopt `planning/PLAN.md` wholesale as v1 scope | Spec is already extremely detailed, internally consistent, and aligned with the capstone demo. No redesign needed. | — Pending |
| Full feature set in v1 (chat + heatmap + P&L chart all included) | Capstone demo requires the "wow" moment of AI-driven trade execution against a polished terminal UI. | — Pending |
| Keep LiteLLM + OpenRouter + `openrouter/openai/gpt-oss-120b` (Cerebras) | Matches the existing `cerebras` skill, Cerebras inference is fast enough to skip token streaming, and OpenRouter abstracts provider. | — Pending |
| No authentication in v1, `user_id="default"` hardcoded | Single-user demo on localhost. Schema is user-keyed so auth is a non-migration addition later. | — Pending |
| Localhost Docker only (no cloud deploy in v1) | Capstone is a local demo; the container is self-contained and can deploy later without code changes. | — Pending |
| Market-data subsystem treated as Validated | 73 tests already green and the architecture is sound — only gap is browser-level SSE integration (captured as APP-04). | — Pending |
| Demo-grade polish target (not production-grade responsive/a11y) | Desktop-first capstone demo. Production-grade responsive/a11y is weeks of extra work for no demo value. | — Pending |
| All §12 E2E scenarios pursued with `LLM_MOCK=true` in a separate `docker-compose.test.yml` | The E2E pack is what proves the whole stack works end-to-end, which is exactly what the capstone must show. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-19 after initialization*
