# Phase 7: Market Data & Trading UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 07-market-data-trading-ui
**Areas discussed:** Flash + sparklines, Trade bar UX
**Areas deferred to Claude's discretion:** Panel layout, Portfolio data flow

---

## Gray Area Selection

| Area | Description | Selected |
|------|-------------|----------|
| Panel layout | 5-panel arrangement on one screen, responsive behavior, Phase 8 chat dock | |
| Portfolio data flow | TanStack Query vs SWR vs plain fetch; client-side vs server-side P&L; refetch-after-trade | |
| Flash + sparklines | Flash mechanism, colors, sparkline buffer, sparkline library | ✓ |
| Trade bar UX | Ticker input, quantity affordance, error surface, post-trade feedback | ✓ |

User chose to leave panel layout and portfolio data flow as Claude's discretion — both have well-trodden defaults that don't need user weigh-in.

---

## Flash + sparklines

### Q1: Price-flash mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| CSS class + setTimeout | Transient `flashDirection` marker in store with 500ms clearing timer; component reads it and applies a Tailwind class with CSS transition. Tiny runtime, no new dep. | ✓ |
| Key-prop re-mount + CSS keyframes | Change a `key` prop each tick; React remounts the cell and `@keyframes` plays from scratch. Churns DOM 20×/sec for 10 tickers. | |
| Framer Motion AnimatePresence | Full animation library (~30 KB) for one flash. Heavier than needed and not required elsewhere in Phase 7 or Phase 8. | |

**Notes:** User picked the recommended default after a clarification round explaining each option in plain language.

### Q2: Flash colors

| Option | Description | Selected |
|--------|-------------|----------|
| Trading-standard teal/red | `--color-up: #26a69a` (teal-green), `--color-down: #ef5350` (coral-red) — Lightweight Charts defaults and universal trading-terminal convention. UI-SPEC §4 already reserved these tokens. | ✓ |
| Brand accents repurposed | Use `#209dd7` blue for up + new red for down. Loses the "trading green/red" readability. | |
| You decide | Claude picks the trading-standard palette in absence of preference. | |

### Q3: Sparkline data buffer

| Option | Description | Selected |
|--------|-------------|----------|
| Rolling buffer in existing store, cap 120 | Extend `usePriceStore` with `sparklineBuffers: Record<string, number[]>`; trim to 120 entries (~60s at 500ms cadence). Selector-based re-renders, survives unmounts. | ✓ |
| Separate store slice, cap 240 | New `useSparklineStore` for a 2-min window. Cleaner separation, two stores to keep in sync. | |
| In-component `useRef` ring buffer | Each sparkline owns its array. Simpler data model; resets on unmount. | |

### Q4: Sparkline rendering library

| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight Charts | Same library as the main chart (per ROADMAP SC#2). One dep total, canvas rendering, no React reconciler pressure. | ✓ |
| Hand-rolled SVG polyline | ~30 lines of code, no library. You maintain scaling/padding/smoothing. | |
| Recharts `<LineChart>` | Forces Phase 8's Recharts dep earlier. SVG + full reconciler at 10 sparklines × 500ms is 20 SVG-tree re-renders/sec. | |

**Notes:** All four Flash + sparkline questions answered with the recommended defaults.

---

## Trade bar UX

### Q1: Ticker input

| Option | Description | Selected |
|--------|-------------|----------|
| Free text, uppercased + regex-validated | `<input>` that upper-cases as the user types; client-side regex `^[A-Z][A-Z0-9.]{0,9}$` matches the backend's `normalize_ticker` rule. Lets user trade any valid symbol. | ✓ |
| Typeahead dropdown from current watchlist only | Faster for the common case but blocks off-list trading. | |
| Free text with passive suggestions | Combobox UX. Best of both, more code. | |

### Q2: Quantity input affordance

| Option | Description | Selected |
|--------|-------------|----------|
| Number input, `step=0.01`, `min=0.01` | `<input type="number" min=0.01 step=0.01>`. Matches backend's `Field(gt=0)` and PLAN.md §7 fractional shares. | ✓ |
| Integer-only number input | `step=1`. Forbids fractional trades in the UI even though backend supports them — contradicts PLAN.md §7. | |
| Text input with manual parsing | Plain `<input>`, parseFloat + validate. More flexibility, more code, loses browser spinner UX. | |

### Q3: Error surface

| Option | Description | Selected |
|--------|-------------|----------|
| Inline message below the buttons | Single `<p role="alert">` rendered when last submit was 400. Cleared on next submit or input change. Co-located, accessible, no global layer. | ✓ |
| Toast at the top-right | More visible at a glance, but introduces a toast system nothing else in Phase 7 needs. | |
| Inline + toast hybrid | Inline for routine validation, toast for terminal errors. Most informative, most code. | |

### Q4: Post-trade feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Implicit: positions/cash/header update | Re-fetch `/api/portfolio` so the positions table + header reflect the new state on next render. The update IS the confirmation. Matches PLAN.md "instant fill, fluid demo." | ✓ |
| Brief flash on the affected position row | Same as option 1 plus a 500ms flash on the changed row. Adds a tiny ceremony showing WHICH position changed. Couples trade bar to positions table. | |
| Tiny inline success line | `'Bought 5 AAPL @ $190.22'` appears under the buttons for a few seconds. Explicit but noisy after repeated trades. | |

**Notes:** All four Trade bar questions answered with the recommended defaults.

---

## Claude's Discretion

Areas the user explicitly delegated to Claude (covered in CONTEXT.md `<decisions>` Claude's Discretion section):

- Panel layout (3-column desktop-first grid; min-width 1024px with horizontal scroll below)
- Portfolio data flow (TanStack Query or plain fetch; refetch on mutation + 15s interval)
- Connection-status dot styling and placement
- Positions table sort + empty state
- Main chart timeframe (session-since-page-load, no selector in Phase 7)
- Header layout / numeric formatting
- Watchlist row layout
- Routing (replace `/` placeholder vs add `/terminal`)

## Deferred Ideas

Captured in CONTEXT.md `<deferred>` section:

- Position-row flash on trade
- Typeahead / combobox for ticker input
- Clickable connection-status dot
- Timeframe selector on the main chart
- Toast system
- Responsive stacking below 1024px
- Multi-select positions / bulk close
- Backend extensions for `session_start_price` or `sparkline_history`
- Recharts for sparklines (reserved for Phase 8)
