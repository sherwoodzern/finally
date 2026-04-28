# Milestone v1.0 — FinAlly: AI Trading Workstation — Project Summary

**Generated:** 2026-04-28
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

FinAlly (Finance Ally) is a single-user, single-container AI trading workstation — a Bloomberg-style terminal that streams live prices, runs a simulated $10k portfolio, and pairs every screen with an LLM chat copilot that can analyze positions and execute trades on the user's behalf. It is the capstone project for an agentic AI coding course; the medium IS the message: orchestrated coding agents (interacting through files in `.planning/`) produced a production-looking full-stack application.

**Core demo moment.** One Docker command → browser opens to `http://localhost:8000` → user immediately sees a 10-ticker streaming watchlist, a $10k portfolio, a heatmap + P&L chart, and an AI chat panel that can buy/sell shares and curate the watchlist via natural language.

**Scope status.** v1.0 is **complete** — all 10 phases shipped, 47 plans executed, the canonical E2E harness exits 0 with `21 passed / 0 failed / 0 flaky` reproducibly across two consecutive runs and three browsers. The roadmap has no Phase 11.

---

## 2. Architecture & Technical Decisions

| Decision | Why | Phase |
|---|---|---|
| **Single Docker container, single port (8000)** | Students run one command; no docker-compose for production, no service orchestration. | Phase 9 |
| **FastAPI serves Next.js static export from `/`** | Same-origin, no CORS, one process for `/api/*` and the static frontend. | Phase 1 (mount), Phase 8 (final build) |
| **SSE over WebSockets** | One-way server→client push is all the price stream needs; simpler, universal browser support, native `EventSource` reconnect. | Phase 1 (router), Phase 6 (client) |
| **SQLite + lazy schema init in FastAPI lifespan** | No auth → no multi-user → no need for a DB server. Volume-mounted file persists; tables created and seeded on first boot if empty. | Phase 2 |
| **Market-orders-only portfolio** | Eliminates order book, limit-order logic, partial fills — drastically simpler portfolio math. Instant fill at the cached mid price. | Phase 3 |
| **Two market-data sources behind one ABC** | `SimulatorDataSource` (correlated GBM + random events) is the default; `MassiveDataSource` (Polygon REST poller) activates only when `MASSIVE_API_KEY` is set. Inherited from prior work. | Pre-existing (validated in Phase 1) |
| **LiteLLM → OpenRouter to `openrouter/openai/gpt-oss-120b` with Cerebras inference** | Matches the `cerebras` skill; Cerebras is fast enough that token streaming is not needed (loading dots suffice); structured outputs drive auto-execution. | Phase 5 |
| **Auto-executed trades from chat (no confirmation dialog)** | Stakes are zero (fake money) and the agentic-AI moment is the demo. Same validation path as manual trades; failures surface back in the reply. | Phase 5 |
| **`LLM_MOCK=true` deterministic chat path** | Free, fast, reproducible E2E tests; key-less local dev. | Phase 5 |
| **Zustand for the live price store + TanStack Query for portfolio/history** | Push-driven prices need a global, mutation-light store; pull-driven REST resources benefit from cache + refetchInterval. Clean separation. | Phase 6, 7, 8 |
| **Lightweight Charts for the main ticker chart + sparklines, Recharts for heatmap + P&L** | Lightweight Charts (canvas) is fast and self-sizing for many small/streaming series; Recharts (SVG) has the simpler API for the lower-frequency heatmap and P&L line. | Phase 7, 8 |
| **Tab-based center column (Chart / Heatmap / P&L) inside a 3-column grid** | Density goal: every pixel earns its place. Three persistent rails (watchlist · workspace · positions) plus the chat drawer. | Phase 7, 8 |
| **Playwright in `test/` with its own `docker-compose.test.yml`** | Keeps browser deps out of the production image; one `compose up --abort-on-container-exit --exit-code-from playwright` runs the full harness. | Phase 10 |
| **Per-project Playwright viewport 1440×900** | Aligns the test environment with `planning/PLAN.md §10`'s `desktop-first ... wide screens` design contract; avoids spurious layout-overlap failures at the 1280×720 device default. | Phase 10 (Plan 10-09) |
| **`tmpfs:/app/db` on the test-side appsvc** | Each `docker compose up` starts with a fresh in-memory `/app/db`, giving the canonical D-03 command's `reproducibly` clause teeth without changing the command, without a `down -v` wrapper, and without a test-only `/api/test/reset` endpoint. Production `Dockerfile:57 VOLUME /app/db` is preserved unchanged. | Phase 10 (Plan 10-09) |
| **Permanent dark theme** *(later flipped to light, post-verification)* | Original Bloomberg-terminal aesthetic; CSS variables in `globals.css` (`--color-surface`, `--color-foreground`, etc.) consumed via Tailwind v4 `@theme` tokens. Most components reflow when tokens change; only canvas/SVG hex literals (Lightweight Charts background, Recharts strokes) need direct edits. | Phase 6 (palette), post-milestone (light flip) |

---

## 3. Phases Delivered

| Phase | Name | Plans | Verification | One-line outcome |
|------|------|-----|------|---|
| 1 | App Shell & Config | 3/3 | passed | FastAPI app + lifespan + PriceCache + market source + SSE router + browser-consumable `/api/stream/prices`. |
| 2 | Database Foundation | 3/3 | passed | SQLite schema (`users_profile`, `watchlist`, `positions`, `trades`, `portfolio_snapshots`, `chat_messages`) + lazy init + volume-mounted `db/finally.db`. |
| 3 | Portfolio & Trading API | 3/3 | passed | `/api/portfolio` (live cache + graceful fallback), `/api/portfolio/trade` (market orders + validation), `/api/portfolio/history` + 60s snapshot piggyback on the price loop. |
| 4 | Watchlist API | 2/2 | passed | `GET/POST/DELETE /api/watchlist/{ticker}` with idempotent add/remove and on-the-fly source onboarding for unknown symbols. |
| 5 | AI Chat Integration | 3/3 | *(no VERIFICATION.md)* | `POST /api/chat` synchronous flow + LiteLLM/OpenRouter/Cerebras structured outputs + auto-execution of trades & watchlist changes + `chat_messages` persistence + `LLM_MOCK=true` deterministic path. |
| 6 | Frontend Scaffold & SSE | 3/3 | passed | Next.js TS `output: 'export'` + Tailwind v4 dark theme + Zustand price store + `EventSource` client wired to `/api/stream/prices` + Vitest mock-EventSource suite + `/debug` page. |
| 7 | Market Data & Trading UI | 8/8 | human_needed | Watchlist panel (flash + sparkline), main ticker chart (Lightweight Charts), positions table, trade bar (manual buy/sell), header with live total + cash + connection dot, brand palette landed in compiled CSS. |
| 8 | Portfolio Visualization & Chat UI | 8/8 | passed | Treemap heatmap (binary up/down + cold-cache neutral) + Recharts P&L line chart (dotted $10k reference, stroke flips at break-even) + collapsible AI chat drawer with action cards, XSS guard, prefers-reduced-motion. 111/111 Vitest tests across 19 files. |
| 9 | Dockerization & Packaging | 4/4 | human_needed | Multi-stage Dockerfile (Node 20 → Python 3.12 slim) + canonical `docker run` invocation + idempotent macOS/Linux + Windows start/stop scripts + `.env.example` with safe placeholders. |
| 10 | E2E Validation | 10/10 | passed | 7 Playwright specs × 3 browser projects = 21 (spec, project) pairs. Canonical `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 with `21 passed / 0 failed / 0 flaky / Container test-appsvc-1 Healthy` on **two consecutive runs with no inter-run cleanup**. |

---

## 4. Requirements Coverage

REQUIREMENTS.md ticked items (from `- [x]`):

- ✅ **APP-01..04** — FastAPI + lifespan + `.env` loading + browser-consumable SSE
- ✅ **PORT-01..05** — full portfolio + trading + history + snapshot cadence
- ✅ **WATCH-01..03** — watchlist GET/POST/DELETE
- ✅ **FE-01, FE-02, FE-05, FE-06, FE-09, FE-11** — Next.js scaffold, SSE client, heatmap, P&L chart, chat panel, demo polish
- ✅ **OPS-01..04** — Dockerfile, single-container run, start/stop scripts, `.env.example`
- ✅ **TEST-02** — frontend component tests (111/111 Vitest)
- ✅ **TEST-03, TEST-04** — Playwright harness + all §12 scenarios green reproducibly

REQUIREMENTS.md unticked items (15) — see **Section 6 (Tech Debt)**: most are documentation drift, not functional gaps.

| ID | Category | Reality |
|---|---|---|
| **DB-01..03** | Database | ✅ Working (Phase 2 verified `passed`); REQUIREMENTS.md not ticked |
| **CHAT-01..06** | AI chat | ✅ Working (Phase 5 ships chat, exercised by `06-chat.spec.ts`); Phase 5 has no VERIFICATION.md and REQUIREMENTS.md not ticked |
| **FE-03, FE-04, FE-07, FE-08, FE-10** | Frontend panels | ✅ Working (Phase 7 ships watchlist, main chart, positions table, trade bar, header — visible in production demo); Phase 7 verification status `human_needed`, never moved to `passed` |
| **TEST-01** | Backend unit tests | ⚠️ Partial — 73 pre-existing market-data tests + portfolio + watchlist tests added; coverage of LLM parsing + LLM mock mode never explicitly audited |

No MILESTONE-AUDIT.md was generated for this milestone. `/gsd-audit-milestone` is the natural follow-up before archive.

---

## 5. Key Decisions Log

(Aggregated from per-phase CONTEXT.md `D-` entries.)

- **D-01..D-12 across phases**: tech-stack picks (FastAPI, uv, Next.js export, SQLite stdlib, Lightweight Charts canvas, Recharts SVG, Zustand, TanStack Query, LiteLLM, Cerebras).
- **Phase 1 D-XX**: `lifespan` startup builds a single shared `PriceCache`, selects market source by `MASSIVE_API_KEY`, mounts SSE router after schema init.
- **Phase 2 D-XX**: tables are created lazily on first boot if missing; default user (`cash_balance=10000.0`) and 10 default tickers seeded; no migrations.
- **Phase 3 D-XX**: portfolio reads from the in-memory cache (with `avg_cost` fallback for cold tickers); snapshots are written inline post-trade plus a 60s piggyback on the price loop.
- **Phase 5 D-XX**: structured outputs schema enforces `trades[]` + `watchlist_changes[]`; `LLM_MOCK=true` returns deterministic mock responses; `cerebras` skill is the canonical invocation path.
- **Phase 6 D-01..D-13**: brand-hex build gate; `EventSource` + Zustand price store; Tailwind v4 `@theme` + `:root` dual-declaration so tree-shaking does not drop reserved tokens.
- **Phase 7 D-01..D-XX**: 3-column grid, tabbed center column, accent-blue underline on the active tab, accent-purple submit buttons, price-flash 500ms.
- **Phase 8 D-01..D-13**: action-card pulse 800ms, ChatDrawer 300ms width transition, ThinkingBubble dots, XSS-guard via plain-text rendering, prefers-reduced-motion guard.
- **Phase 9 D-XX**: bash 3.2-portable scripts; `--build` and `--no-open` flags; PowerShell 5.1+ mirror; `cp .env.example .env` boots simulator-mode demo with no edits.
- **Phase 10 D-01..D-10**: full-browser matrix (chromium/firefox/webkit), test-only HSTS-bypass via service rename `app → appsvc`, baseURL wiring, no per-project compose orchestration, no test-only reset endpoint, compose-side healthcheck only.
- **Phase 10 (Plan 10-09)**: per-project viewport bump 1280×720 → 1440×900 (closes Mode A — layout overlap, NOT the originally-blamed Recharts tooltip), `tmpfs: - /app/db` (closes Mode A.2 — cross-run SQLite carry-over via persistent anonymous volume), `<Tooltip formatter={...}>` USD-formatting (closes WR-01 advisory).

---

## 6. Tech Debt & Deferred Items

### 6.1 — Verification debt
- **Phase 5 (AI chat) has no VERIFICATION.md.** The chat works (proven by `06-chat.spec.ts` green across all 3 browsers + 16 Vitest tests in Phase 8) but no formal verifier pass exists. Run `/gsd-verify-work 5` to backfill.
- **Phase 7 (market-data trading UI) and Phase 9 (dockerization) have `status: human_needed`** in their VERIFICATION.md — automated checks pass but human acceptance was never recorded. Run `/gsd-verify-work 7` and `/gsd-verify-work 9`.

### 6.2 — REQUIREMENTS.md drift
15 of 40 requirements remain unticked despite the implementation existing and passing tests. Recommend a sweep pass to reconcile REQUIREMENTS.md with reality (see Section 4 table).

### 6.3 — Post-milestone fixes not retrofitted into a phase
Two source-impacting commits landed AFTER the verifier marked Phase 10 `passed`. Both are green under the canonical harness, but neither belongs to a phase:

| Commit | Fix | Why it surfaced post-verification |
|---|---|---|
| `73abc58` | Heatmap + P&L charts render at deterministic 360px height | The Playwright spec asserted `toBeVisible()` on the wrapper div, which passed even when Recharts emitted a 0×0 inner div under React 19 + ResponsiveContainer + flex-1 parent. The user noticed the empty charts in the live demo. **Verification gap also closed in `05-portfolio-viz.spec.ts` (now asserts `svg rect` and `svg path` count > 0).** |
| `e79ad18` | Light theme (white surfaces / dark text) | User-requested polish after verification; not a regression. CSS variable flip in `globals.css` + matching hex updates in chart components. |

If a v1.1 / Phase 10.1 is desired, both commits can be retroactively assigned. Otherwise, surface them as pre-archive notes.

### 6.4 — Verification gaps to watch
- **`toBeVisible()` is insufficient for SVG-rendered components.** Always pair it with a content-presence assertion (e.g. `svg rect`, `svg path` count > 0).
- **Recharts `<ResponsiveContainer width="100%" height="100%">` inside a `flex-1` parent under React 19 measures -1×-1 on first render and never recovers.** Use explicit pixel heights (`h-[360px]`) or `minHeight` on the container.

### 6.5 — Out of scope (deliberate)
- Auth / multi-user (`user_id="default"` hardcoded; schema is user-keyed for a future migration)
- Limit / stop / order-book / partial fills (market-only by design)
- Fees / commissions / slippage / borrow costs
- Real money / brokerage integration
- Token-by-token LLM streaming (Cerebras inference + loading dots is enough)
- WebSockets (SSE is sufficient)
- Postgres / external DB server (SQLite + volume)
- Cloud deploy (localhost-Docker only in v1)
- Production-grade responsive / a11y pass (desktop-first, demo-grade polish)
- Trade confirmation dialogs (deliberately omitted so AI-driven trade execution feels immediate)
- Order-history UI beyond the positions table

---

## 7. Getting Started

### Run the demo (one command)

```bash
cp .env.example .env                    # add OPENROUTER_API_KEY
./scripts/start_mac.sh                  # macOS / Linux
./scripts/start_windows.ps1             # Windows PowerShell
```

Open **http://localhost:8000**. Default state: 10-ticker watchlist + $10,000 cash.

Stop:
```bash
./scripts/stop_mac.sh                   # macOS / Linux
./scripts/stop_windows.ps1              # Windows
```

The SQLite db lives in the `finally-data` Docker volume — your portfolio + chat history persist across restarts. (To start fresh: `docker volume rm finally-data`.)

### Run the E2E harness (canonical, exactly as Phase 10 verifies)

```bash
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
```

Expect: `21 passed (~25s) / 0 failed / 0 flaky / Container test-appsvc-1 Healthy`, exit code 0.

### Project layout

```
finally/
├── frontend/                 # Next.js TS, output: 'export'
│   └── src/
│       ├── app/              # globals.css = theme tokens
│       ├── components/
│       │   ├── chat/         # ChatDrawer, ChatThread, ActionCard, ChatInput
│       │   ├── portfolio/    # Heatmap, HeatmapCell, PnLChart, PnLTooltip
│       │   └── terminal/     # Header, TabBar, Watchlist, MainChart, PositionsTable, TradeBar, Sparkline
│       └── lib/              # api/, price-store (Zustand), fixtures
├── backend/                  # FastAPI uv project
│   └── app/
│       ├── main.py           # lifespan startup
│       ├── market/           # PriceCache + Simulator + Massive (pre-existing, 73 tests)
│       ├── portfolio/        # service + router
│       ├── watchlist/        # service + router
│       └── chat/             # LiteLLM/OpenRouter integration + structured outputs
├── test/                     # Playwright specs + docker-compose.test.yml
├── scripts/                  # start/stop_{mac,windows}
├── Dockerfile                # multi-stage Node 20 → Python 3.12 slim
└── planning/PLAN.md          # original spec (canonical reference)
```

### Tests

```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test

# E2E (canonical)
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright
```

### Where to look first
- **`planning/PLAN.md`** — the original specification, adopted wholesale as v1 scope. Endpoint shapes, schema, SSE event contents, structured-output schema all live here.
- **`backend/app/main.py`** — lifespan startup; the moment the system comes alive.
- **`frontend/src/components/terminal/Terminal.tsx`** — the 3-column grid + tab layout that every other component plugs into.
- **`frontend/src/lib/price-store.ts`** — the Zustand store the SSE client writes into and every panel reads from.
- **`test/05-portfolio-viz.spec.ts`** — the spec that proves heatmap + P&L render (now with SVG-presence assertions).

---

## Stats

- **Timeline:** 2026-04-19 → 2026-04-28 (9 days from first phase commit to v1.0 milestone close)
- **Phases:** 10/10 complete
- **Plans:** 47/47 complete
- **Commits in milestone window:** 309
- **Files changed (cumulative diff from first phase commit):** 348 (+86,084 / −139)
- **Contributors:** Sherwood Zern (operating GSD-orchestrated coding agents)
- **Canonical harness final result:** `21 passed (24.6s)` on 2026-04-27, reproduced `21 passed (24.8s)` on 2026-04-28 — both green across chromium + firefox + webkit, both with `Container test-appsvc-1 Healthy`.
