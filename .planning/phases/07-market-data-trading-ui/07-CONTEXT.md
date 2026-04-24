# Phase 7: Market Data & Trading UI - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Render the five visible product surfaces of the trading terminal on one
desktop-first screen, all driven by the Phase 06 SSE store and the Phase
03/04 REST APIs:

1. **Watchlist panel** (FE-03) — one row per watched ticker with current
   price flashing green/red on tick, daily-change % computed from each
   tick's `session_start_price`, and a progressive sparkline accumulated
   from SSE since page load.
2. **Main chart area** (FE-04) — Lightweight Charts canvas for the
   currently selected ticker, fed by the same live SSE stream. Clicking
   a watchlist row selects that ticker.
3. **Positions table** (FE-07) — ticker, quantity, avg cost, current
   price, unrealized P&L ($), unrealized % — one row per position
   returned by `GET /api/portfolio`, updating as prices tick.
4. **Trade bar** (FE-08) — ticker input, quantity input, Buy and Sell
   buttons. Market-only, instant fill via `POST /api/portfolio/trade`,
   no confirmation dialog.
5. **Header** (FE-10) — live total portfolio value, live cash balance,
   connection-status dot (green connected / yellow reconnecting / red
   disconnected) reading directly from the Phase 06 store.

**In scope (FE-03, FE-04, FE-07, FE-08, FE-10):**
- All five panels wired to the Phase 06 Zustand store
  (`usePriceStore`, `selectTick`, `selectConnectionStatus`) and the
  Phase 03 `/api/portfolio`, `/api/portfolio/trade` endpoints.
- Extending the Phase 06 store with a `sparklineBuffers` slice and
  transient `flashDirection` markers — no new store, no new provider.
- Adding two semantic CSS tokens (`--color-up`, `--color-down`) to the
  existing `@theme` block in `globals.css`. No other theme changes.
- Installing `lightweight-charts` as the ONE new npm prod dep (used by
  both the main chart and the sparklines).
- Component tests for price-flash triggering and core render behavior
  — following the Phase 06 Vitest + Testing Library + MockEventSource
  harness.

**Out of scope (belongs to later phases):**
- Portfolio heatmap, P&L line chart, AI chat panel, demo polish,
  frontend component tests for chat flow → Phase 8 (FE-05, FE-06,
  FE-09, FE-11, TEST-02).
- FastAPI `StaticFiles` mount of the export at `/` → Phase 8 (APP-02).
- Node 20 Docker build stage that copies `frontend/out/` into the
  Python image → Phase 9 (OPS-01).
- Playwright E2E for buy/sell, reconnect, empty state → Phase 10
  (TEST-03, TEST-04).
- Backend changes — SSE shape, API endpoints, and trade semantics are
  all stable contracts from Phases 01-04 and Phase 06.

</domain>

<decisions>
## Implementation Decisions

### Price Flash Animation

- **D-01:** **CSS class + setTimeout** — on each tick, `ingest()` sets
  a transient `flashDirection: Record<string, 'up'|'down'>` entry in
  `usePriceStore` for the ticker whose price changed, and schedules a
  500ms `setTimeout` that clears just that entry. The watchlist row
  and positions row subscribe via selector and apply a Tailwind class
  (`bg-up/10` or `bg-down/10`) with `transition-colors duration-500`.
  No new animation dependency; matches the "be simple" CLAUDE.md rule
  and the Phase 06 narrow-state pattern.
  Rejected: key-prop re-mount (churns DOM 20×/sec for 10 tickers);
  Framer Motion (~30 KB dep for one flash, not needed elsewhere in
  Phase 7 or Phase 8).

### Up/Down Color Palette

- **D-02:** Extend `@theme` in `src/app/globals.css` with
  `--color-up: #26a69a` (muted teal-green) and
  `--color-down: #ef5350` (desaturated coral-red) — the Lightweight
  Charts defaults and universal trading-terminal convention. These
  same tokens drive the price-flash backgrounds (D-01), the sparkline
  stroke color (green when last-tick price ≥ session_start, red
  otherwise), the positions table unrealized-P&L text color, and the
  main chart price line color. UI-SPEC §4 already reserved these two
  names as placeholders with no values — this assigns them.
  Rejected: repurposing brand accents (loses "trading green/red"
  readability); deferring to Claude (same answer, not worth extra
  cycle).

### Sparkline Data Buffer

- **D-03:** **Rolling buffer inside `usePriceStore`** as
  `sparklineBuffers: Record<string, number[]>`. On each `ingest()`
  call, append `raw.price` to the ticker's array and trim to the last
  120 entries (~60 seconds at the backend's 500ms cadence). Selector
  exposed as `selectSparkline(ticker)` so each sparkline subscribes
  only to its own ticker's slice — no cross-ticker re-renders. The
  buffer survives component unmounts (important once watchlists
  become long and virtualization or pagination is considered).
  Rejected: separate `useSparklineStore` (two stores to keep in sync,
  doubles testing surface); in-component `useRef` buffer (resets on
  every unmount, stale-looking on first reappearance).

### Sparkline Rendering

- **D-04:** **Lightweight Charts** — same library the main chart
  (FE-04) uses per ROADMAP SC#2. Each sparkline is a minimal `createChart`
  instance inside a fixed-size `<div>` with time scale, price scale,
  grid, crosshair, and watermark all disabled. One canvas per
  sparkline; canvas rendering handles 10+ sparklines at 500ms cadence
  without React reconciler pressure. One new npm prod dep
  (`lightweight-charts`) total for Phase 7.
  Rejected: hand-rolled SVG polyline (re-invents axis/scaling/line
  smoothing we'll want later when sparklines need a hover crosshair);
  Recharts (SVG + full React reconciler per tick — 10 × 500ms = 20
  SVG-tree re-renders/sec; also would force Phase 8's Recharts dep
  earlier than needed).

### Trade Bar — Ticker Input

- **D-05:** **Free-text `<input>` that upper-cases as the user types**,
  with client-side validation via the same regex the backend uses
  (`^[A-Z][A-Z0-9.]{0,9}$`, see `backend/app/watchlist/service.py`
  `normalize_ticker`). No watchlist-only restriction — the user can
  trade any valid symbol (e.g., a ticker they know about but haven't
  added yet). On blur or submit, reject with inline error if the
  regex fails (never hit the server for obviously-bad input).
  Rejected: typeahead dropdown from watchlist only (blocks off-list
  trading, PLAN.md doesn't require that); combobox with free-text +
  suggestions (nice but more code than Phase 7 needs — revisit in
  Phase 8 if the demo feels clunky).

### Trade Bar — Quantity Input

- **D-06:** **`<input type="number" min="0.01" step="0.01">`** to
  match the backend's `Field(gt=0)` constraint and PLAN.md §7 /
  `backend/app/portfolio/models.py:21` which allows fractional shares.
  Browser spinner controls + HTML `min`/`step` validation prevent
  zero or negative values without JavaScript. Client parses with
  `parseFloat`; server is still the source of truth for the final
  validation (`TradeValidationError` → 400).
  Rejected: integer-only (contradicts backend + PLAN.md); free text
  with manual parsing (more code, worse UX, no clear upside).

### Trade Bar — Error Surface

- **D-07:** **Inline error message below the Buy/Sell buttons.** A
  single `<p role="alert">` element rendered when the last submit
  produced a 400 response. Cleared on next successful submit or
  when either input changes. The text maps directly from the
  backend's `detail.code`:
    - `insufficient_cash` → "Not enough cash for that order."
    - `insufficient_shares` → "You don't have that many shares to sell."
    - `unknown_ticker` → "No such ticker."
    - `price_unavailable` → "Price unavailable right now — try again."
  Phase 7 does NOT introduce a toast system; Phase 8's chat panel
  may or may not add one, but the trade bar owns its own error space.
  Rejected: toast (new dep/provider for something no other Phase 7
  panel needs); inline + toast hybrid (most code, hardest to test).

### Post-Trade Feedback

- **D-08:** **Implicit — the UI updates are the confirmation.** On
  200 response from `/api/portfolio/trade`:
    1. Invalidate / re-fetch `/api/portfolio` so the positions table
       re-renders with the new quantity / avg cost and the header
       re-renders with the new cash balance.
    2. Clear the ticker and quantity inputs in the trade bar.
    3. Leave focus on the ticker field for rapid repeat trades.
  No toast, no confirmation banner, no dialog. This matches PLAN.md
  §9 "instant, fluid demo" and the `planning/PLAN.md` §2 aesthetic
  ("every pixel earns its place").
  Rejected: position-row flash (adds coupling between trade bar and
  positions table, and reuses D-01 primitive for a different meaning
  — "trade occurred" vs "price ticked"); inline success line (noisy
  after repeated trades, clutters a data-dense screen).

### Claude's Discretion

Planner may pick the conventional answer without re-asking.

- **Panel layout.** Desktop-first Bloomberg-adjacent grid. Reasonable
  default: three-column CSS grid — left column watchlist, center
  column header strip on top of main chart, right column positions
  table on top of trade bar. Keep the Phase 8 chat panel's future
  dock in mind (right edge, collapsible) but do not build it here.
  PLAN.md §2 says "functional on tablet" — a simple `min-width: 1024px`
  with horizontal scroll below that is acceptable for a demo terminal;
  true responsive stacking can come later.

- **Portfolio data flow.** TanStack Query is the conventional
  react-query choice for the single `/api/portfolio` GET + the `/trade`
  mutation. A 15-second `refetchInterval` plus post-mutation
  invalidation is the simplest setup. If TanStack Query feels heavy
  for two endpoints, a plain `useEffect` + `setInterval` is fine too —
  the planner can decide. Unrealized P&L for the positions TABLE is
  computed CLIENT-SIDE on every render: `current_price` comes from
  the Phase 06 store (selector), `avg_cost` and `quantity` from the
  `/api/portfolio` response. The backend's `PositionOut.unrealized_pnl`
  is used only as a fallback when the store has no tick for that
  ticker yet (cold start).

- **Connection-status dot.** Small `<span>` with `rounded-full w-2.5
  h-2.5` backgrounds `bg-up` (connected) / `bg-accent-yellow`
  (reconnecting) / `bg-down` (disconnected). Hover `title` attribute
  with the status word. Placed in the header strip next to the cash
  balance. Clicking it does nothing in Phase 7; reserve behavior for
  a later polish pass.

- **Positions table interactions.** Clicking a row selects that
  ticker in the main chart (same selector as watchlist click). Sort:
  default by weight (quantity × current_price) descending, no sort
  UI in Phase 7. Empty state: "No positions yet — use the trade bar
  to buy shares."

- **Main chart content.** Line (not candles — we only have ticks).
  Timeframe = session-since-page-load (same data as sparklines, just
  bigger and for one ticker at a time); no timeframe selector in
  Phase 7. Crosshair + tooltip on hover (Lightweight Charts default
  is fine). Y-axis format `$ X,XXX.XX`. No session-start reference
  line — that's a nice-to-have for a later polish pass.

- **Header live totals.** `total_value = cash_balance + sum(position
  qty × current_price from store)`. Re-renders whenever the store
  ticks. Format `$ X,XXX.XX`.

- **Watchlist row layout.** Fixed 48–56px row height, monospace
  numerics (consistent with UI-SPEC §5.2 `/debug` page). Columns:
  ticker (bold), daily-change % (colored by sign), price, sparkline
  (fixed ~80×32px).

- **Routes.** Keep the existing `/` placeholder from Phase 06 and
  replace its body with the terminal UI (or render it on `/terminal`
  and keep `/` as a landing — planner's call). The `/debug` page
  from Phase 06 stays as a developer tool.

- **Tailwind utilities.** Free to add derived tokens (`text-up`,
  `text-down`, `bg-up/10`, etc.) that reference the new `--color-up`
  / `--color-down` variables. No other theme changes.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (source of truth)
- `planning/PLAN.md` §2 — Visual design (dark theme, muted borders,
  price-flash ~500ms, connection dot). Backs D-01, D-02.
- `planning/PLAN.md` §6 — SSE contract (~500ms cadence, event shape,
  session-start price). Backs the tick-driven flash + sparkline logic.
- `planning/PLAN.md` §7 — DB schema; fractional `quantity` in positions
  and trades. Backs D-06.
- `planning/PLAN.md` §8 — REST endpoints (`/api/portfolio`,
  `/api/portfolio/trade`, `/api/watchlist`). Backs D-07, D-08, and
  the positions/watchlist wiring.
- `planning/PLAN.md` §10 — Frontend design notes (Lightweight Charts
  for main chart and sparklines, Recharts for later P&L chart).
  Confirms D-04.

### Project planning
- `.planning/REQUIREMENTS.md` — FE-03, FE-04, FE-07, FE-08, FE-10
  (the five requirements this phase delivers).
- `.planning/ROADMAP.md` — Phase 7 Success Criteria (all 5 must
  evaluate TRUE: watchlist flash + sparkline + daily %, main chart
  on click, positions table live, trade bar instant fill, header
  with connection dot).

### Prior-phase context
- `.planning/phases/06-frontend-scaffold-sse/06-CONTEXT.md` —
  D-11 (root provider), D-12 (Zustand), D-13 (store shape extended
  here with sparkline + flash slices), D-14 (session_start_price
  — required for FE-03 daily %), D-18 (connection status — required
  for FE-10 dot).
- `.planning/phases/06-frontend-scaffold-sse/06-UI-SPEC.md` §4 —
  Semantic `--color-up` / `--color-down` placeholder tokens that D-02
  now assigns values to. §8 — exact copywriting strings.
- `.planning/phases/03-portfolio-trading-api/03-CONTEXT.md` —
  `/api/portfolio`, `/api/portfolio/trade`,
  `TradeValidationError` → HTTP 400 mapping with `{error: code,
  message}`. Backs D-07 error-text map.
- `.planning/phases/04-watchlist-api/04-CONTEXT.md` — idempotent
  add/remove semantics; the watchlist panel's row list is
  authoritative from `GET /api/watchlist`.

### Reusable code surfaces (read-only — do NOT modify)
- `frontend/src/lib/price-store.ts` — Zustand store; Phase 7 adds
  `sparklineBuffers` and `flashDirection` slices in a backward-
  compatible way.
- `frontend/src/lib/sse-types.ts` — `Tick`, `RawPayload`,
  `ConnectionStatus`, `Direction`. Phase 7 may add a
  `SparklineSnapshot` or similar helper type, but the existing
  exports are stable.
- `frontend/src/lib/price-stream-provider.tsx` — single EventSource
  owner; Phase 7 does not touch this.
- `backend/app/portfolio/routes.py` — `GET /api/portfolio`, `POST
  /api/portfolio/trade`; Phase 7 consumes these verbatim.
- `backend/app/portfolio/models.py` — `TradeRequest`,
  `TradeResponse`, `PositionOut`, `PortfolioResponse`. The
  frontend's fetch types mirror these.
- `backend/app/watchlist/routes.py` + `backend/app/watchlist/models.py`
  — `GET /api/watchlist` returns the user's tickers with latest
  prices; Phase 7 uses these to seed the watchlist panel.
- `backend/app/market/stream.py` + `backend/app/market/models.py:39-49`
  — SSE contract (stable from Phase 1 APP-04).

### External docs (to read during research/planning)
- Lightweight Charts library (main API):
  https://tradingview.github.io/lightweight-charts/
- Lightweight Charts React + Next.js App Router integration patterns
  (dynamic import to avoid SSR, canvas sizing with `ResizeObserver`):
  research this before the first chart task lands.
- Tailwind v4 `@theme` extension with semantic color tokens (already
  precedented by Phase 06 UI-SPEC §4):
  https://tailwindcss.com/docs/theme
- TanStack Query v5 (if the planner picks it over plain fetch):
  https://tanstack.com/query/latest/docs/framework/react/overview

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`usePriceStore` + selectors** (`frontend/src/lib/price-store.ts`)
  — ticker-keyed live state with `selectTick`, `selectConnectionStatus`.
  Phase 7 subscribes extensively. Extends the store with
  `sparklineBuffers` (D-03) and `flashDirection` (D-01) without
  reshaping existing fields.
- **`Tick` interface** (`frontend/src/lib/sse-types.ts`) — carries
  `session_start_price` which FE-03 daily-change % computes as
  `(price - session_start_price) / session_start_price * 100`.
- **`PriceStreamProvider`** (`frontend/src/lib/price-stream-provider.tsx`)
  — owns the single EventSource; Phase 7 components simply subscribe
  via `usePriceStore` and do NOT open their own connection.
- **`ConnectionStatus`** (`frontend/src/lib/sse-types.ts` + store
  status slice) — FE-10's dot reads this directly.
- **Tailwind `@theme` block** (`frontend/src/app/globals.css`) —
  already wires the brand accents. D-02 adds two more tokens here.
- **Dark base + body classes** (`frontend/src/app/layout.tsx`) —
  `<html className="dark">`, `<body className="bg-surface
  text-foreground">`. Phase 7 replaces the body children below
  `PriceStreamProvider` with the terminal UI.

### Established Patterns
- **Narrow try/catch at wire boundary** (Phase 06 D-19) — the
  single try/catch in `price-store.ts.onmessage` is the model.
  Phase 7's trade bar wraps `fetch('/api/portfolio/trade')` in one
  try/catch that maps 4xx body to inline error text; no outer
  wrappers.
- **Named exports, no default** — consistent with Phase 06 store
  and 06-SUMMARY. Phase 7 component modules follow suit.
- **`'use client'` at the top of interactive components** — all
  of Phase 7's panels are client components.
- **Minimal unstyled precedent** — the Phase 06 `/debug` page is
  the reference for monospace numerics + right-aligned numeric
  columns. Phase 7's positions and watchlist inherit the same
  numeric-column treatment.
- **`npm run build` → `frontend/out/` as the go/no-go gate** —
  Phase 06 Plan 01 Task 3 pattern; Phase 7 plans include the same
  gate on the last task.
- **Vitest + `@testing-library/react` + MockEventSource DI** —
  Phase 06 Plan 03 test harness. Phase 7 component tests follow
  the same pattern for price-flash and render-on-tick coverage.

### Integration Points
- `frontend/src/app/page.tsx` — currently the Phase 06 placeholder
  landing page. Phase 7 either replaces its body with the terminal
  UI or moves the terminal to `/terminal` and keeps `/` as a
  landing (planner's discretion).
- `frontend/src/lib/price-store.ts` — surgical extensions only.
  D-01 adds `flashDirection` slice + clearing timer inside `ingest`;
  D-03 adds `sparklineBuffers` slice + `selectSparkline(ticker)` helper.
- `GET /api/portfolio` and `POST /api/portfolio/trade` — consumed
  from the trade bar, positions table, and header. No backend
  changes.
- `GET /api/watchlist` — consumed to seed the watchlist panel's
  row list. Phase 7 does not add/remove tickers via the UI —
  that's what the Phase 8 chat will do.

### Anti-Patterns to Avoid (Phase 06 hard-won)
- Re-opening an `EventSource` from a Phase 7 component. Subscribe
  to `usePriceStore` only. The provider is the single owner.
- Toast/notification systems for trade outcomes — inline error
  (D-07) and implicit success (D-08) are the whole Phase 7 surface
  for user feedback.
- Recharts in Phase 7 — reserved for Phase 8's P&L line chart.
- Backend extension (e.g., adding a `sparkline_history` field to
  `PriceUpdate`). Phase 7 is FRONTEND-ONLY on a stable backend
  contract.
- Installing multiple chart libraries. Lightweight Charts is the
  only new prod dep this phase.

</code_context>

<specifics>
## Specific Ideas

- **D-02's teal `#26a69a` / red `#ef5350`** are the Lightweight Charts
  default series colors. Using them means the sparkline stroke, flash
  highlight, main-chart line, and P&L text are all visually cohesive
  with zero extra theming.

- **D-03's 120-tick / 60-second sparkline window** is chosen so a
  user who arrives at the page sees a meaningful line within about
  10 ticks (5 seconds), and the visible history doesn't exceed one
  minute — keeping the sparkline dense without looking "flatlined"
  at longer windows. If the sparkline feels too twitchy in practice,
  the planner may widen to 240 (~2 min) without any other change.

- **D-08's "implicit confirmation"** is the heart of the FE-08 demo
  experience: buy, blink, see position, sell, blink, see cash.
  Any dialog breaks the "fluid demo" vibe PLAN.md explicitly calls
  out.

- **`--color-up` / `--color-down` power everything up/down**, not
  just flashes: the sparkline stroke color (green if
  last_tick ≥ session_start else red), the positions table unrealized-
  P&L text color, the daily-change % in the watchlist row. One
  palette decision → four visual surfaces consistent.

</specifics>

<deferred>
## Deferred Ideas

- **Position-row flash on trade** — show "this row just changed from
  a trade" distinctly from "price just ticked." Interesting but
  couples trade bar to positions table. Revisit in Phase 8 if the
  demo feels understated.

- **Typeahead / combobox for ticker input.** Nice UX, not required
  for FE-08. Revisit when the watchlist gets long or when Phase 8's
  chat UI suggests a pattern we can borrow.

- **Clickable connection-status dot** (force reconnect, show last-
  tick timestamp popover). Phase 7 ships passive display only.

- **Timeframe selector on the main chart** (1m / 5m / 15m windows).
  Phase 7 ships session-since-page-load only. A zoom/timeframe UX
  belongs in a later polish phase.

- **Toast system** for trade errors or reconnect events. Phase 7
  resists; Phase 8's chat panel may revisit.

- **Responsive stacking below 1024px.** Phase 7 ships desktop-first
  with horizontal scroll on narrow windows. True stacking for
  tablet/mobile layouts is a later phase (not in v1 requirements).

- **Multi-select positions / bulk close.** Out of v1 scope entirely.

- **Backend extension to emit `session_start_price` or
  `sparkline_history`.** Phase 7 continues to compute these client-
  side (matches Phase 06 D-14 rationale).

- **Recharts for sparklines.** Explicitly rejected in D-04; reserved
  for Phase 8's P&L chart.

</deferred>

---

*Phase: 07-market-data-trading-ui*
*Context gathered: 2026-04-24*
