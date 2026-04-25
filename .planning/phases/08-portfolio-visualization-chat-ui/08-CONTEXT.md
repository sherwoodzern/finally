# Phase 8: Portfolio Visualization & Chat UI - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the three "wow" surfaces of the trading terminal — portfolio
heatmap (FE-05), P&L line chart (FE-06), and a docked AI chat panel
(FE-09) — and ship them as static files served by FastAPI on the same
port as the API (APP-02). Demo polish (FE-11) and frontend component
tests (TEST-02) round out the phase.

**In scope (FE-05, FE-06, FE-09, FE-11, APP-02, TEST-02):**

- Recharts `<Treemap>` heatmap and `<LineChart>` P&L chart, both wired to
  existing endpoints (`/api/portfolio` for heatmap, `/api/portfolio/history`
  for P&L).
- Right-edge collapsible chat panel (~380px) with `POST /api/chat` +
  `GET /api/chat/history` integration; inline rendering of executed and
  failed `trades[]` and `watchlist_changes[]` per Phase 5 D-07 response
  shape.
- Demo polish: skeleton-per-panel cold start, agentic-trade visuals
  (action-card pulse + position-row flash), 3-dot LLM loading bubble,
  smooth chat-drawer slide.
- FastAPI `StaticFiles` mount of `frontend/out/` at `/` (APP-02),
  removing the G1 dev redirect chain in prod.
- Frontend component tests for: price flash, watchlist CRUD UI surfaces
  (existing watchlist + chat-driven add/remove confirmations),
  portfolio display calculations (heatmap weights, P&L %), chat
  rendering + loading state — Vitest + RTL + MockEventSource pattern
  from Phase 6.

**Out of scope (later phases):**

- Multi-stage Dockerfile, start/stop scripts, `.env.example` → Phase 9
  (OPS-01..04).
- Playwright E2E coverage → Phase 10 (TEST-03, TEST-04).
- Backend changes — `/api/chat`, `/api/portfolio/*`, `/api/watchlist/*`,
  SSE shape are stable contracts from Phases 1–5.
- Token-by-token chat streaming (CHAT-07, v2).
- Responsive stacking, a11y polish, mobile/tablet (POLISH-01, v2).
- Dedicated trade-history view (HIST-01, v2).

**Carry-over from Phase 7 (G1):**

The dev-only SSE redirect chain (`trailingSlash: true` in
`next.config.mjs` → Next 308 → FastAPI 307 cross-origin) blocks
`npm run dev` SSE. Phase 8 SC#4's static mount (D-14) removes the
chain in prod; D-15 also patches `next.config.mjs`
(`skipTrailingSlashRedirect: true`) so `npm run dev` SSE works
through the rest of Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Heatmap (FE-05)

- **D-01:** **Recharts `<Treemap>`** — single new chart dep, SVG matches
  the P&L chart (D-04), `content` prop allows custom rectangle
  rendering. Rejected: hand-rolled CSS-grid (reinvents layout math),
  `react-d3-treemap` (third chart-ish dep without payoff for ~10–20
  positions).
- **D-02:** **Binary up/down coloring.** Rectangle background =
  `--color-up` when `unrealized_pnl >= 0` else `--color-down`
  (Phase 7 D-02 palette). One palette → four surfaces consistent
  (price flash, sparkline stroke, P&L text, heatmap). Rejected:
  P&L gradient (slows quick-read, demo-hostile), sector coloring
  (no taxonomy, doesn't trace to FE-05 acceptance).
- **D-03:** **Label = ticker + P&L %, click selects ticker.** Bold
  ticker on top, P&L % below (e.g., `AAPL  +2.4%`). Click reuses
  Phase 7's `selectedTicker` state to drive the main chart. Cash
  excluded — heatmap is positions-only; cash lives in the header.
  Recharts `content` prop hides labels automatically on small
  rectangles.

### P&L Line Chart (FE-06)

- **D-04:** **Recharts `<LineChart>` over all snapshots.** X-axis =
  `recorded_at`, Y-axis = `total_value`, all rows from
  `GET /api/portfolio/history` (no time-window selector — Phase 7
  D-Main-Chart parallel: timeframe UX is a polish-pass concern).
  Snapshots already accumulate from post-trade + 60s cadence
  (PORT-05).
- **D-05:** **Dotted $10k starting reference line.** Horizontal
  `<ReferenceLine y={10000}>` so "am I up or down vs starting?" is
  instantly visible. Rationale: the simulated portfolio always starts
  at $10k (DB-02 seed); the line is the most demo-clear anchor. The
  line is dashed and low-opacity so the actual P&L line stays
  dominant.
- **D-06:** **Stroke flips at break-even.** Solid `--color-up` when
  last `total_value >= 10000` else `--color-down`. Same palette as
  heatmap and Phase 7 surfaces; reads as "in the green / in the red".

### Chat Panel (FE-09)

- **D-07:** **Right-edge drawer, default open, push layout.** ~380px
  column, opens by default so the demo lands with the AI visible.
  Header toggle collapses to a thin icon strip; expanding slides back
  via `transition-[width] duration-300`. The page becomes ~1760px
  wide when open (consistent with Phase 7's desktop-first boundary).
  Rejected: default-closed overlay (loses first-impression "wow"),
  bottom drawer (eats viz space, breaks PLAN.md §10 "sidebar"
  framing).
- **D-08:** **Loading indicator = animated 3-dot "thinking" bubble.**
  Pure CSS keyframes, sits as the last assistant message in the
  thread while `POST /api/chat` is in flight. Cerebras inference is
  fast (~1–3s typical), so this rarely lingers. Rejected: skeleton
  placeholder (reads "loading content" not "AI thinking"),
  Send-button spinner only (eye is on the thread, not the input).
- **D-09:** **History on mount via `GET /api/chat/history`** (Phase 5
  D-19 — ASC-ordered tail, `limit=50` default). Render once on first
  chat-panel render; new messages append locally on `POST /api/chat`
  resolve.

### Action Confirmations in Chat

- **D-10:** **Inline action cards under the assistant message.** For
  each entry in `trades[]` and `watchlist_changes[]` from the Phase 5
  D-07 response, render a compact card inside the assistant message
  bubble. Cards carry the action verb (Buy/Sell/Add/Remove), ticker,
  quantity (trades) or status word (watchlist), and the result. Order
  matches Phase 5 D-09 (watchlist first, then trades).
- **D-11:** **Status styling — color-coded by Phase 5 D-07 status.**
  - `executed` / `added` / `removed` → green left border +
    `--color-up` accent text
  - `exists` / `not_present` → muted gray border (idempotent no-op)
  - `failed` → red left border + `--color-down` accent text + the
    `error` code mapped to the same human strings as Phase 7 D-07
    (`insufficient_cash`, `insufficient_shares`, `unknown_ticker`,
    `price_unavailable`), plus the Phase 5 D-12 codes
    (`invalid_ticker`, `internal_error`).
  No toast; the card IS the surface. Phase 7 inline-error doctrine
  carried forward.

### Agentic "Wow" Moment (FE-11)

- **D-12:** **Action-card pulse + position-row flash on auto-trade.**
  Two coordinated micro-animations when an `executed` trade card
  lands from chat:
  1. The action card pulses once via `--color-up`/`--color-down`
     background (~800ms, longer than Phase 7's 500ms price flash so
     they read as different events).
  2. The corresponding row in the positions table flashes the same
     color for the same ~800ms window. This is the agentic-AI moment
     PROJECT.md calls "non-negotiable" — the eye sees both the chat
     receipt AND the portfolio change.
  3. Header total + cash re-render naturally via TanStack Query
     invalidation (no explicit animation).
- **D-13:** **First-load = skeleton blocks per panel.** Each panel
  renders a muted-grey skeleton matching its final shape: watchlist
  rows as bars, positions table as bars, header values as `—`,
  heatmap as a single grey rectangle, P&L chart as a faint axis. Pure
  CSS, no library. Removes the "flicker of empty/zero" on cold start.
  Skeleton displays until the first SSE tick / first `/api/portfolio`
  resolve / first snapshot arrives.

### Static Mount (APP-02)

- **D-14:** **FastAPI `StaticFiles` mount of `frontend/out/` at `/`
  AFTER API routers.** Mount in `lifespan.py` after all `/api/*`
  routers so route precedence is correct (FastAPI matches routes in
  registration order; `StaticFiles` at `/` is a catch-all that must
  come last). `html=True` so visiting `/` serves `out/index.html`.
  Frontend build artifacts referenced by relative path; Phase 9
  OPS-01 will copy `frontend/out/` into the Python image's `static/`
  dir at build time, but Phase 8 can point at `frontend/out/`
  directly during development.
- **D-15:** **Resolve G1 dev-redirect during APP-02.** Set
  `skipTrailingSlashRedirect: true` in `next.config.mjs` so the Next
  dev server stops appending the trailing slash that breaks the
  FastAPI rewrite chain (Phase 7 STATE.md G1). Production static
  mount (D-14) sidesteps the chain entirely. Result: `npm run dev`
  SSE works, and `/api/stream/prices` works through the prod mount —
  UAT 1/2/3/5 from Phase 7 become testable.

### Frontend Tests (TEST-02)

- **D-16:** **Vitest + RTL + MockEventSource pattern (Phase 6
  D-test).** Coverage:
  - **Price-flash animation trigger** — already present from Phase 7;
    re-verified here on the new positions-row auto-trade flash (D-12)
    so we don't regress the existing test.
  - **Watchlist CRUD UI** — covered indirectly via chat-driven
    add/remove (D-10, D-11) action-card rendering for `added` /
    `removed` / `exists` / `not_present` / `failed` statuses; plus
    the existing watchlist panel render.
  - **Portfolio display calculations** — heatmap weight (`quantity *
    current_price` over total positions value); P&L %
    (`(current_price - avg_cost) / avg_cost * 100`); reference-line
    condition for stroke color (D-06).
  - **Chat rendering + loading state** — thread renders user/assistant
    turns from history, 3-dot bubble appears during in-flight
    `POST /api/chat`, action cards render the right styling per
    status.
  No Playwright in this phase (TEST-03 belongs to Phase 10).

### Dependencies

- **D-17:** **Add `recharts` as a frontend prod dep.** Phase 7 added
  `lightweight-charts`; this is the second and final chart dep. No
  others — the chat UI is pure React + Tailwind.

### Claude's Discretion

The planner may pick conventional defaults without re-asking on:

- **Heatmap empty state** ("No positions yet — use the trade bar or
  ask the AI to buy something") and cold-cache fallback (a position
  with `current_price == null` — fall back to `avg_cost`, paint
  neutral gray).
- **P&L chart with 0/1 snapshots** — show the skeleton + empty state
  until at least 2 points exist.
- **P&L chart tooltip detail** — date + total_value formatted as
  `$X,XXX.XX`, optional delta vs $10k.
- **Layout placement of heatmap and P&L chart** — most natural fit is
  a tabbed center column (Main Chart / Heatmap / P&L) keeping the
  existing 3-col grid for desktop, but the planner may also place
  them as a stacked second row below the chart. Either is acceptable
  as long as the chat drawer (D-07) coexists at the right edge.
- **Action-card layout details** — icon, padding, monospace numerics
  consistent with the rest of the terminal.
- **Failed-action error message strings** — reuse the Phase 7 D-07 map
  verbatim where codes overlap; supply a sensible default for the new
  Phase 5 codes.
- **Chat input UX** — Enter to send, Shift+Enter for newline (chat-app
  default).
- **Empty chat state** — a single welcome line ("Ask me about your
  portfolio or tell me to trade.") — no suggested-prompt buttons in
  v1 (defer to a polish pass).
- **Manual-trade flash** — for consistency with D-12, the planner may
  also flash position-row on manual `POST /api/portfolio/trade`
  success; this is the inverse of Phase 7 D-08 ("implicit
  confirmation") but Phase 8's polish budget supports it.
- **Drawer toggle keyboard shortcut** — optional `Cmd+K` / `Ctrl+K` to
  focus the chat input; not required.

### Folded Todos

None — todo cross-reference returned 0 matches.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (source of truth)
- `planning/PLAN.md` §2 — Visual design: dark theme, demo polish,
  "every pixel earns its place", agentic AI as the core experience.
- `planning/PLAN.md` §6 — SSE contract (~500ms cadence, session-start
  price). Chat panel and viz components subscribe via `usePriceStore`,
  never re-open EventSource.
- `planning/PLAN.md` §7 — DB schema for `portfolio_snapshots` and
  `chat_messages`. Backs D-04 (P&L chart data) and D-09 (history
  mount).
- `planning/PLAN.md` §8 — REST endpoints: `/api/portfolio`,
  `/api/portfolio/history`, `/api/chat`, `/api/chat/history`,
  `/api/watchlist`. Backs D-04, D-09, D-10, D-11.
- `planning/PLAN.md` §9 — LLM integration, structured output schema,
  "instant, fluid demo" auto-execution. Backs D-10 (inline
  confirmations) and D-12 (agentic wow moment).
- `planning/PLAN.md` §10 — Frontend design notes: Recharts SVG for the
  P&L chart, "docked/collapsible sidebar" for chat. Confirms D-04 and
  D-07.
- `planning/PLAN.md` §11 — Multi-stage Docker; Phase 8 ships APP-02
  (static mount) and Phase 9 ships OPS-01 (Dockerfile that copies
  `frontend/out/` into `static/`).

### Project planning
- `.planning/REQUIREMENTS.md` — FE-05, FE-06, FE-09, FE-11, APP-02,
  TEST-02 (the six requirements this phase delivers).
- `.planning/ROADMAP.md` — Phase 8 success criteria (heatmap, P&L
  chart, chat panel, FastAPI same-origin static mount, frontend
  component tests).
- `.planning/STATE.md` — G1 carry-over (Phase 7 dev-redirect chain),
  recommended fix candidate `skipTrailingSlashRedirect: true`. Backs
  D-15.

### Prior-phase context (read these — they constrain Phase 8)
- `.planning/phases/03-portfolio-trading-api/03-CONTEXT.md` —
  `/api/portfolio` shape, `/api/portfolio/history` ordering and
  bounds, snapshot recording cadence (PORT-05). Backs D-04, D-13.
- `.planning/phases/05-ai-chat-integration/05-CONTEXT.md` —
  D-07 (response payload shape: per-action `status` + `error` codes),
  D-09 (watchlist-first auto-exec order), D-12 (per-action error code
  map), D-19 (`GET /api/chat/history` semantics: ASC tail, `limit=50`
  default). Backs D-09, D-10, D-11.
- `.planning/phases/06-frontend-scaffold-sse/06-CONTEXT.md` —
  D-13 (Zustand store shape), D-14 (session_start_price client-side),
  D-18 (connection status), D-19 (narrow try/catch at wire boundary).
  Phase 8 components subscribe — never re-open EventSource.
- `.planning/phases/07-market-data-trading-ui/07-CONTEXT.md` —
  D-01 (price-flash primitive — D-12 reuses with longer duration for
  trade flash), D-02 (`--color-up`/`--color-down` palette — D-02,
  D-06, D-11, D-12 inherit), D-08 (Phase 7 trade implicit-confirmation
  — Phase 8 D-12 overrides for chat-driven trades and may extend to
  manual). Existing terminal layout grid in
  `frontend/src/components/terminal/Terminal.tsx`.

### Reusable code surfaces (read-only — Phase 8 extends without breaking)
- `frontend/src/lib/price-store.ts` — Zustand store. Phase 8 reads via
  existing selectors; may add a `flashTrade(ticker, dir)` slice for
  D-12 if not already present from Phase 7.
- `frontend/src/lib/api/portfolio.ts` — extend with
  `getPortfolioHistory()`. Mirror the pattern in `watchlist.ts`.
- `frontend/src/lib/api/` — add a new `chat.ts` for `getChatHistory()`
  and `postChat()` clients.
- `frontend/src/lib/sse-types.ts` — stable; no changes.
- `frontend/src/components/terminal/Terminal.tsx` — current 3-col
  grid; Phase 8 wraps or adjusts to host the chat drawer (D-07) and
  place heatmap+P&L (Claude's Discretion).
- `frontend/src/app/providers.tsx` — TanStack Query client already
  configured (10s `staleTime`, `refetchOnWindowFocus: false`); Phase 8
  adds query keys for `portfolio.history`, `chat.history`.
- `backend/app/lifespan.py` — Phase 8 mounts `StaticFiles` after the
  existing `/api/*` routers (D-14). Single edit to add the mount.
- `backend/app/chat/routes.py` — `POST /api/chat`,
  `GET /api/chat/history`. Stable; Phase 8 consumes verbatim.
- `backend/app/portfolio/routes.py` — `GET /api/portfolio/history`
  (PORT-04). Stable; Phase 8 consumes for the P&L chart.

### External docs (research before first task)
- Recharts `<Treemap>` API:
  https://recharts.org/en-US/api/Treemap
- Recharts `<LineChart>` + `<ReferenceLine>`:
  https://recharts.org/en-US/api/LineChart
- FastAPI `StaticFiles` mount with `html=True`:
  https://fastapi.tiangolo.com/tutorial/static-files/
- Next.js `skipTrailingSlashRedirect`:
  https://nextjs.org/docs/app/api-reference/next-config-js/skipTrailingSlashRedirect

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`usePriceStore` + selectors**
  (`frontend/src/lib/price-store.ts`) — heatmap and P&L chart compute
  live values via `selectTick`. Chat panel does not subscribe to
  prices directly.
- **TanStack Query `QueryClientProvider`**
  (`frontend/src/app/providers.tsx`) — wraps the app; Phase 8 adds
  queries for `/api/portfolio/history` and `/api/chat/history` and a
  `postChat` mutation.
- **`frontend/src/lib/api/portfolio.ts`** — existing fetch patterns
  for `getPortfolio()` and `postTrade()`; Phase 8 adds parallel
  functions for history and chat.
- **`Terminal.tsx` 3-col grid** — host for both the new viz surfaces
  and the right-edge chat drawer.
- **Phase 7 `--color-up` / `--color-down` tokens** in `globals.css` —
  heatmap (D-02), P&L chart stroke (D-06), action card status borders
  (D-11), trade-flash backgrounds (D-12) all reuse these.
- **Phase 7 price-flash primitive** in `price-store.ts` `flashDirection`
  slice — D-12 builds on this with a longer duration and a separate
  trigger source (chat auto-trade) so the two flashes read as distinct
  events.

### Established Patterns
- **Vitest + RTL + MockEventSource** (Phase 6 D-test, Phase 7
  inheritance) — same harness for D-16 component tests.
- **Narrow try/catch at wire boundary** (Phase 6 D-19) — chat
  `postChat` mutation wraps `fetch` in one try/catch; no outer
  wrappers.
- **Named exports, no default** — consistent across Phase 6 and Phase
  7.
- **`'use client'` at top of interactive components** — chat panel,
  action cards, heatmap, P&L chart are all client components.
- **`npm run build` → `frontend/out/` go/no-go gate** — Phase 8 plans
  include the same gate; APP-02 mount validates this artifact loads
  end-to-end.

### Integration Points
- `backend/app/lifespan.py` — single edit: add
  `app.mount("/", StaticFiles(directory="frontend/out", html=True))`
  AFTER all routers (D-14).
- `next.config.mjs` — single edit: `skipTrailingSlashRedirect: true`
  (D-15).
- `frontend/src/components/terminal/Terminal.tsx` — restructured to
  host the chat drawer at the right edge and the heatmap+P&L surfaces
  (location is Claude's Discretion).
- `frontend/src/lib/api/portfolio.ts` + new `chat.ts` — extend the API
  client layer.
- `frontend/src/components/chat/` (new) — chat panel, message list,
  action cards, send box.
- `frontend/src/components/portfolio/` (new) — heatmap and P&L chart
  components.

### Anti-Patterns to Avoid (carry-overs)
- Re-opening an EventSource from any new component. Subscribe to
  `usePriceStore` only.
- Toast/notification system. Inline action cards (D-10, D-11) own the
  chat-action surface; trade-bar errors stay inline (Phase 7 D-07).
- Backend changes — chat, portfolio, watchlist, SSE contracts are all
  stable from Phases 1–5.
- Multiple chart libraries beyond `lightweight-charts` + `recharts`.
  No d3, no chart.js.
- Mounting `StaticFiles` at `/` BEFORE API routers — would shadow
  `/api/*` routes.

</code_context>

<specifics>
## Specific Ideas

- **D-12's coordinated 800ms flash** — chosen specifically to read
  distinctly from Phase 7's 500ms price flash. The eye learns within
  seconds of the demo: "fast green/red blink = price tick, slower
  bigger blink with chat card = an action just executed". This
  dual-tempo language is the core agentic-AI affordance.

- **D-05's $10k reference line** is the demo's emotional anchor: the
  viewer instantly sees whether the AI assistant has put them above
  or below their starting balance. The line is dashed, low-opacity so
  the actual P&L line stays dominant.

- **D-07's "default open" chat drawer** trades horizontal real estate
  for first-impression impact. The single most important thing the
  demo communicates is "there's an AI here that can do things";
  collapsing it behind a button risks viewer confusion in the first
  five seconds.

- **D-13's per-panel skeletons** are the polish element non-developers
  actually feel. Generic spinners read as "broken/slow"; matching-
  shape skeletons read as "this is intentional".

- **D-15 (G1 fix)** is small but unblocks every dev-mode SSE workflow
  for the rest of Phase 8. Pair it with the prod static mount (D-14)
  in the same plan so both paths land together and Phase 7's deferred
  UAT 1/2/3/5 become testable.

</specifics>

<deferred>
## Deferred Ideas

- **P&L chart time-window selector** (1h / 1d / All toggles). Phase 8
  ships all-snapshots; selector is a polish-pass / v2 concern.
- **Heatmap with cash slice** — including cash as a "position" in the
  treemap could be informative but conflicts with FE-05 acceptance
  ("rectangles are positions"). Keep in head if v2 wants a "total
  allocation" view.
- **Sector coloring on heatmap** — needs a sector taxonomy we don't
  have; not in v1 requirements.
- **Suggested-prompt buttons in empty chat** ("Show me my biggest
  position", "Sell my losers"). Genuinely valuable for demo handoff
  but adds copywriting + a button row; defer to a later polish phase.
- **Token-by-token chat streaming (CHAT-07)** — already deferred to
  v2; Cerebras inference is fast enough that the 3-dot bubble
  suffices.
- **Toast / global notification system** — explicitly rejected in
  Phase 7; rejected again here. Inline is enough.
- **Trade-history dedicated view (HIST-01)** — v2.
- **Mobile/tablet responsive stacking + a11y polish (POLISH-01)** — v2.
- **Chat keyboard shortcut to focus input** (Cmd+K) — nice-to-have,
  not required for the demo.
- **Heatmap drilling/zooming** — out of scope; Recharts default
  click-to-select is enough.

### Reviewed Todos (not folded)

None — cross-reference returned 0 matches.

</deferred>

---

*Phase: 08-portfolio-visualization-chat-ui*
*Context gathered: 2026-04-25*
