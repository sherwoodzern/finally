---
phase: 07
slug: market-data-trading-ui
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-24
---

# Phase 07 — UI Design Contract

> Visual and interaction contract for the FinAlly trading terminal. Five panels on
> one desktop-first screen. Extends the Phase 06 `@theme` palette; inherits the dark
> theme, monospace-numeric pattern from `/debug`, and every SSE store decision
> (D-11..D-19). Locks all CONTEXT.md D-01..D-08 and resolves the two upstream
> palette conflicts (D-02 over Phase 06 §4.1; `detail.error` over D-07's
> "detail.code" wording).

---

## Scope & Intent

Phase 07 paints all five product surfaces of the trading terminal:

1. Watchlist panel (FE-03)
2. Main chart area (FE-04)
3. Positions table (FE-07)
4. Trade bar (FE-08)
5. Header strip (FE-10)

Everything renders on a desktop-first (`min-width: 1024px`) three-column grid,
driven by the existing Phase 06 Zustand store plus the existing `/api/portfolio`,
`/api/portfolio/trade`, and `/api/watchlist` REST endpoints from Phases 03/04.

**Out of scope (belongs to later phases):** Portfolio heatmap, P&L line chart,
AI chat panel, demo polish (FE-05 / FE-06 / FE-09 / FE-11 → Phase 08). Static
export mount at `/` (APP-02 → Phase 08). Docker build (Phase 09). Playwright
E2E (Phase 10).

---

## 1. Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none (manual Tailwind v4 CSS-first `@theme`) | Phase 06 UI-SPEC §1 (inherited) |
| Preset | not applicable | — |
| Component library | none (hand-authored `components/terminal/*.tsx`) | 07-RESEARCH §2 "Recommended Project Structure" |
| Icon library | none (Phase 07 has no icons) | — |
| Font stack — sans | `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | Phase 06 UI-SPEC §3 (inherited) |
| Font stack — mono | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | Phase 06 UI-SPEC §3 (inherited) |
| Chart library | `lightweight-charts@^5.2.0` (main chart + sparklines) | CONTEXT.md D-04, 07-RESEARCH §1 |
| Data-fetching | `@tanstack/react-query@^5.100.1` for `/api/portfolio` + `/api/portfolio/trade` | 07-RESEARCH §4 recommendation |

**Registry safety gate:** N/A — no shadcn, no third-party registries, no vetting
required.

---

## 2. Spacing Scale

Inherited from Phase 06. Tailwind v4 4px base. Only multiples of 4. No arbitrary
`px-[Npx]` values.

| Token | Value | Usage in Phase 07 |
|-------|-------|-------------------|
| `gap-1` / `p-1` | 4px | Icon-like inline gaps (e.g., between status dot and label) |
| `gap-2` / `p-2` / `px-2 py-2` | 8px | Table cell padding, stack gap inside rows |
| `gap-3` / `p-3` | 12px | Input vertical padding |
| `gap-4` / `p-4` | 16px | Panel internal padding, section gaps, input horizontal padding |
| `gap-6` / `p-6` | 24px | Grid column gap, page outer padding |
| `gap-8` / `p-8` | 32px | Not used in Phase 07 — reserved for Phase 08 |

**Exceptions:** none. Every spacing utility referenced in §5 below is a multiple
of 4.

---

## 3. Typography

Inherited from Phase 06 UI-SPEC §3 unchanged. Phase 07 adds one behavioral rule:
**every numeric cell uses `font-mono` + `tabular-nums` + `text-right`** so digit
columns align across rows in the watchlist, positions table, and header totals.

| Role | Family | Size | Weight | Line-height | Notes |
|------|--------|------|--------|-------------|-------|
| Body / default | sans | 16px | 400 | 1.5 | Panel headings, button labels |
| h1 (page title — reuse Phase 06) | sans | 28px | 600 | 1.2 | Not used in Phase 07 — no h1 on the terminal page |
| h2 (panel header) | sans | 20px | 600 | 1.3 | Watchlist / Positions / Main-chart panel titles |
| Small / caption | sans | 14px | 400 | 1.4 | Input labels, error copy, status-dot label |
| **Monospace (numeric)** | mono | 14px | 400 | 1.4 | **All prices, percentages, quantities, cash, P&L, timestamps.** Apply `font-mono tabular-nums text-right`. |

**Sizes declared:** 4 (28, 20, 16, 14) — unchanged from Phase 06.
**Weights declared:** 2 (400, 600) — unchanged from Phase 06.

---

## 4. Color Contract

### 4.1 Palette — Two New Tokens

Phase 07 **adds two tokens** to the existing `@theme` block in
`frontend/src/app/globals.css` and **overrides** the placeholder hex values that
Phase 06 UI-SPEC §4.1 declared for `--color-up` / `--color-down`.

| Token | Phase 06 placeholder | Phase 07 final | Rationale |
|-------|----------------------|----------------|-----------|
| `--color-up` | `#3fb950` | **`#26a69a`** | CONTEXT.md D-02. Lightweight Charts default series color — no custom `color:` option needed on sparkline/main-chart `addSeries(LineSeries, ...)` calls. |
| `--color-down` | `#f85149` | **`#ef5350`** | CONTEXT.md D-02. Same rationale. |

**Override is explicit.** CONTEXT.md D-02 is the latest decision artifact and
downstream of Phase 06 UI-SPEC. The first task of Plan 07-01 updates
`globals.css` — both inside `@theme` and inside the force-emit `:root` block —
to the D-02 values. This is a one-commit change affecting one file. Phase 07
supersedes Phase 06 §4.1 for these two tokens only; every other Phase 06 color
token (surface, surface-alt, border-muted, foreground, foreground-muted,
accent-yellow, accent-blue, accent-purple) is unchanged.

Full `@theme` block after the Phase 07 update:

```css
/* src/app/globals.css */
@import "tailwindcss";

@theme {
  /* Surfaces (unchanged, Phase 06) */
  --color-surface:      #0d1117;
  --color-surface-alt:  #1a1a2e;
  --color-border-muted: #30363d;

  /* Text (unchanged, Phase 06) */
  --color-foreground:        #e6edf3;
  --color-foreground-muted:  #8b949e;

  /* Brand accents (unchanged, Phase 06) */
  --color-accent-yellow: #ecad0a;
  --color-accent-blue:   #209dd7;
  --color-accent-purple: #753991;

  /* Semantic up/down — Phase 07 D-02 values (override Phase 06 §4.1) */
  --color-up:   #26a69a;
  --color-down: #ef5350;
}

/* Force-emit block — must mirror @theme values for any token that might tree-shake. */
:root {
  --color-accent-purple: #753991;
  --color-surface-alt:   #1a1a2e;
  --color-border-muted:  #30363d;
  --color-up:            #26a69a;   /* Phase 07 D-02 */
  --color-down:          #ef5350;   /* Phase 07 D-02 */
  --color-foreground-muted: #8b949e;
}
```

### 4.2 60 / 30 / 10 Split

| Share | Role | Color(s) |
|-------|------|----------|
| 60% | Dominant surface | `--color-surface` (`#0d1117`) — page background, main-chart background, watchlist/positions panel background |
| 30% | Secondary surface | `--color-surface-alt` (`#1a1a2e`) — header strip, trade-bar panel; `--color-border-muted` (`#30363d`) — grid lines, panel dividers, input borders |
| 10% | Accent | `--color-accent-purple` — **trade-bar Submit button (primary CTA)**; `--color-accent-blue` — focus rings on inputs and interactive rows; `--color-accent-yellow` — connection-status dot (reconnecting state only) |

**Accent is reserved for (Phase 07 scope only):**
- `--color-accent-purple` (`#753991`) — Submit-trade button background (the sole
  primary-CTA in Phase 07). Matches PLAN.md §2 "Purple Secondary: submit buttons".
- `--color-accent-blue` (`#209dd7`) — `focus-visible:outline-accent-blue` on inputs,
  buttons, and clickable rows (watchlist rows, position rows). No hover color
  swap — keep interactions subtle.
- `--color-accent-yellow` (`#ecad0a`) — connection-status dot when
  `status === 'reconnecting'` (nowhere else in Phase 07).

**Semantic up/down — where the tokens render:**
- Price-flash row background (`bg-up/10`, `bg-down/10`, `transition-colors duration-500`).
- Watchlist daily-change % text color (`text-up` when ≥0, `text-down` when <0).
- Sparkline stroke color (green when `last_tick >= session_start` else red).
- Main chart price-line stroke color (same convention as sparklines).
- Positions table unrealized P&L column text color.
- Connection-status dot (`bg-up` connected, `bg-down` disconnected).

Derived Tailwind v4 utilities auto-generated from the two `@theme` tokens:
`text-up`, `text-down`, `bg-up`, `bg-down`, `border-up`, `border-down`,
and the alpha variants `bg-up/10`, `bg-down/10`, `text-up/80`, etc. (CITED:
07-RESEARCH §10.)

### 4.3 Accessibility (WCAG AA contrast against `#0d1117` surface)

| Pair | Ratio | Pass |
|------|-------|------|
| `#26a69a` (up) on `#0d1117` | ~5.8:1 | AA |
| `#ef5350` (down) on `#0d1117` | ~4.6:1 | AA |
| `#e6edf3` foreground on `#0d1117` (inherited) | ~15.4:1 | AAA |
| `#8b949e` foreground-muted on `#0d1117` (inherited) | ~6.3:1 | AA |
| `#ecad0a` accent-yellow on `#0d1117` (inherited) | ~9.1:1 | AAA |
| `#209dd7` accent-blue on `#0d1117` (inherited) | ~5.6:1 | AA |
| White (`#ffffff`) foreground on `#753991` accent-purple (Submit button) | ~5.2:1 | AA |

Both new semantic colors pass WCAG AA as text on `bg-surface`. The
price-flash backgrounds use `bg-up/10` / `bg-down/10` (10% alpha over surface)
— effectively a tint rather than a fill, so the flash does not change text
contrast for the row underneath.

### 4.4 Focus Rings

Use `focus-visible:outline-2 focus-visible:outline-offset-2
focus-visible:outline-accent-blue` on every interactive element:

- Trade-bar ticker input
- Trade-bar quantity input
- Trade-bar Buy button
- Trade-bar Sell button
- Watchlist row (`tabindex={0}` — clicking selects the ticker)
- Positions row (`tabindex={0}` — clicking selects the ticker)

---

## 5. Layout & Component Contracts

### 5.1 Layout Grid

Desktop-first three-column CSS grid. `min-width: 1024px` on the outer
container; narrower viewports get horizontal scroll (responsive stacking is
deferred per CONTEXT.md "Claude's Discretion").

```
┌─ min-w-[1024px] bg-surface p-6 ─────────────────────────────────────────────┐
│                                                                             │
│  grid grid-cols-[320px_1fr_360px] gap-6                                     │
│                                                                             │
│  ┌─ Watchlist ─────┐  ┌─ Header strip ─────────────────┐  ┌─ Positions ──┐ │
│  │ h2 Watchlist    │  │ h-16 bg-surface-alt px-4 flex  │  │ h2 Positions │ │
│  │ ─────────────── │  │  ● connected   $10,234.56 │ … │  │ ───────────── │ │
│  │ AAPL  +0.42% .. │  └──────────────────────────────────┘  │ AAPL 10 @ 190│ │
│  │ GOOGL -0.11% .. │  ┌─ Main chart ───────────────────┐  │ ...         │ │
│  │ MSFT  +0.03% .. │  │ h2 Chart: AAPL                 │  │             │ │
│  │ ...             │  │ h-[calc(100vh-...)]             │  └──────────────┘ │
│  │ (scroll-y)      │  │ (Lightweight Charts canvas)    │  ┌─ Trade bar ─┐ │
│  │                 │  │                                │  │ bg-surface-alt│ │
│  │                 │  │                                │  │ Ticker: [__]  │ │
│  │                 │  │                                │  │ Qty:    [__]  │ │
│  │                 │  │                                │  │ [Buy] [Sell]  │ │
│  │                 │  │                                │  │ <p role=alert>│ │
│  └─────────────────┘  └────────────────────────────────┘  └──────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Concrete grid contract:

| Region | Tailwind classes | Notes |
|--------|------------------|-------|
| Page outer | `min-h-screen min-w-[1024px] bg-surface text-foreground p-6` | Root of the terminal page |
| Grid | `grid grid-cols-[320px_1fr_360px] gap-6` | Three columns, 24px gaps |
| Left column (Watchlist) | `flex flex-col gap-4` | Single panel; grows vertically |
| Center column (Header + Chart) | `flex flex-col gap-4 min-w-0` | `min-w-0` prevents grid blowout on long chart tooltips |
| Right column (Positions + Trade bar) | `flex flex-col gap-4` | Positions on top, trade bar fixed at bottom |
| Header strip | `h-16 bg-surface-alt border border-border-muted rounded px-4 flex items-center gap-6` | Fixed 64px height |
| Main chart | `flex-1 bg-surface border border-border-muted rounded p-4 min-h-[400px]` | Flex-fills remaining vertical space |
| Watchlist panel | `flex-1 bg-surface border border-border-muted rounded overflow-hidden` | Internal table is `overflow-y-auto` |
| Positions panel | `flex-1 bg-surface border border-border-muted rounded overflow-hidden min-h-[240px]` | Same treatment as watchlist |
| Trade bar panel | `bg-surface-alt border border-border-muted rounded p-4` | Fixed-height; does not flex |

At 1440×900 target (typical desktop) this yields approximately:
- Left column 320px, center ~704px, right 360px, with 24px gaps and 24px outer
  padding.
- Header 64px; main chart fills ~700px vertically; positions + trade bar split
  the right column vertically.

### 5.2 Watchlist Panel (FE-03)

**Route:** rendered by `<Watchlist />` inside the left grid column.
**Data source:** `GET /api/watchlist` once on mount (seed row order), then
per-row subscribes to `selectTick(ticker)`, `selectSparkline(ticker)`,
`selectFlash(ticker)` from `usePriceStore`.

**Panel markup skeleton:**

```tsx
<aside className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col">
  <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">Watchlist</h2>
  <div className="overflow-y-auto">
    <table className="w-full border-collapse">
      <tbody>
        {tickers.map(ticker => <WatchlistRow key={ticker} ticker={ticker} />)}
      </tbody>
    </table>
  </div>
</aside>
```

**Row markup skeleton (fixed 56px row height):**

```tsx
<tr
  className={`h-14 border-b border-border-muted cursor-pointer transition-colors duration-500 ${flashClass} focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent-blue`}
  tabIndex={0}
  role="button"
  aria-label={`Select ${ticker}`}
  onClick={() => setSelectedTicker(ticker)}
  onKeyDown={handleEnterKey}
>
  <td className="px-4 font-semibold">{ticker}</td>
  <td className={`px-2 font-mono tabular-nums text-right text-sm ${pctColor}`}>{formatPercent(pct)}</td>
  <td className="px-2 font-mono tabular-nums text-right text-sm">{formatPrice(price)}</td>
  <td className="px-2 w-[96px]"><Sparkline ticker={ticker} /></td>
</tr>
```

**Column contract:**

| Column | Width | Content | Formatting |
|--------|-------|---------|------------|
| Ticker | `auto` (starts at col-1 edge, `px-4`) | `{ticker}` | `font-semibold` (sans, 16px, 600) |
| Daily-change % | ~72px | `(price - session_start_price) / session_start_price * 100` | `font-mono tabular-nums text-right text-sm`. Color: `text-up` if ≥0, `text-down` if <0. Format: `+0.42%` or `-0.11%` (sign always shown, 2 decimals) |
| Price | ~80px | `{price}` | `font-mono tabular-nums text-right text-sm`. Format: `$190.23` (2 decimals) |
| Sparkline | 96px cell, 80×32 canvas | Lightweight Charts micro-chart | Stroke `--color-up` if `last_tick >= session_start` else `--color-down`. No axes, grid, crosshair, watermark. |

**Row states:**

| State | Visual |
|-------|--------|
| Idle | `bg-surface` (inherits panel background) |
| Flash up | `bg-up/10` applied immediately on tick, `transition-colors duration-500` fades back to surface after the selector sees `flashDirection[ticker]` cleared by the 500ms `setTimeout` in `ingest()` (D-01) |
| Flash down | `bg-down/10` — same mechanics |
| Hover | `hover:bg-surface-alt` (subtle elevation) |
| Selected (this ticker drives the main chart) | `bg-surface-alt` with a 2px `border-l-accent-blue` on the leftmost cell |
| Focus-visible | `outline-2 outline-accent-blue outline-offset-[-2px]` (inset so it doesn't break row alignment) |

**Empty state (no SSE ticks received yet — first 500ms after connect):**
Render each row with price/percent cells as `—` (em-dash) and an empty
sparkline. No separate empty-panel copy: the watchlist is never empty (backend
seeds 10 tickers on init).

### 5.3 Main Chart Area (FE-04)

**Route:** rendered by `<MainChart />` inside the center grid column, below
the header strip.
**Data source:** subscribes to the full `selectSparkline(selectedTicker)`
history. `setData(...)` once when `selectedTicker` changes, then `update(...)`
per subsequent tick (CITED: 07-RESEARCH §3 Pattern 3).

**Panel markup skeleton:**

```tsx
<section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
  <header className="flex items-baseline gap-4 mb-3">
    <h2 className="text-xl font-semibold">Chart: {selectedTicker}</h2>
    <span className="font-mono tabular-nums text-sm text-foreground-muted">
      {formatPrice(currentPrice)}
    </span>
  </header>
  <div ref={containerRef} className="flex-1 w-full" />
</section>
```

**Chart chrome (Lightweight Charts v5 options):**

| Concern | Value |
|---------|-------|
| Background | `--color-surface` (`#0d1117`) — `layout.background.color: '#0d1117'` |
| Text color | `--color-foreground` (`#e6edf3`) — `layout.textColor: '#e6edf3'` |
| Grid lines | `--color-border-muted` (`#30363d`) — `grid.vertLines.color`, `grid.horzLines.color` |
| Border | panel wrapper `border border-border-muted rounded` |
| Internal padding | `p-4` (16px) |
| Height | `flex-1 min-h-[400px]` — fills remaining vertical space, never shorter than 400px |
| Series type | `LineSeries` — `chart.addSeries(LineSeries, { color, lineWidth: 2 })` |
| Line stroke | `--color-up` if `last_tick_price >= session_start_price` else `--color-down` (recompute via `applyOptions({ color })` on each tick) |
| Y-axis format | `$ X,XXX.XX` — configure via `priceFormat: { type: 'price', precision: 2, minMove: 0.01 }` and prefix with `$` in `localization.priceFormatter` |
| X-axis | `timeScale` visible, default. No custom tick label formatter in Phase 07 |
| Crosshair | default on hover (Lightweight Charts built-in) |
| Tooltip | default on hover (Lightweight Charts built-in) |
| Watermark | **disabled** (`watermark: { visible: false }` — or omit the option entirely in v5) |
| Auto-sizing | `autoSize: true` (ResizeObserver-based; required for flex-fill container) |

**Empty state (no ticker selected yet):** If `selectedTicker === null`, render
the panel with a centered foreground-muted message:
`"Select a ticker from the watchlist to view its chart."` — sans, 14px,
`text-foreground-muted`, `text-center`. Do NOT create a chart instance until
a ticker is selected.

**Selected-ticker source:** new Zustand slice
`selectedTicker: string | null` (default `null` until user clicks a watchlist
row). Rationale: 07-RESEARCH Open Question #3 recommends Option (a) — lives in
the same store for selector symmetry.

### 5.4 Positions Table (FE-07)

**Route:** rendered by `<PositionsTable />` inside the right grid column, above
the trade bar.
**Data source:** `useQuery(['portfolio'], fetchPortfolio, { refetchInterval: 15_000 })`.
Rows subscribe to `selectTick(ticker)` for live `current_price`; unrealized
P&L is computed client-side on every render; cold-start fallback (no tick in
store yet) uses backend's `PositionOut.unrealized_pnl`.

**Panel markup skeleton:**

```tsx
<section className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col min-h-[240px]">
  <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">Positions</h2>
  <div className="overflow-y-auto">
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-sm text-foreground-muted">
          <th className="text-left  px-4 py-2 border-b border-border-muted">Ticker</th>
          <th className="text-right px-2 py-2 border-b border-border-muted">Qty</th>
          <th className="text-right px-2 py-2 border-b border-border-muted">Avg Cost</th>
          <th className="text-right px-2 py-2 border-b border-border-muted">Price</th>
          <th className="text-right px-2 py-2 border-b border-border-muted">P&L</th>
          <th className="text-right px-4 py-2 border-b border-border-muted">%</th>
        </tr>
      </thead>
      <tbody>{/* rows */}</tbody>
    </table>
  </div>
</section>
```

**Row markup skeleton (fixed 48px row height):**

```tsx
<tr
  className={`h-12 border-b border-border-muted cursor-pointer hover:bg-surface-alt transition-colors duration-500 ${flashClass}`}
  tabIndex={0}
  role="button"
  onClick={() => setSelectedTicker(ticker)}
>
  <td className="px-4 font-semibold">{ticker}</td>
  <td className="px-2 font-mono tabular-nums text-right text-sm">{formatQty(quantity)}</td>
  <td className="px-2 font-mono tabular-nums text-right text-sm">{formatPrice(avg_cost)}</td>
  <td className="px-2 font-mono tabular-nums text-right text-sm">{formatPrice(current_price)}</td>
  <td className={`px-2 font-mono tabular-nums text-right text-sm ${pnlColor}`}>{formatSignedMoney(pnl)}</td>
  <td className={`px-4 font-mono tabular-nums text-right text-sm ${pnlColor}`}>{formatPercent(pct)}</td>
</tr>
```

**Column contract:**

| Column | Source | Format |
|--------|--------|--------|
| Ticker | `position.ticker` | `font-semibold`, sans, 16px, left-aligned |
| Qty | `position.quantity` | `{quantity}` with up to 4 decimal places stripped of trailing zeros (fractional shares supported — PLAN.md §7) |
| Avg Cost | `position.avg_cost` | `$190.00` (2 decimals) |
| Price | `store.prices[ticker].price ?? position.current_price` | `$190.23` (2 decimals). Store tick wins; backend `current_price` is cold-start fallback only. |
| P&L | client-computed: `(current_price - avg_cost) * quantity`, fallback `position.unrealized_pnl` | `+$12.34` or `-$5.67` (signed, 2 decimals). Text color: `text-up` if ≥0 else `text-down`. |
| % | client-computed: `(current_price - avg_cost) / avg_cost * 100`, fallback `position.change_percent` | `+0.42%` or `-0.11%` (signed, 2 decimals). Same color rule as P&L. |

**Row states:** identical contract to watchlist row — `hover:bg-surface-alt`,
selected state gets `bg-surface-alt + border-l-accent-blue`, flash background
applies when store emits a tick for that ticker. Clicking a row selects that
ticker in the main chart (same `setSelectedTicker` store action as the
watchlist).

**Default sort:** by weight descending (`position.quantity * current_price`).
Computed client-side on every render. **No sort UI in Phase 07.**

**Empty state (no positions yet):** Render one `<tr>` with a single cell
spanning all columns:
`"No positions yet — use the trade bar to buy shares."` in
`text-foreground-muted text-center py-6 text-sm`.

**Loading state (TanStack Query `isPending`):** Render one `<tr>` with a single
cell: `"Loading positions…"` in `text-foreground-muted text-center py-6 text-sm`.

**Error state (TanStack Query `isError`):** Render one `<tr>` with a single
cell: `"Couldn't load positions. Retrying in 15s."` in
`text-foreground-muted text-center py-6 text-sm`. (TanStack retries
automatically via `refetchInterval`.)

### 5.5 Trade Bar (FE-08)

**Route:** rendered by `<TradeBar />` inside the right grid column, below the
positions panel.
**Data source:** `useMutation(postTrade)` with `onSuccess → invalidateQueries(['portfolio'])`
+ clear-inputs + focus ticker. (CITED: 07-RESEARCH §4.)

**Panel markup skeleton:**

```tsx
<section className="bg-surface-alt border border-border-muted rounded p-4">
  <form onSubmit={handleSubmit} className="flex flex-col gap-3">
    <label className="flex flex-col gap-1 text-sm text-foreground-muted">
      Ticker
      <input
        ref={tickerRef}
        type="text"
        inputMode="text"
        placeholder="AAPL"
        maxLength={10}
        value={ticker}
        onChange={e => setTicker(e.target.value.trim().toUpperCase())}
        className="h-10 px-3 bg-surface border border-border-muted rounded text-foreground font-mono focus-visible:outline-2 focus-visible:outline-accent-blue"
      />
    </label>
    <label className="flex flex-col gap-1 text-sm text-foreground-muted">
      Quantity
      <input
        type="number"
        min="0.01"
        step="0.01"
        placeholder="1"
        value={quantity}
        onChange={e => setQuantity(e.target.value)}
        className="h-10 px-3 bg-surface border border-border-muted rounded text-foreground font-mono focus-visible:outline-2 focus-visible:outline-accent-blue"
      />
    </label>
    <div className="flex gap-3">
      <button
        type="submit"
        name="side"
        value="buy"
        disabled={isSubmitting || !isValid}
        className="flex-1 h-10 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
      >
        Buy
      </button>
      <button
        type="submit"
        name="side"
        value="sell"
        disabled={isSubmitting || !isValid}
        className="flex-1 h-10 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
      >
        Sell
      </button>
    </div>
    {errorCode && (
      <p role="alert" className="text-sm text-down">
        {ERROR_TEXT[errorCode] ?? 'Something went wrong. Try again.'}
      </p>
    )}
  </form>
</section>
```

**Input contracts:**

| Input | Rule | Source |
|-------|------|--------|
| Ticker | `<input type="text">`, `maxLength={10}`, upper-cases on change (`e.target.value.trim().toUpperCase()`). Client validates against `/^[A-Z][A-Z0-9.]{0,9}$/` before submit — if regex fails, set `errorCode = 'unknown_ticker'` without calling the server. | CONTEXT.md D-05; 07-RESEARCH §5 |
| Quantity | `<input type="number" min="0.01" step="0.01">`. Parsed with `parseFloat` on submit. Server is the final source of truth; client relies on HTML `min`/`step` for non-JS baseline. | CONTEXT.md D-06 |

**Button contract:**

| Button | Color | Label | Role |
|--------|-------|-------|------|
| Buy | `bg-accent-purple text-white` | `Buy` | `type="submit" name="side" value="buy"` |
| Sell | `bg-accent-purple text-white` | `Sell` | `type="submit" name="side" value="sell"` |

**Both Buy and Sell use `bg-accent-purple`** per PLAN.md §2 ("Purple Secondary:
submit buttons"). The semantic up/down colors are NOT used on the buttons
themselves — reserving them for price direction only keeps the color meaning
unambiguous. The difference between Buy and Sell is encoded only in the label
+ the POST body's `side` field.

**Button states:**

| State | Visual |
|-------|--------|
| Idle | `bg-accent-purple text-white font-semibold` |
| Hover | `hover:brightness-110` (subtle lift, no separate hover color) |
| Disabled (submitting OR input invalid) | `disabled:opacity-50 disabled:cursor-not-allowed` |
| Focus-visible | `outline-2 outline-accent-blue` |

**Error surface (D-07):**

- Single `<p role="alert">` rendered below the buttons when
  `errorCode !== null`.
- Text color: `text-down` (`#ef5350`), font size 14px.
- Cleared on: next successful submit (200 from `/api/portfolio/trade`), OR
  when `ticker` or `quantity` input value changes.
- Error-code → copy map (exact strings):

  | Code (from `body.detail.error`) | Copy |
  |---------------------------------|------|
  | `insufficient_cash` | `Not enough cash for that order.` |
  | `insufficient_shares` | `You don't have that many shares to sell.` |
  | `unknown_ticker` | `No such ticker.` |
  | `price_unavailable` | `Price unavailable right now — try again.` |
  | *(any other code or network error)* | `Something went wrong. Try again.` |

- **Note on the backend key:** CONTEXT.md D-07 refers to `detail.code`; the
  backend actually emits `detail.error`. The frontend fetch wrapper reads
  `body.detail.error` (07-RESEARCH §7 verified against
  `backend/app/portfolio/routes.py:47`). This is a plan-level implementation
  detail — the UI-SPEC copy map is authoritative and keyed by code.

**Post-trade behavior (D-08 — implicit confirmation):**

1. On 200: TanStack Query invalidates `['portfolio']` → positions + cash
   re-fetch → positions row + header re-render with new values.
2. Ticker and quantity inputs clear (`setTicker('')`, `setQuantity('')`).
3. Focus returns to the ticker input (`tickerRef.current?.focus()`).
4. No toast, no success banner, no modal.

### 5.6 Header Strip (FE-10)

**Route:** rendered by `<Header />` inside the center grid column, above the
main chart.
**Data source:** `useQuery(['portfolio'])` for `cash_balance` and positions;
`usePriceStore(s => s.prices)` for live prices (for total-value recompute);
`usePriceStore(selectConnectionStatus)` for the dot.

**Markup skeleton:**

```tsx
<header className="h-16 bg-surface-alt border border-border-muted rounded px-4 flex items-center gap-6">
  <ConnectionDot />
  <div className="flex items-baseline gap-2">
    <span className="text-sm text-foreground-muted">Total</span>
    <span className="font-mono tabular-nums text-lg">{formatPrice(totalValue)}</span>
  </div>
  <div className="flex items-baseline gap-2">
    <span className="text-sm text-foreground-muted">Cash</span>
    <span className="font-mono tabular-nums text-lg">{formatPrice(cashBalance)}</span>
  </div>
</header>
```

**Total-value computation:**

```
total_value = cash_balance + Σ over positions of (quantity × current_price from store, fallback avg_cost)
```

Re-computed on every render; re-renders on store tick and on portfolio
invalidation.

**Format:** `$ X,XXX.XX` with thousands separator and 2 decimals. `font-mono
tabular-nums text-lg` so the digits stay stable as values tick.

**Copy contract:**

| Element | Copy |
|---------|------|
| Total label | `Total` |
| Cash label | `Cash` |

**Optional a11y enhancement:** consider
`aria-live="polite"` on the two numeric spans so screen readers announce
balance changes after trades. This is a recommendation, not a requirement —
Phase 07 can skip it; Phase 11 polish can add it.

### 5.7 Connection-Status Dot

**Component:** `<ConnectionDot />` (always rendered inside the header strip as
the leftmost element).
**Data source:** `usePriceStore(selectConnectionStatus)`.

```tsx
export function ConnectionDot() {
  const status = usePriceStore(selectConnectionStatus);
  const classes: Record<ConnectionStatus, string> = {
    connected:    'bg-up',
    reconnecting: 'bg-accent-yellow',
    disconnected: 'bg-down',
  };
  const titles: Record<ConnectionStatus, string> = {
    connected:    'Live',
    reconnecting: 'Reconnecting…',
    disconnected: 'Disconnected',
  };
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${classes[status]}`}
      title={titles[status]}
      aria-label={`SSE ${status}`}
    />
  );
}
```

| Status | Pixel size | Tailwind | Color | `title=` |
|--------|-----------|----------|-------|----------|
| `connected` | 10×10 | `w-2.5 h-2.5 rounded-full bg-up` | `#26a69a` | `Live` |
| `reconnecting` | 10×10 | `w-2.5 h-2.5 rounded-full bg-accent-yellow` | `#ecad0a` | `Reconnecting…` |
| `disconnected` | 10×10 | `w-2.5 h-2.5 rounded-full bg-down` | `#ef5350` | `Disconnected` |

**Placement:** first child of the header `<header>`, before the total/cash
numbers. Not interactive in Phase 07 (CONTEXT.md "Claude's Discretion" notes
clickable-dot behavior is reserved).

---

## 6. Price-Flash Animation Contract (D-01)

| Property | Value |
|----------|-------|
| Trigger | Inside `usePriceStore.ingest()`. When `raw.price !== prior.price`, set `flashDirection[ticker] = (raw.price > prior.price ? 'up' : 'down')`. |
| Clear | `setTimeout(() => delete flashDirection[ticker], 500)` scheduled at the same instant. Timer handle tracked in a module-level `Map<string, Timeout>` so a rapid re-tick cancels the prior pending clear. |
| Duration | **500ms** (matches PLAN.md §2 "fading over ~500ms via CSS transitions"). |
| Class applied on up | `bg-up/10` (10% alpha — `#26a69a` at 10% opacity over `#0d1117` surface) |
| Class applied on down | `bg-down/10` (10% alpha — `#ef5350` at 10% opacity over `#0d1117` surface) |
| Transition | `transition-colors duration-500` — Tailwind emits `transition-property: background-color; transition-duration: 500ms; transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1)` (Tailwind default ease-out curve) |
| Class when no flash | empty string — row falls back to `bg-surface` (inherited) |
| Cleanup | On store `disconnect()` / `reset()`: clear all pending timers and zero `flashDirection`. |

Row template:

```tsx
const flash = usePriceStore(selectFlash(ticker));
const flashClass =
  flash === 'up'   ? 'bg-up/10' :
  flash === 'down' ? 'bg-down/10' :
  '';
// On a <tr> or <div>:
className={`transition-colors duration-500 ${flashClass}`}
```

---

## 7. Sparkline Chrome (D-04)

| Property | Value |
|----------|-------|
| Library | `lightweight-charts@^5.2.0` |
| Container | `<div className="w-20 h-8" />` — **80×32 px** (`w-20` = 80, `h-8` = 32) |
| Chart options | `autoSize: true`, `layout.background.color: 'transparent'`, `layout.textColor: 'transparent'` |
| Right price scale | `rightPriceScale: { visible: false }` |
| Left price scale | `leftPriceScale: { visible: false }` |
| Time scale | `timeScale: { visible: false, borderVisible: false }` |
| Grid | `grid: { vertLines: { visible: false }, horzLines: { visible: false } }` |
| Crosshair | `crosshair: { horzLine: { visible: false }, vertLine: { visible: false } }` |
| Scroll / scale | `handleScroll: false, handleScale: false` |
| Watermark | disabled (omit the option) |
| Series | `chart.addSeries(LineSeries, { color, lineWidth: 1 })` — `lineWidth: 1` for the small size |
| Stroke color | `--color-up` (`#26a69a`) if `last_tick_price >= session_start_price` else `--color-down` (`#ef5350`). Recompute via `series.applyOptions({ color })` whenever the sign flips. |
| Data | `series.setData(buffer.map((price, i) => ({ time: i as UTCTimestamp, value: price })))` on first render; `series.update({ time: buffer.length - 1, value: lastPrice })` on subsequent ticks. Because sparkline time is just a monotonic integer index, Lightweight Charts treats it as an ordered series without needing real Unix timestamps. |

---

## 8. Copywriting Contract (consolidated)

Every visible string in Phase 07. Executor copies verbatim.

| Location | String |
|----------|--------|
| Watchlist panel h2 | `Watchlist` |
| Watchlist empty cell (no tick yet) | `—` (em-dash) |
| Main chart h2 (while a ticker is selected) | `Chart: {TICKER}` (template; literal prefix `Chart: ` + upper-case ticker) |
| Main chart empty state | `Select a ticker from the watchlist to view its chart.` |
| Positions panel h2 | `Positions` |
| Positions column headers | `Ticker`, `Qty`, `Avg Cost`, `Price`, `P&L`, `%` |
| Positions empty state | `No positions yet — use the trade bar to buy shares.` |
| Positions loading state | `Loading positions…` |
| Positions error state | `Couldn't load positions. Retrying in 15s.` |
| Trade bar ticker label | `Ticker` |
| Trade bar quantity label | `Quantity` |
| Trade bar ticker placeholder | `AAPL` |
| Trade bar quantity placeholder | `1` |
| Trade bar Buy button | `Buy` |
| Trade bar Sell button | `Sell` |
| Trade bar error — insufficient_cash | `Not enough cash for that order.` |
| Trade bar error — insufficient_shares | `You don't have that many shares to sell.` |
| Trade bar error — unknown_ticker | `No such ticker.` |
| Trade bar error — price_unavailable | `Price unavailable right now — try again.` |
| Trade bar error — unmapped / network | `Something went wrong. Try again.` |
| Header total label | `Total` |
| Header cash label | `Cash` |
| Connection dot title — connected | `Live` |
| Connection dot title — reconnecting | `Reconnecting…` |
| Connection dot title — disconnected | `Disconnected` |
| Connection dot aria-label — connected | `SSE connected` |
| Connection dot aria-label — reconnecting | `SSE reconnecting` |
| Connection dot aria-label — disconnected | `SSE disconnected` |

**Notes:**
- Use ASCII apostrophes (`'`) and straight dashes or em-dash (`—`). The em-dash
  `—` in `price_unavailable` and in the empty state is intentional — it matches
  CONTEXT.md D-07 verbatim.
- No emojis in any string (CLAUDE.md rule).
- "Destructive actions" are **not applicable in Phase 07** — a market sell
  cancels a position but there is no confirmation flow (CONTEXT.md D-08).

---

## 9. Routing Decision (locked)

**Terminal renders at `/` (the root route).** The Phase 06 placeholder body
in `frontend/src/app/page.tsx` is **replaced** by the terminal UI.

| Route | Phase 07 status | Content |
|-------|-----------------|---------|
| `/` | **replaced** | The terminal — three-column grid (watchlist + header/chart + positions/trade bar) |
| `/debug` | unchanged | Phase 06 SSE diagnostic view — stays as a developer tool |

Rationale:
- PLAN.md §2 First Launch: user opens `http://localhost:8000` and "immediately
  sees" the terminal. That's the root path.
- Single landing = simpler test setup + simpler Phase 09 Docker preview.
- `/debug` is a useful permanent dev affordance — keeping it alive at the same
  path costs nothing and was promised by the Phase 06 UI-SPEC.

---

## 10. Accessibility

| Element | Requirement |
|---------|-------------|
| Trade-bar error | `<p role="alert">` — screen readers announce the new error text when it appears (D-07 spec). |
| Header totals | **Recommendation** (not required for Phase 07): `aria-live="polite"` on the numeric `<span>` so balance changes after trades are announced. Plan may include or skip. |
| Connection dot | `title="Live|Reconnecting…|Disconnected"` + `aria-label="SSE connected|reconnecting|disconnected"`. Dot is not interactive in Phase 07 (no `role="button"`). |
| Interactive rows | `tabIndex={0}`, `role="button"`, `aria-label="Select {ticker}"`, handle both `onClick` and `onKeyDown` Enter/Space. |
| Focus rings | `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-blue` on every focusable element (inputs, buttons, rows). |
| Color as only indicator | P&L and daily-change % always carry a sign prefix (`+`/`-`) alongside the color so meaning survives colorblind users and high-contrast modes. |

---

## 11. Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | *(not initialized)* | not applicable |
| *(no third-party registries)* | *(none)* | not applicable |

No `components.json`, no `shadcn view` gates to run. All Phase 07 components
are hand-authored inside `frontend/src/components/terminal/`. Only two npm
packages are added: `lightweight-charts` (named by PLAN.md §10) and
`@tanstack/react-query` (07-RESEARCH §1). Both are first-party
TradingView / TanStack libraries — standard, audited, widely deployed.

---

## 12. Component Inventory

| Component | Path | Role |
|-----------|------|------|
| `<Providers>` | `src/app/providers.tsx` (NEW) | `'use client'` — wraps `QueryClientProvider` inside `PriceStreamProvider`; mounted from `layout.tsx` |
| Terminal page | `src/app/page.tsx` (REPLACE body) | Renders the three-column grid with the five panels |
| `<Header>` | `src/components/terminal/Header.tsx` (NEW) | Header strip: dot + total + cash |
| `<ConnectionDot>` | `src/components/terminal/ConnectionDot.tsx` (NEW) | 10×10 colored dot with status-driven class |
| `<Watchlist>` | `src/components/terminal/Watchlist.tsx` (NEW) | Left column panel + row list |
| `<WatchlistRow>` | `src/components/terminal/WatchlistRow.tsx` (NEW) | One row: ticker + Δ% + price + sparkline |
| `<Sparkline>` | `src/components/terminal/Sparkline.tsx` (NEW) | 80×32 Lightweight Charts micro-chart |
| `<MainChart>` | `src/components/terminal/MainChart.tsx` (NEW) | Center panel; shows selected ticker, or empty-state copy when `selectedTicker === null` |
| `<PositionsTable>` | `src/components/terminal/PositionsTable.tsx` (NEW) | Right column top panel |
| `<PositionRow>` | `src/components/terminal/PositionRow.tsx` (NEW) | One row in PositionsTable |
| `<TradeBar>` | `src/components/terminal/TradeBar.tsx` (NEW) | Right column bottom panel |
| `lib/api/portfolio.ts` | NEW | `fetchPortfolio`, `postTrade`, `TradeError` |
| `lib/api/watchlist.ts` | NEW | `fetchWatchlist` (seed order only) |
| `lib/price-store.ts` | EXTEND | Add `sparklineBuffers`, `flashDirection`, `selectedTicker` slices + their selectors and `setSelectedTicker` action |
| `src/app/globals.css` | UPDATE | Override `--color-up` / `--color-down` to D-02 values in both `@theme` and `:root` |
| `src/app/layout.tsx` | EXTEND | Wrap children in `<Providers>` (adds `QueryClientProvider` alongside existing `PriceStreamProvider`) |

**Module size budget (inherited from Phase 06):** ≤120 lines per
`.tsx`/`.ts` file. Split when a file crosses the line.

---

## 13. Pre-population Sources

| Field | Source |
|-------|--------|
| Spacing scale 4px base | Phase 06 UI-SPEC §2 (inherited) |
| Typography sizes 28/20/16/14 + weights 400/600 | Phase 06 UI-SPEC §3 (inherited) |
| Monospace for numerics | Phase 06 UI-SPEC §3 + `/debug` precedent |
| `#0d1117` surface | PLAN.md §2; Phase 06 UI-SPEC §4 |
| `#1a1a2e` surface-alt | PLAN.md §2; Phase 06 UI-SPEC §4 |
| `#30363d` border-muted | Phase 06 UI-SPEC §4 |
| `#753991` purple Submit button | PLAN.md §2 "Purple Secondary: submit buttons" |
| `#26a69a` up / `#ef5350` down | CONTEXT.md D-02 (overrides Phase 06 UI-SPEC §4.1 placeholders) |
| 500ms price-flash duration | PLAN.md §2; CONTEXT.md D-01 |
| `bg-up/10` / `bg-down/10` flash classes | CONTEXT.md D-01; 07-RESEARCH §10 |
| 120-tick rolling sparkline buffer | CONTEXT.md D-03 |
| 80×32 sparkline size | CONTEXT.md "Claude's Discretion" recommendation |
| Lightweight Charts for main chart + sparklines | PLAN.md §10; CONTEXT.md D-04 |
| Ticker regex `^[A-Z][A-Z0-9.]{0,9}$` | CONTEXT.md D-05; 07-RESEARCH §5 (verified against `backend/app/watchlist/models.py:10`) |
| `<input type="number" min="0.01" step="0.01">` | CONTEXT.md D-06 |
| Trade-bar error copy map | CONTEXT.md D-07 (verbatim) |
| `detail.error` key name | 07-RESEARCH §7 (corrects D-07's informal "detail.code") |
| Implicit post-trade feedback | CONTEXT.md D-08 |
| Three-column grid `320px / 1fr / 360px` | CONTEXT.md "Claude's Discretion" + researcher default |
| `min-width: 1024px` desktop-first | CONTEXT.md "Claude's Discretion" |
| Connection dot 10×10 `w-2.5 h-2.5 rounded-full` | CONTEXT.md "Claude's Discretion"; 07-RESEARCH §9 |
| Route `/` replaces Phase 06 placeholder | PLAN.md §2 First Launch; researcher pick |
| `/debug` preserved unchanged | Phase 06 UI-SPEC §9 (out-of-scope removal) |
| TanStack Query for REST | 07-RESEARCH §4 recommendation |
| No toast system | CONTEXT.md D-07 |
| No emojis anywhere | `CLAUDE.md` project rule |
| WCAG AA contrast | Researcher default; inherited from Phase 06 §4.4 |

---

## 14. Handoff Notes

**For the planner:** Tasks should cover, in order:
1. Update `globals.css` to D-02 values in both `@theme` and `:root`. (One commit.)
2. Install `lightweight-charts@^5.2.0` and `@tanstack/react-query@^5.100.1`.
3. Create `src/app/providers.tsx` and wire it into `layout.tsx`.
4. Extend `price-store.ts` with `sparklineBuffers`, `flashDirection`,
   `selectedTicker` slices + selectors.
5. Create `lib/api/portfolio.ts` and `lib/api/watchlist.ts`.
6. Build the 7 terminal components (Header, ConnectionDot, Watchlist +
   WatchlistRow, Sparkline, MainChart, PositionsTable + PositionRow, TradeBar).
7. Replace the body of `src/app/page.tsx` with the three-column grid.
8. Write Vitest component tests per 07-RESEARCH §6 Test Map (15 tests covering
   FE-03, FE-04, FE-07, FE-08, FE-10).
9. Gate: `npm run test:ci && npm run build` green before phase verification.

**For the executor:**
- Copy color hex values verbatim — do not substitute `teal-600` or `red-400`
  for the declared custom tokens.
- Keep each component ≤120 lines. Split when it grows.
- Use `'use client'` at the top of every component that subscribes to the
  store or opens a Lightweight Charts instance.
- Import `{ createChart, LineSeries, ... }` from `'lightweight-charts'` — do
  NOT use the v4 `chart.addLineSeries()` pattern (removed in v5).
- Do not open a second `EventSource`. All live price data flows through the
  existing Phase 06 store.
- Do not install Recharts (reserved for Phase 08) or Framer Motion (not
  needed).
- All numeric cells: `font-mono tabular-nums text-right`.

**For the UI checker:** Validate that:
1. Spacing uses only multiples of 4px.
2. Typography declares exactly 4 sizes + 2 weights (inherited from Phase 06).
3. Color tokens match §4.1 verbatim — both `@theme` and `:root` blocks must
   carry `#26a69a` / `#ef5350`.
4. Copy matches §8 verbatim.
5. No emojis anywhere.
6. No out-of-scope surfaces were built (no heatmap, no P&L chart, no chat
   panel, no toast, no confirmation dialog).

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | *(not initialized — no components.json)* | not applicable |
| *(no third-party registries)* | *(none)* | not applicable |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
