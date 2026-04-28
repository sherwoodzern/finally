# FinAlly — AI Trading Workstation

## Current State

**Shipped:** v1.0 MVP on 2026-04-28 (tag `v1.0`).

A single-Docker-command Bloomberg-style AI trading workstation: live SSE price streaming for 10 default tickers, a simulated $10k portfolio with instant-fill market orders, a three-column terminal layout (watchlist · workspace · positions) plus a collapsible LLM chat copilot that auto-executes trades and watchlist changes via structured outputs. FastAPI serves the Next.js static export from `:8000` from a single multi-stage container. SQLite persists in a Docker volume. Canonical Playwright harness exits 0 reproducibly with `21 passed / 0 failed / 0 flaky` × 2 consecutive runs across 3 browsers.

11 phases / 51 plans complete. 40/40 v1 requirements satisfied. Audit verdict: `passed`.

## Next Milestone Goals

To be defined via `/gsd-new-milestone`. Candidate themes from v1.0 deferred items and v2 backlog:

- **v1.1 Polish & Coverage** — Promote 7 partial / 1 missing Nyquist phases to compliant; resolve Phase 7 + 9 indefinite-acceptance items via per-host human spot-check; clean up the 5-error TypeScript baseline in test files; write the recurring retrospective inline.
- **v1.2 Auth & Multi-User (AUTH-01)** — Login + sessions + per-user data isolation. Schema is already `user_id`-keyed so it's a non-migration addition.
- **v1.3 Streaming Chat (CHAT-07)** — Token-by-token LLM responses (deferred from v1.0 because Cerebras inference was fast enough that loading dots sufficed).
- **v2.0 Cloud Deploy (DEPLOY-01)** — App Runner / Render / Fly.io with managed persistence replacing the Docker volume.

## What This Is

FinAlly (Finance Ally) is a single-user, single-container AI trading workstation — a Bloomberg-style terminal that streams live prices, runs a simulated $10k portfolio, and pairs every screen with an LLM chat copilot that can analyze positions and execute trades on the user's behalf. It was the capstone project for an agentic AI coding course; the medium IS the message — orchestrated coding agents (interacting through files in `.planning/`) produced a production-looking full-stack application end-to-end.

## Core Value

A user runs one Docker command, opens `http://localhost:8000`, and within seconds is watching live prices stream, buying shares, and asking an AI assistant to reshape the portfolio — with trades actually executing from the chat. **Validated in v1.0**: the canonical demo moment shipped intact and is exercised on every E2E run.

## Requirements

### Validated

<!-- All 40 v1 requirements shipped in v1.0. Inherited validated items remain. -->

**Inherited (pre-v1.0):**
- ✓ MARKET-01..06 — Strategy-pattern market data layer + thread-safe `PriceCache` + immutable `PriceUpdate` + `create_stream_router` factory + dynamic ticker lifecycle + 73 tests — `backend/app/market/`

**Shipped in v1.0:**
- ✓ APP-01..04 — FastAPI lifespan + `.env` loading + `/api/health` + browser-consumable SSE — v1.0 (Phase 1, 8)
- ✓ DB-01..03 — SQLite schema + lazy seed + volume-mounted persistence — v1.0 (Phase 2)
- ✓ PORT-01..05 — `/api/portfolio` + `/api/portfolio/trade` + validation + history + 60s + post-trade snapshots — v1.0 (Phase 3)
- ✓ WATCH-01..03 — `/api/watchlist` GET/POST/DELETE with idempotent ops + simulator onboarding — v1.0 (Phase 4)
- ✓ CHAT-01..06 — `/api/chat` synchronous + LiteLLM/OpenRouter/Cerebras structured outputs + auto-execution + persistence + `LLM_MOCK=true` — v1.0 (Phase 5)
- ✓ FE-01..11 — Next.js static export + EventSource + watchlist with sparklines + main chart + heatmap + P&L chart + chat drawer + positions table + trade bar + header + polish — v1.0 (Phase 6, 7, 8)
- ✓ OPS-01..04 — Multi-stage Dockerfile + canonical `docker run` + cross-platform start/stop scripts + `.env.example` — v1.0 (Phase 9)
- ✓ TEST-01..04 — Backend pytest + frontend Vitest (111/111) + Playwright canonical harness (21/21 × 2 runs × 3 browsers) — v1.0 (Phase 5, 8, 10)

### Active

<!-- v1.1+ candidates. Empty for now — populated by /gsd-new-milestone. -->

(No active requirements — start the next milestone with `/gsd-new-milestone`.)

### Out of Scope

<!-- Boundaries that held through v1.0 and reasoning still applies. -->

- **Authentication / multi-user** — single-user, `user_id="default"` hardcoded for v1.0. Schema is user-keyed, so AUTH-01 is a non-migration addition for a future milestone.
- **Limit orders, stop orders, order book, partial fills** — market orders only. Eliminates order-matching complexity. *Reasoning still valid.*
- **Fees, commissions, slippage, borrow costs** — instant fill at the cached mid price. *Reasoning still valid.*
- **Real money / brokerage integration** — simulated portfolio, fake money. *Reasoning still valid.*
- **Token-by-token LLM streaming (CHAT-07)** — deferred. Cerebras inference proved fast enough in v1.0 that loading dots sufficed; canonical harness validates the synchronous-payload approach. CHAT-07 is a v1.x candidate if user feedback demands it.
- **WebSockets** — SSE one-way push proved sufficient through v1.0. *Reasoning still valid.*
- **Postgres / external DB server** — single-file SQLite + Docker volume worked for v1.0. *Reasoning still valid.*
- **Cloud deploy (DEPLOY-01)** — deferred. Container is cloud-ready; deployment is a future milestone.
- **Production-grade responsive / accessibility (POLISH-01)** — desktop-first demo-grade was the v1.0 target. v1.x candidate if scope expands beyond capstone.
- **Trade confirmation dialogs** — deliberately omitted; AI-driven execution feels immediate and agentic. Validated by demo. *Reasoning still valid.*
- **Trade history UI (HIST-01)** — `trades` is persisted but no dedicated view in v1.0. v1.x candidate.

## Context

- **Capstone for an agentic AI coding course — shipped.** The product itself is the medium. Orchestrated coding agents (through files in `.planning/`) produced 11 phases / 51 plans / 364 commits / 14,365 LOC source code in 9 days (2026-04-19 → 2026-04-28).
- **Codebase as of v1.0 close:** 7,721 LOC Python (backend + 295/295 backend chat tests + 158/158 portfolio tests + 73 inherited market tests), 4,292 LOC TypeScript/TSX (frontend + 111/111 Vitest tests across 19 files), 2,352 LOC test code (Playwright + Vitest). 418 files modified across the milestone.
- **Tech stack at v1.0:** Python 3.12 + FastAPI + uvicorn + SQLite (stdlib) + LiteLLM + python-dotenv (backend); Next.js 16 + TypeScript + React 19 + Tailwind v4 (CSS-first @theme) + Zustand 5 + TanStack Query + Lightweight Charts (canvas) + Recharts (SVG) + Vitest 4 (frontend); Playwright + docker-compose.test.yml + tmpfs `/app/db` (E2E).
- **Runtime contract proven:** canonical `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` exits 0 with `21 passed / 0 failed / 0 flaky` reproducibly across two consecutive runs (no inter-run cleanup) at viewport 1440×900 across chromium/firefox/webkit.
- **Known deferred items (accepted policy debt):** Phase 7 visual feel (price-flash, sparklines, main-chart, reconnect-dot in dev) — `human_acceptance: indefinite` recorded 2026-04-28 per G3. Phase 9 Windows pwsh runtime + macOS/Linux browser auto-open + cross-arch buildx — `human_acceptance: indefinite` recorded 2026-04-28 per G4. See `.planning/STATE.md` ## Deferred Items.
- **Known technical debt (non-blocking):** Nyquist coverage 3 compliant / 7 partial / 1 missing — functionally compensated by canonical harness; promotion is a v1.1 candidate. 5-error TypeScript baseline in `MainChart.test.tsx` + `Sparkline.test.tsx` (tuple-index errors) — production `next build` excludes test files. Several Phase 7 plan SUMMARYs lack `requirements-completed` frontmatter — superseded by REQUIREMENTS.md sweep in Plan 11-02.
- **Pre-existing spec.** `planning/PLAN.md` is the canonical reference for endpoint shapes, schema, SSE event contents, and the LLM structured-output schema. v1.0 adopted it wholesale.
- **Codebase map.** `.planning/codebase/*.md` (analysis date 2026-04-19) — pre-v1.0 architecture snapshot. Now superseded by shipped code; refresh before next milestone.

## Constraints

- **Tech stack (backend)**: Python 3.12+, FastAPI, `uv` for package management (project rule: `uv run xxx`, never `python3`; `uv add xxx`, never `pip install`), uvicorn, SQLite via stdlib `sqlite3`, LiteLLM, NumPy, Massive SDK.
- **Tech stack (frontend)**: Next.js with TypeScript in `output: 'export'` mode, Tailwind v4 CSS-first @theme, Lightweight Charts (main chart + sparklines), Recharts (heatmap + P&L), Zustand price store, TanStack Query for REST.
- **Tech stack (LLM)**: LiteLLM → OpenRouter to `openrouter/openai/gpt-oss-120b` with Cerebras as inference provider. Structured outputs for trade/watchlist actions. Invoke via the `cerebras` skill.
- **Runtime**: Single Docker container on port 8000. One Python process. No compose file in production. Multi-stage Dockerfile (Node 20 → Python 3.12 slim).
- **Persistence**: SQLite file at `db/finally.db`, volume-mounted to `/app/db`. No migrations — lazy schema creation on first startup.
- **Transport**: REST under `/api/*`, SSE under `/api/stream/*`, same origin as static frontend. No CORS configuration.
- **Code style**: No over-engineering, no defensive programming, exception managers only when needed. Short modules and functions. Clear docstrings, sparing comments. No emojis in code or logs. Latest library APIs.
- **Process**: Work incrementally — small steps, validate each one. For any bug or unexpected behavior, prove the root cause before fixing.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Adopt `planning/PLAN.md` wholesale as v1 scope | Spec extremely detailed, internally consistent, aligned with capstone demo. | ✓ Good — shipped 40/40 requirements with no scope churn. |
| Full feature set in v1 (chat + heatmap + P&L chart all included) | Capstone demo requires the "wow" of AI-driven trade execution against a polished terminal UI. | ✓ Good — demo moment landed; canonical harness validates end-to-end. |
| LiteLLM + OpenRouter + `openrouter/openai/gpt-oss-120b` (Cerebras) | Matches `cerebras` skill, Cerebras inference fast enough to skip token streaming, OpenRouter abstracts provider. | ✓ Good — synchronous payload pattern proved sufficient; CHAT-07 streaming deferred without complaint. |
| No auth in v1, `user_id="default"` hardcoded | Single-user demo on localhost. Schema user-keyed so auth is a non-migration addition. | ✓ Good — schema is ready for AUTH-01 in a future milestone. |
| Localhost Docker only (no cloud deploy in v1) | Capstone is a local demo; container is self-contained. | ✓ Good — DEPLOY-01 deferred cleanly. |
| Market-data subsystem treated as Validated | 73 tests already green; only gap was browser-level SSE integration (captured as APP-04). | ✓ Good — APP-04 closed in Phase 1; subsystem still 73 tests. |
| Demo-grade polish target (not production-grade responsive/a11y) | Desktop-first capstone demo. | ✓ Good — POLISH-01 deferred; visual feel signed off via Phase 7 indefinite acceptance. |
| All §12 E2E scenarios with `LLM_MOCK=true` in a separate `docker-compose.test.yml` | E2E pack proves the whole stack end-to-end. | ✓ Good — 21/21 green × 2 consecutive runs validates the contract. |
| Per-project Playwright viewport 1440×900 (Plan 10-09) | Aligned test env with `planning/PLAN.md §10` desktop-first contract; avoids spurious 1280×720 layout-overlap failures. | ✓ Good — Mode A misdiagnosis (Plan 10-08) corrected; harness reproducibly green. |
| `tmpfs:/app/db` on test-side appsvc (Plan 10-09) | Gives canonical command's `reproducibly` clause teeth without changing the command, without `down -v` wrapper, without test-only reset endpoint. | ✓ Good — production `Dockerfile:57 VOLUME /app/db` preserved; only test compose overrides. |
| Option B for `human_needed` closure (Plan 11-03 G3+G4) | Preserve enum, ADD `human_acceptance: indefinite` sibling key with dated rationale. | ✓ Good — milestone audit verdict shifted from `tech_debt` to `passed`; honest paper trail. |

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
*Last updated: 2026-04-28 after v1.0 milestone close — all 40 v1 requirements moved to Validated; Active section emptied for v1.1; Out of Scope retained with v1.x routing notes.*
