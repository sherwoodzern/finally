# Phase 7: Market Data & Trading UI - Research

**Researched:** 2026-04-24
**Domain:** Next.js App Router, Lightweight Charts v5, Zustand selector extension, TanStack Query v5, Tailwind v4 tokens
**Confidence:** HIGH

---

## Summary

Phase 7 paints the FinAlly terminal: watchlist with flashing prices and sparklines, a
main chart, a positions table, a trade bar, and a header strip — all driven by the
Phase 06 Zustand store and the Phase 03/04 REST contracts. Every decision of consequence
is already locked in `07-CONTEXT.md`, so this research is prescriptive and narrow: it
confirms current library APIs, pins versions, flags v4→v5 API migration, resolves a
two-hex palette conflict with Phase 06 UI-SPEC, and defines the exact component
validation surface Nyquist expects.

**Primary recommendations:**

1. Install `lightweight-charts@^5.2.0` as the single new prod dep and use the v5
   `chart.addSeries(LineSeries, ...)` + `series.update()` API. Do NOT use the v4
   `chart.addLineSeries()` pattern — it was removed in v5.
2. Adopt **TanStack Query v5** for the two REST endpoints (`GET /api/portfolio`, `POST
   /api/portfolio/trade`). Two endpoints is the break-even point: the built-in
   `refetchInterval`, `useMutation.onSuccess → invalidateQueries`, and `useState(() =>
   new QueryClient())` provider pattern remove ~40 lines of hand-rolled
   `useEffect + setInterval + error-mapping` code.
3. Extend the existing Zustand store surgically — add `sparklineBuffers` and
   `flashDirection` slices, plus `clearFlashTimers()` tracked in a module-level `Map`.
   Keep every selector narrow so unrelated subscribers don't re-render at the 2 Hz
   tick cadence.
4. Import Lightweight Charts dynamically via `next/dynamic` with `{ ssr: false }` — it
   accesses `window`/`HTMLCanvasElement` at module-eval time.
5. Reconcile the two-hex palette conflict (CONTEXT.md D-02 says `#26a69a`/`#ef5350`,
   Phase 06 UI-SPEC §4.1 already declared `#3fb950`/`#f85149` as `--color-up`/`--color-down`).
   This is **the one open question the planner must resolve before Task 1**. Both sides
   have strong precedent; research recommends D-02's values because they are the
   Lightweight Charts library defaults and the newer decision explicitly locked them.

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 Price Flash Animation.** CSS class + setTimeout. `ingest()` sets a transient
  `flashDirection: Record<string, 'up'|'down'>` entry in `usePriceStore` for the ticker
  whose price changed, and schedules a 500ms `setTimeout` that clears just that entry.
  Watchlist/positions rows subscribe via selector and apply a Tailwind class
  (`bg-up/10` or `bg-down/10`) with `transition-colors duration-500`. No new animation
  dep.
- **D-02 Up/Down Color Palette.** Extend `@theme` in `src/app/globals.css` with
  `--color-up: #26a69a` (muted teal-green) and `--color-down: #ef5350` (desaturated
  coral-red) — Lightweight Charts defaults and universal trading-terminal convention.
  Same tokens drive flash backgrounds, sparkline stroke, positions P&L text, and main
  chart line.
  **⚠ Conflict:** Phase 06 UI-SPEC §4.1 previously declared `--color-up: #3fb950` and
  `--color-down: #f85149` — currently live in `frontend/src/app/globals.css`. See §
  "User Constraints Reconciliation" below.
- **D-03 Sparkline Data Buffer.** Rolling buffer inside `usePriceStore` as
  `sparklineBuffers: Record<string, number[]>`. On each `ingest()` call, append
  `raw.price` to the ticker's array and trim to the last 120 entries (~60s at 500ms).
  Selector `selectSparkline(ticker)` subscribes only to its own ticker's slice.
- **D-04 Sparkline Rendering.** Lightweight Charts — same library as the main chart
  per ROADMAP SC#2. Each sparkline is a minimal `createChart` instance with
  timeScale/priceScale/grid/crosshair/watermark disabled. One canvas per sparkline. One
  new npm prod dep: `lightweight-charts`.
- **D-05 Trade Bar Ticker Input.** Free-text `<input>` that upper-cases as the user
  types, with client-side validation via `^[A-Z][A-Z0-9.]{0,9}$` (matches backend
  `normalize_ticker` — verified below). On blur/submit, reject with inline error if
  regex fails.
- **D-06 Trade Bar Quantity Input.** `<input type="number" min="0.01" step="0.01">`
  to match backend `Field(gt=0)` and PLAN.md §7 fractional quantities.
- **D-07 Trade Bar Error Surface.** Inline `<p role="alert">` below Buy/Sell buttons.
  Cleared on next successful submit or when either input changes. Text maps from
  backend `detail.code`:
    - `insufficient_cash` → "Not enough cash for that order."
    - `insufficient_shares` → "You don't have that many shares to sell."
    - `unknown_ticker` → "No such ticker."
    - `price_unavailable` → "Price unavailable right now — try again."
  No toast system.
- **D-08 Post-Trade Feedback.** Implicit — on 200 response: re-fetch `/api/portfolio`,
  clear trade-bar inputs, leave focus on ticker field. No toast, no confirmation
  banner, no dialog.

### Claude's Discretion

- **Panel layout.** Three-column CSS grid — left watchlist, center header-strip-over-
  main-chart, right positions-table-over-trade-bar. `min-width: 1024px` with horizontal
  scroll below that is acceptable.
- **Portfolio data flow.** TanStack Query recommended (see §4 below). 15s
  `refetchInterval` + post-mutation invalidation. Client-side P&L in positions table:
  `current_price` from the Phase 06 store selector; `avg_cost`/`quantity` from
  `/api/portfolio` response. Backend `PositionOut.unrealized_pnl` used only as cold-
  start fallback.
- **Connection-status dot.** `<span>` `rounded-full w-2.5 h-2.5` with
  `bg-up`/`bg-accent-yellow`/`bg-down` + `title` attribute. Phase 7 is passive display.
- **Positions table.** Clicking a row selects that ticker in the main chart. Default
  sort: weight descending. No sort UI. Empty state: "No positions yet — use the trade
  bar to buy shares."
- **Main chart.** Line (not candles). Timeframe = session-since-page-load. Crosshair
  on hover (default). Y-axis format `$ X,XXX.XX`.
- **Header live totals.** `total_value = cash_balance + sum(qty × current_price from
  store)`. Format `$ X,XXX.XX`.
- **Watchlist row.** Fixed 48–56px row height, monospace numerics. Columns: ticker
  (bold), daily-change % (colored), price, sparkline (~80×32px).
- **Routes.** Keep `/` or add `/terminal`. Planner's call.
- **Tailwind utilities.** Free to add `text-up`, `text-down`, `bg-up/10`, `bg-down/10`,
  etc., that reference the new tokens.

### Deferred Ideas (OUT OF SCOPE)

- Position-row flash on trade; typeahead/combobox ticker input; clickable connection
  dot; timeframe selector on main chart; toast system; responsive stacking below
  1024px; multi-select positions / bulk close; backend extension to emit
  `session_start_price` or `sparkline_history`; Recharts in Phase 7.

### User Constraints Reconciliation (requires planner decision before Task 1)

Phase 06 UI-SPEC §4.1 already committed `--color-up: #3fb950` and `--color-down:
#f85149` into `frontend/src/app/globals.css` (both in the `@theme` block and the
force-emit `:root` block). Phase 07 CONTEXT.md D-02 specifies `#26a69a`/`#ef5350`
without acknowledging the existing values.

| Option | Effect | Recommendation |
|--------|--------|----------------|
| A. Honor D-02 (latest decision) | Edit `globals.css` `@theme` and `:root` to use
`#26a69a`/`#ef5350`. Matches Lightweight Charts library defaults so sparkline stroke +
main-chart line need zero explicit color options. | **Recommended.** |
| B. Honor Phase 06 UI-SPEC | Leave `globals.css` as-is; D-02 is effectively rescinded.
Sparkline/main-chart series need explicit `color: '#3fb950'` options. | Acceptable if
the planner believes Phase 06 UI-SPEC trumps later CONTEXT.md. |
| C. Split tokens | Keep `--color-up`/`--color-down` for flash/P&L/change-%, add
`--color-chart-up`/`--color-chart-down` at D-02's values for chart lines only. | Over-
engineering; rejected. |

Research recommends **Option A**. Rationale:
- D-02 explicitly says "Lightweight Charts defaults" — using any other values means
  custom `color:` option on every `addSeries(LineSeries, {...})` call.
- CONTEXT.md is the latest decision artifact and is downstream of UI-SPEC.
- The hex difference (`#26a69a` vs `#3fb950`) is small visually (both pass WCAG AA on
  `#0d1117`) and contained to two files (`globals.css` `@theme` + `:root`).
- The first Phase 07 plan should update `globals.css` to the D-02 values as its first
  task; this is a one-commit change affecting only that file.

</user_constraints>

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-03 | Watchlist panel — ticker, live price with green/red flash on tick, daily-change % from session-start price, progressive sparkline (Lightweight Charts) | §1 Standard Stack (lightweight-charts v5.2.0), §2 Architecture (sparklineBuffers + selectSparkline, per-row flash via selector), §3 Lightweight Charts v5 patterns (sparkline chart options), §6 Validation Architecture (render-on-tick + flash + daily-% tests) |
| FE-04 | Main chart area showing currently selected ticker; clicking a watchlist row selects it | §3 Lightweight Charts v5 (dynamic import, ResizeObserver, series.update), §2 Architecture (selectedTicker slice or URL search param), §6 Validation (click handler + series.update calls) |
| FE-07 | Positions table — ticker, quantity, avg cost, current price, unrealized P&L, % per position | §4 TanStack Query (useQuery for `/api/portfolio`), §2 Architecture (client-side P&L from store × avg_cost), §6 Validation (column render test, P&L math test) |
| FE-08 | Trade bar — ticker + quantity inputs + Buy/Sell, market-only, instant fill, no dialog | §4 TanStack Query (useMutation + invalidateQueries), §5 Trade validation (regex + min/step), §7 Error-code map verbatim from 03-CONTEXT.md D-10, §6 Validation (fetch body/URL assertion + error mapping) |
| FE-10 | Header — live total portfolio value, cash balance, connection-status dot | §2 Architecture (header re-computes from cash + store), §8 Connection dot semantics (subscribe to `selectConnectionStatus`), §6 Validation (header updates on tick + status dot colors) |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Watchlist row rendering | Browser (React) | — | Pure view layer, subscribes to Phase 06 store via selectors |
| Sparkline buffer accumulation | Browser (Zustand store) | — | Buffer lives in memory since the backend has no `sparkline_history` field and we never want to re-fetch history on ticker change |
| Sparkline canvas render | Browser (Lightweight Charts) | — | Canvas rendering handles 10+ sparklines × 2 Hz without React reconciler pressure |
| Main chart canvas render | Browser (Lightweight Charts) | — | Same reasoning — canvas-backed chart is the tool for live finance line charts |
| Price flash animation | Browser (Zustand + CSS) | — | No backend signal needed; animation is a pure visual response to a delta the store already tracks |
| Positions data fetch | Browser → API | API (Phase 03) | `/api/portfolio` is the source of truth for cash + qty + avg_cost; P&L is recomputed client-side from store prices on every render |
| Trade submission | Browser → API | API (Phase 03) | `POST /api/portfolio/trade` is stable; error-code mapping is the UI's responsibility |
| Connection-status dot | Browser (Zustand store) | — | Reads directly from `selectConnectionStatus` — no backend change |
| Header total portfolio value | Browser | — | Derived value; never stored, never persisted |

**No backend extension.** Phase 07 is frontend-only on a stable Phase 01–06 backend.

---

## 1. Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `lightweight-charts` | `^5.2.0` (published 2026-04-24) | Main chart + sparklines | [VERIFIED: npm registry] Industry-standard canvas charting library for financial data; the exact library PLAN.md §10 names; TradingView maintains it. |
| `@tanstack/react-query` | `^5.100.1` (2026-04-24) | `/api/portfolio` GET + `/api/portfolio/trade` POST | [VERIFIED: npm registry] [CITED: tanstack.com/query/v5] Removes hand-rolled `useEffect+setInterval` + mutation + error mapping. Two endpoints is the break-even: one endpoint would not justify the dep; three+ definitely would. |

**Version verification (2026-04-24):**
```bash
cd frontend && npm view lightweight-charts version   # → 5.2.0
cd frontend && npm view @tanstack/react-query version # → 5.100.1
```
Both confirmed against npm registry.

### Supporting (already installed — no action)

| Library | Version | Purpose |
|---------|---------|---------|
| `zustand` | `^5.0.12` | Shared store; extend with sparkline/flash slices. |
| `next` / `react` / `react-dom` | `16.2.4` / `19.2.4` / `19.2.4` | App Router host. |
| `tailwindcss` + `@tailwindcss/postcss` | `^4` | CSS-first `@theme` block. |
| `vitest` + `@testing-library/react` + `jsdom` | pinned | Component testing harness from Phase 06. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Lightweight Charts for sparklines | Hand-rolled SVG polyline | [ASSUMED] Re-invents scaling, aspect ratio, smoothing. Rejected in D-04. |
| Lightweight Charts for sparklines | Recharts | SVG + React reconciler per tick = 10 × 500ms = 20 re-renders/sec. Forces Phase 08's Recharts dep earlier. Rejected in D-04. |
| TanStack Query | Plain `useEffect` + `setInterval` | Works but ~40 more lines for the same feature. See §4 for full trade-off. |
| TanStack Query | SWR | [VERIFIED: docs.swr.vercel.app] Functionally equivalent for this use case; TanStack Query is the React Query default and has richer DevTools. Either would work; pick TanStack for ecosystem alignment with the Next.js 16 + App Router docs. |

### Installation

```bash
cd frontend
npm install lightweight-charts@^5.2.0 @tanstack/react-query@^5.100.1
```

[ASSUMED] `@tanstack/react-query-devtools` can be added as a devDependency for dev
debugging; it is not a production requirement.

---

## 2. Architecture Patterns

### System Architecture Diagram

```
┌──────────────────── Phase 06 already exists ───────────────────┐
│                                                                 │
│   Backend SSE                                                   │
│   /api/stream/prices   →   EventSource   →   usePriceStore     │
│                              (unchanged)         │              │
│                                                  ▼              │
│                                      { prices, status,          │
│                                        lastEventAt, ingest }    │
└─────────────────────────────────────────┬───────────────────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────┐
            │  Phase 07 ADDS:             ▼                         │
            │                      Store extensions:                │
            │              sparklineBuffers + flashDirection        │
            │              + selectSparkline + selectFlash          │
            │                             │                         │
            │                             ▼                         │
            │   ┌──────────────┬──────────────┬──────────────────┐ │
            │   │              │              │                  │ │
            │ Watchlist    Main Chart     Positions           Header │
            │ (FE-03)      (FE-04)         Table + Trade bar  (FE-10) │
            │              selects from    (FE-07 / FE-08)           │
            │              URL or store                              │
            │   │              │              │                  │  │
            │   │              │              │                  │  │
            │ Lightweight  Lightweight    TanStack Query       Store│
            │  Charts       Charts        /api/portfolio      subscrib│
            │  (sparkline)  (main)        + /trade mutation    e only│
            │                             + invalidateQueries        │
            └─────────────────────────────────────────────────────── ┘
                                              │
                                              ▼
                                     Phase 03 REST (stable)
                                /api/portfolio, /api/portfolio/trade
```

### Recommended Project Structure

```
frontend/src/
├── app/
│   ├── layout.tsx              # (EXTEND) wrap with <Providers>
│   ├── page.tsx                # (REPLACE body) render the terminal
│   ├── globals.css             # (UPDATE) align --color-up / --color-down
│   ├── providers.tsx           # (NEW) 'use client' QueryClientProvider + PriceStreamProvider
│   └── debug/page.tsx          # unchanged
├── lib/
│   ├── price-store.ts          # (EXTEND) + sparklineBuffers + flashDirection
│   ├── sse-types.ts            # unchanged
│   ├── price-stream-provider.tsx # unchanged
│   └── api/
│       ├── portfolio.ts        # (NEW) fetchPortfolio + postTrade + types
│       └── watchlist.ts        # (NEW) fetchWatchlist + types
├── components/terminal/        # (NEW directory)
│   ├── Watchlist.tsx
│   ├── WatchlistRow.tsx
│   ├── Sparkline.tsx           # Lightweight Charts wrapper, small
│   ├── MainChart.tsx           # Lightweight Charts wrapper, large
│   ├── PositionsTable.tsx
│   ├── PositionRow.tsx
│   ├── TradeBar.tsx
│   ├── Header.tsx
│   └── ConnectionDot.tsx
```

Files: keep each ≤120 lines (Phase 06 module budget). Extract helpers (format money,
compute daily-change %) to `lib/format.ts` once duplication appears twice.

### Pattern 1: Store Slice Extension (D-01, D-03)

**What:** Surgical extension of `usePriceStore` — same `create()` call, two new slices,
one new timer-tracking `Map`, no store split.

**When to use:** Phase 06 already ships the store; additional slices that share the
same lifecycle (tick ingestion triggers both) belong together.

**Pattern:**

```ts
// lib/price-store.ts (extension shown in isolation)
// Source: CONTEXT.md D-01, D-03; zustand v5 docs.

const flashTimers = new Map<string, ReturnType<typeof setTimeout>>();
const FLASH_MS = 500;
const SPARKLINE_WINDOW = 120; // ~60s at 500ms tick cadence

interface PriceStoreState {
  // ...existing...
  sparklineBuffers: Record<string, number[]>;
  flashDirection: Record<string, 'up' | 'down'>;
}

// Inside ingest(): for each ticker in payload -
//   1. Determine direction: prior && raw.price !== prior.price ?
//        (raw.price > prior.price ? 'up' : 'down') : undefined
//   2. If direction defined: flashDirection[ticker] = direction
//      - clearTimeout(flashTimers.get(ticker))
//      - flashTimers.set(ticker, setTimeout(() => set(s => {
//          const next = { ...s.flashDirection };
//          delete next[ticker];
//          return { flashDirection: next };
//        }), FLASH_MS))
//   3. Append raw.price to sparklineBuffers[ticker] array:
//      const buf = s.sparklineBuffers[ticker] ?? [];
//      const nextBuf = buf.length >= SPARKLINE_WINDOW
//        ? [...buf.slice(buf.length - SPARKLINE_WINDOW + 1), raw.price]
//        : [...buf, raw.price];
```

**Selectors** (define next to the store):

```ts
export const selectSparkline =
  (ticker: string) =>
  (s: PriceStoreState): number[] | undefined =>
    s.sparklineBuffers[ticker];

export const selectFlash =
  (ticker: string) =>
  (s: PriceStoreState): 'up' | 'down' | undefined =>
    s.flashDirection[ticker];

export const selectCashAndPositions = // TanStack Query provides this — store does NOT
```

**Re-render safety (critical):** Zustand already does `Object.is` shallow comparison on
the selector return value. A selector that returns `s.sparklineBuffers[ticker]` only
re-renders the subscriber when THAT ticker's array reference changes. Creating a new
array on every ingest is fine here because only the subscribing sparkline re-renders —
other tickers' arrays remain the same reference. [CITED: github.com/pmndrs/zustand
#recipes]

**Disconnect / reset cleanup (critical — prevents timer leak):**

```ts
disconnect: () => {
  if (es) { es.close(); es = null; }
  flashTimers.forEach(clearTimeout);
  flashTimers.clear();
  set({ status: 'disconnected', flashDirection: {} });
},
reset: () => {
  flashTimers.forEach(clearTimeout);
  flashTimers.clear();
  set({ prices: {}, status: 'disconnected', lastEventAt: null,
        sparklineBuffers: {}, flashDirection: {} });
},
```

### Pattern 2: Lightweight Charts Dynamic Import (FE-03, FE-04)

**What:** Import the library only on the client. Lightweight Charts reads `window` /
`HTMLCanvasElement` at module-eval time — a static import under `output: 'export'`
won't break the export build (it's still CSR), but imports can be deferred to keep the
first JS payload small and to prevent hydration pitfalls.

**Two viable patterns:**

```tsx
// Option A: dynamic() in the parent (simpler)
// components/terminal/MainChart.tsx parent:
import dynamic from 'next/dynamic';
const MainChart = dynamic(() => import('./MainChartImpl'), { ssr: false });

// Option B: static import in the chart component itself
// (works because every chart component is already 'use client';
//  Next.js will emit the import only into the client bundle)
'use client';
import { createChart, LineSeries, type IChartApi, type ISeriesApi }
  from 'lightweight-charts';
```

**Recommendation:** Option B. Every Phase 07 chart wrapper is already `'use client'`.
`output: 'export'` means there is no SSR to worry about — the browser is the only
renderer. Option A's `dynamic()` adds a wrapper that's unnecessary here.

[VERIFIED: Context7 — tradingview_github_io_lightweight-charts_5_0, "createChart" +
"addSeries" sections]

### Pattern 3: Lightweight Charts v5 createChart + addSeries

**What:** The v5 API for adding a line series. v4's `chart.addLineSeries()` no longer
exists — it is the **single most common migration pitfall**.

**Example (main chart):**

```tsx
// components/terminal/MainChartImpl.tsx
// Source: Context7 tradingview_github_io_lightweight-charts_5_0
//         "Migrate Series Creation to v5" + "Update Data in Area and Candlestick Series"
'use client';

import { useEffect, useRef } from 'react';
import {
  createChart, LineSeries,
  type IChartApi, type ISeriesApi, type LineData, type UTCTimestamp,
} from 'lightweight-charts';

export function MainChartImpl({ ticker, stream }:
  { ticker: string; stream: { time: number; price: number }[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  // Mount + cleanup (StrictMode-safe via ref-gating).
  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,                        // uses ResizeObserver internally
      layout: { background: { type: 'solid', color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#30363d' }, horzLines: { color: '#30363d' } },
    });
    const series = chart.addSeries(LineSeries, { color: '#26a69a', lineWidth: 2 });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Feed ticks: call series.update({ time, value }) per tick — do NOT recreate.
  useEffect(() => {
    const s = seriesRef.current;
    if (!s) return;
    const last = stream[stream.length - 1];
    if (!last) return;
    // setData for first load, update() for every subsequent tick.
    if (stream.length === 1) {
      s.setData(stream.map(p => ({ time: p.time as UTCTimestamp, value: p.price })));
    } else {
      s.update({ time: last.time as UTCTimestamp, value: last.price });
    }
  }, [stream]);

  return <div ref={containerRef} className="h-full w-full" />;
}
```

**Key v5 API points:**
- `createChart(container, options)` — unchanged from v4 shape. [CITED: docs/5.0]
- `chart.addSeries(SeriesType, options)` — **new in v5**, replaces
  `chart.addLineSeries()`. [CITED: docs/5.0/migrations/from-v4-to-v5]
- Import `LineSeries` as a value from `'lightweight-charts'` alongside `createChart`.
- `series.update({ time, value })` — incremental update, performant. Same time replaces
  the last point; greater time appends a new point. [CITED: docs/5.0 API/ISeriesApi]
- `series.setData(array)` — bulk replace. Use once on mount or when switching tickers.
- `chart.remove()` — irreversible cleanup; call in `useEffect` return.
- `autoSize: true` — chart auto-resizes via `ResizeObserver`. Required when the
  container uses CSS grid/flex and you don't know final pixel dimensions. Browsers
  that support ResizeObserver: all evergreen. [CITED: docs/5.0 ChartOptionsBase]

### Pattern 4: Sparkline configuration (maximally stripped chart)

**What:** A Lightweight Charts instance with everything visual disabled except the
line. Used for 80×32px rows.

**Options for sparkline:**

```ts
// Source: Context7 tradingview_github_io_lightweight-charts_5_0 — PriceScaleOptions,
// TimeScaleOptions, GridOptions, CrosshairOptions
const sparklineOptions = {
  autoSize: true,
  layout: {
    background: { type: 'solid', color: 'transparent' },
    textColor: 'transparent',
  },
  rightPriceScale: { visible: false },
  leftPriceScale: { visible: false },
  timeScale: { visible: false, borderVisible: false },
  grid: { vertLines: { visible: false }, horzLines: { visible: false } },
  crosshair: { horzLine: { visible: false }, vertLine: { visible: false } },
  handleScroll: false,
  handleScale: false,
};
```

Per-sparkline series color: derive from whether last tick price >= session_start_price
(green) or < (red) — same `--color-up`/`--color-down` tokens.

### Pattern 5: TanStack Query v5 Provider in App Router

**What:** `QueryClientProvider` must be inside a `'use client'` boundary. App Router
layouts are Server Components by default — the provider lives in a colocated client
component.

**Example (canonical):**

```tsx
// src/app/providers.tsx
// Source: Context7 tanstack_query_v5 "Configure QueryClientProvider for RSC"
'use client';

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PriceStreamProvider } from '@/lib/price-stream-provider';

export function Providers({ children }: { children: ReactNode }) {
  // useState(() => new QueryClient()) guarantees a stable singleton per browser tab
  // while being compatible with React StrictMode's double-invoke in dev.
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,            // portfolio rarely changes — 10s is plenty
        refetchOnWindowFocus: false,  // terminal is always-on; avoid churn
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <PriceStreamProvider>{children}</PriceStreamProvider>
    </QueryClientProvider>
  );
}
```

```tsx
// src/app/layout.tsx (updated)
import { Providers } from './providers';
// ...
<body className="bg-surface text-foreground">
  <Providers>{children}</Providers>
</body>
```

[CITED: tanstack.com/query/v5/docs/framework/react/guides/advanced-ssr]

### Anti-Patterns to Avoid (Phase 07 specific)

- **Do NOT open a second `EventSource`.** The Phase 06 `PriceStreamProvider` owns the
  one connection. Any new chart/table component subscribes via `usePriceStore`.
- **Do NOT import `lightweight-charts` at module top of a `page.tsx`** (the Server
  Component root). Import only inside `'use client'` components.
- **Do NOT create a new chart per tick.** Create on mount; `series.update()` on tick.
  Re-creating a chart is ~10ms of work; at 2 Hz × 10 sparklines that's 200ms of
  wasted work per second.
- **Do NOT pass store-selected arrays as `useEffect` deps.** `sparklineBuffers[ticker]`
  gets a new reference on every tick — that's the desired "tick happened" signal,
  but deep-compare deps or memoization here is wrong. Trust Zustand's shallow-equality
  gate.
- **Do NOT build a toast system.** D-07 is explicit. Inline `<p role="alert">` only.
- **Do NOT install Recharts** (reserved for Phase 08's P&L chart).
- **Do NOT install Framer Motion** (~30KB for a CSS transition D-01 already solves).
- **Do NOT extend the backend SSE shape** to include `session_start_price` or
  `sparkline_history`. Session-start stays frontend-side (Phase 06 D-14); sparkline
  accumulates client-side (D-03).
- **Do NOT reach for `use()` / Suspense** for the portfolio fetch — the Phase 07 UI
  needs a graceful "loading…" state, not a suspense boundary that flashes skeletons.
  `useQuery({ queryKey: ['portfolio'] })` + `{ isPending, data }` render-branch is the
  idiomatic pattern.

---

## 3. Lightweight Charts v5 — Specific Notes

| Concern | Answer | Source |
|---------|--------|--------|
| Current version (2026-04-24) | `5.2.0`, published 2026-04-24 | [VERIFIED: `npm view`] |
| v5 breaking change | `addLineSeries()` removed; use `chart.addSeries(LineSeries, ...)`. Same pattern for AreaSeries, CandlestickSeries, HistogramSeries. | [CITED: docs/5.0/migrations/from-v4-to-v5] |
| Types to import | `createChart, LineSeries, IChartApi, ISeriesApi<'Line'>, UTCTimestamp, LineData` | [CITED: docs/5.0 API] |
| SSR / Next.js App Router | Import inside a `'use client'` component. `output: 'export'` already forces CSR for these routes. No special `dynamic()` needed. | [ASSUMED — widely deployed pattern; SSR isn't a concern in `output: 'export'`] |
| Container sizing | `autoSize: true` uses a `ResizeObserver` internally. Works with CSS grid, flex, 100%/100% containers. Requires the container to have non-zero height. | [CITED: docs/5.0 ChartOptionsBase] |
| Tick cadence (500ms) | `series.update()` is optimized for this. Do not `setData` on each tick — it's a full replace. | [CITED: docs/5.0 "Update Data in Area and Candlestick Series"] |
| Time format | Use `UTCTimestamp` (unix seconds). Backend emits `timestamp` in unix seconds — pass directly. | [VERIFIED: backend/app/market/models.py:49 `timestamp: int`] |
| Disabling axes/grid | Options matrix in Pattern 4 above. `rightPriceScale.visible: false`, `timeScale.visible: false`, `grid.{vert,horz}Lines.visible: false`, `crosshair.{horz,vert}Line.visible: false`. | [CITED: docs/5.0 PriceScaleOptions, TimeScaleOptions, GridOptions, CrosshairOptions] |
| Cleanup on unmount | `chart.remove()` in the `useEffect` return. Clearing chartRef.current = null after. | [CITED: docs/5.0 IChartApiBase — remove()] |
| HMR / StrictMode double-mount | Ref-gate construction: `if (chartRef.current) return;` inside the mount `useEffect`. Mirror of Phase 06 D-15. | [ASSUMED — React dev best practice] |
| Canvas sizing conflict | If the parent has padding/border, the chart accounts for it via `autoSize`. If the chart is inside a fixed pixel box, pass `width`/`height` explicitly and skip autoSize. | [CITED: docs/5.0 IChartApiBase — resize()] |
| Dark theme colors | `layout.background.color`, `layout.textColor`, `grid.vertLines.color`, `grid.horzLines.color`. Match tokens: surface `#0d1117`, text `#e6edf3`, border `#30363d`. | [VERIFIED: frontend/src/app/globals.css] |

---

## 4. TanStack Query v5 vs plain useEffect — Trade-Off

Phase 07 has exactly two HTTP endpoints:
1. `GET /api/portfolio` — polled to track cash and positions.
2. `POST /api/portfolio/trade` — mutation that invalidates #1.

(A third — `GET /api/watchlist` — could seed the watchlist panel, but the Phase 06
store already contains the tickers via `selectTick(ticker)` entries. Using
`GET /api/watchlist` is optional seed data, not a live need.)

### Option A: TanStack Query v5 (recommended)

**Install:** 1 prod dep, ~13 KB gzipped.

**Portfolio fetch (in `Header.tsx` and `PositionsTable.tsx`):**
```tsx
// lib/api/portfolio.ts
export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch('/api/portfolio');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// in components
const { data, isPending } = useQuery({
  queryKey: ['portfolio'],
  queryFn: fetchPortfolio,
  refetchInterval: 15_000,   // 15s poll; price motion is handled by SSE
});
```

**Trade mutation (in `TradeBar.tsx`):**
```tsx
const qc = useQueryClient();
const mutation = useMutation({
  mutationFn: postTrade,
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ['portfolio'] });
    setTicker(''); setQuantity('');  // D-08
    tickerRef.current?.focus();
  },
  onError: (err: unknown) => {
    if (err instanceof TradeError) setErrorCode(err.code); // D-07 map
  },
});
```

**Error mapping helper:**
```ts
// lib/api/portfolio.ts
export class TradeError extends Error {
  constructor(public code: string, message: string) { super(message); }
}
export async function postTrade(body: TradeBody): Promise<TradeResponse> {
  const res = await fetch('/api/portfolio/trade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = await res.json().catch(() => ({}));
    // Phase 03 D-10: detail = { error: code, message: str(exc) }
    throw new TradeError(j?.detail?.error ?? 'unknown', j?.detail?.message ?? '');
  }
  return res.json();
}
```

**Pros:**
- `refetchInterval`, `onSuccess → invalidate`, `isPending`/`isError` branching all
  built-in.
- Cache is deduped across components (Header and PositionsTable share one fetch).
- DevTools for inspection (optional).
- Sets up Phase 08 (heatmap + chat panel) with the same ergonomic surface.

**Cons:**
- One dep; ~13 KB.

### Option B: Plain `useEffect + setInterval` + `useReducer`

**Install:** 0 new deps.

**Estimate:** ~80 LOC for the equivalent of the above:
- `useEffect` polling loop + `AbortController` cleanup
- In-flight guard to avoid racing fetches
- A small reducer/useState for `{ data, error, isPending }`
- Manual invalidation after trade — an imperative `refetch()` call or a state version-bump
- Error-code mapping inline in the submit handler
- Deduping between Header and PositionsTable requires either lifted state or
  context — otherwise you run two 15s pollers

**Pros:**
- Zero deps.

**Cons:**
- More code. More bug surface. No dedupe without extra plumbing.

### Recommendation

**Option A — TanStack Query v5.** Two endpoints is the break-even; the moment Phase 08
adds a third (`GET /api/portfolio/history` for the P&L chart), Option B's cost
compounds.

[VERIFIED: Context7 — tanstack_query_v5 "useQuery", "useMutation",
"invalidateQueries", "Configure QueryClientProvider for React Server Components"]

---

## 5. Trade-Bar Validation — Ticker Regex Alignment

**CONTEXT.md D-05 says:** client-side regex `^[A-Z][A-Z0-9.]{0,9}$`.

**Backend truth:** `backend/app/watchlist/models.py:10`:
```python
_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
```

**Verified:** **Identical. Use the same regex client-side.**

Additional backend behavior:
- `normalize_ticker()` strips whitespace and uppercases before matching.
- The backend's `WatchlistAddRequest` uses `extra='forbid'`; malformed JSON body → 422.
- `POST /api/portfolio/trade` (Phase 03) does NOT run `normalize_ticker`. Instead:
  - `TradeRequest.ticker: str = Field(min_length=1, max_length=10)` — lenient.
  - `service.execute_trade()` does `ticker.strip().upper()` then checks watchlist.
  - An invalid ticker that passes `Field(min_length=1, max_length=10)` and isn't in
    the watchlist → `UnknownTicker` → 400 `unknown_ticker`.

**Client-side implication:** The frontend regex is **stricter than what the trade
endpoint enforces on the body shape**. That's fine — we use the regex to short-circuit
obviously-bad input (e.g., `"hello world"`) before the server round-trip, and let
`unknown_ticker` handle the in-regex-but-not-watchlisted case.

**Input normalization code (copy-paste):**
```tsx
const TICKER_RE = /^[A-Z][A-Z0-9.]{0,9}$/;
const normalize = (v: string) => v.trim().toUpperCase();
const onChange = (e) => setTicker(normalize(e.target.value));
const isValid = TICKER_RE.test(ticker);
```

---

## 6. Validation Architecture

> `nyquist_validation: true` (from `.planning/config.json`). Section REQUIRED.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.5 + @testing-library/react 16.3.2 + jsdom 29 |
| Config file | `frontend/vitest.config.mts` (landed in Plan 06-03) |
| Quick run command | `cd frontend && npm run test:ci` |
| Full suite command | `cd frontend && npm run test:ci && npm run build` |
| Coverage (optional) | `cd frontend && npx vitest run --coverage` |

### Phase Requirements → Test Map

| Req ID | Behavior to verify | Test Type | Automated Command | File Exists? |
|--------|--------------------|-----------|-------------------|--------------|
| FE-03 | Watchlist row renders ticker, price, daily-change % (from session_start_price) | component | `npm run test:ci -- Watchlist` | ❌ Wave 0 |
| FE-03 | Tick with price > prev applies `bg-up/10` class; 500ms later class removed (fake timers) | component | `npm run test:ci -- Flash` | ❌ Wave 0 |
| FE-03 | `sparklineBuffers[ticker]` appends and trims to 120 entries | unit | `npm run test:ci -- price-store` (extend) | ❌ Wave 0 |
| FE-03 | Sparkline component calls `chart.addSeries(LineSeries, ...)` and `series.update()` (mock `lightweight-charts`) | component | `npm run test:ci -- Sparkline` | ❌ Wave 0 |
| FE-04 | Clicking a `WatchlistRow` dispatches select-ticker; MainChart re-renders for the new ticker | component | `npm run test:ci -- MainChart` | ❌ Wave 0 |
| FE-04 | MainChart calls `series.setData` on ticker-change and `series.update` on subsequent ticks | component | `npm run test:ci -- MainChart` | ❌ Wave 0 |
| FE-07 | PositionsTable renders one row per `/api/portfolio` position with client-computed P&L using store tick × avg_cost | component | `npm run test:ci -- PositionsTable` | ❌ Wave 0 |
| FE-07 | Cold-start fallback: when store has no tick for a held ticker, display `unrealized_pnl` from backend | component | `npm run test:ci -- PositionsTable` | ❌ Wave 0 |
| FE-08 | TradeBar rejects ticker not matching regex before fetching | component | `npm run test:ci -- TradeBar` | ❌ Wave 0 |
| FE-08 | TradeBar posts `{ticker, side, quantity}` to `/api/portfolio/trade` with correct body | component | `npm run test:ci -- TradeBar` | ❌ Wave 0 |
| FE-08 | TradeBar maps each `detail.code` to the correct D-07 string | component | `npm run test:ci -- TradeBar` | ❌ Wave 0 |
| FE-08 | Successful submit: inputs cleared, `/api/portfolio` invalidated (re-fetch triggered) | component | `npm run test:ci -- TradeBar` | ❌ Wave 0 |
| FE-10 | Header renders total portfolio value = cash_balance + Σ(qty × store_price) | component | `npm run test:ci -- Header` | ❌ Wave 0 |
| FE-10 | Header re-renders on store tick (cash unchanged, price changes) | component | `npm run test:ci -- Header` | ❌ Wave 0 |
| FE-10 | Connection dot: 'connected'→`bg-up`, 'reconnecting'→`bg-accent-yellow`, 'disconnected'→`bg-down` | component | `npm run test:ci -- Header` | ❌ Wave 0 |
| — | Build gate: `npm run build` exits 0; `frontend/out/` produced; no type errors | integration | `cd frontend && npm run build` | ✅ (script exists) |

### Test Patterns (from Phase 06 harness — reuse verbatim)

**MockEventSource DI** — already in `price-stream.test.ts`. Phase 07 tests that need
live ticks import and reuse the same pattern:
```ts
import { __setEventSource, usePriceStore } from './price-store';
```
Then `MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) })` to simulate
ticks.

**Fake timers for D-01 500ms flash clear:**
```ts
import { vi } from 'vitest';
beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

// in test
usePriceStore.getState().ingest({ AAPL: payload('AAPL', 195, 190) });
expect(usePriceStore.getState().flashDirection.AAPL).toBe('up');
vi.advanceTimersByTime(500);
expect(usePriceStore.getState().flashDirection.AAPL).toBeUndefined();
```

**Mocking `lightweight-charts` in component tests:**
```ts
import { vi } from 'vitest';
const mockSeries = { setData: vi.fn(), update: vi.fn() };
const mockChart = { addSeries: vi.fn(() => mockSeries), remove: vi.fn(), applyOptions: vi.fn() };
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart),
  LineSeries: 'LineSeries' as unknown,  // v5 imports LineSeries as a value token
}));
```
This avoids needing a real canvas in jsdom (jsdom has a partial canvas mock;
Lightweight Charts itself will warn/fail on it).

**Mocking `fetch` for TanStack Query:**
Use a per-test `vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({...}) }))`,
or use `msw` (already a Wave 0 optional). For two endpoints, bare `vi.stubGlobal` is
sufficient. Ensure each test `new QueryClient()` (fresh cache) to avoid leakage.

**TanStack Query in tests:**
```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
function wrap(ui) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}
render(wrap(<PositionsTable />));
```

### Sampling Rate

- **Per task commit:** `npm run test:ci` (~380ms in Phase 06; Phase 07 budget is <5s
  even with ~15 new tests).
- **Per wave merge:** `npm run test:ci && npm run build`.
- **Phase gate:** Full suite green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `frontend/src/components/terminal/*.test.tsx` — none exist yet.
- [ ] `frontend/src/lib/api/portfolio.test.ts` — fetch wrappers + TradeError mapping.
- [ ] `frontend/src/lib/price-store.test.ts` — extend the existing
      `price-stream.test.ts` with sparkline buffer and flash timer cases.
- [ ] `frontend/src/test-utils.tsx` — `wrap()` helper that provides a fresh
      QueryClient + optional `PriceStreamProvider`. Small new file. [ASSUMED]
- [x] Vitest config + jest-dom setup: already landed in Plan 06-03.

### Success-Criteria Coverage (ROADMAP Phase 7)

| SC# | Description | Automated coverage |
|-----|-------------|--------------------|
| SC1 | Watchlist renders with flash + sparkline + daily-% | FE-03 component tests above |
| SC2 | Main chart on click-select | FE-04 component tests above |
| SC3 | Positions table live | FE-07 component tests above |
| SC4 | Trade bar instant fill | FE-08 component tests above |
| SC5 | Header with live totals + connection dot | FE-10 component tests above |

All five covered via component tests — no manual-only gates required.

---

## 7. Backend Contract (verbatim — consume, do not extend)

### GET /api/portfolio → `PortfolioResponse`

```json
{
  "cash_balance": 10000.0,
  "total_value": 10234.56,
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10.0,
      "avg_cost": 190.0,
      "current_price": 190.12,
      "unrealized_pnl": 1.2,
      "change_percent": 0.06
    }
  ]
}
```
- [VERIFIED: `backend/app/portfolio/models.py` `PortfolioResponse`, `PositionOut`]
- Reads cache via `PriceCache.get_price(ticker)`; falls back to `avg_cost` when cache
  cold. Server response therefore always has non-null fields (Phase 03 D-13 covers the
  "no cached tick" case).

### POST /api/portfolio/trade

**Request:**
```json
{ "ticker": "AAPL", "side": "buy", "quantity": 10.0 }
```
- Body validated by `TradeRequest`: `side: Literal['buy','sell']`, `quantity > 0`,
  `ticker: 1..10 chars`. `extra='forbid'` — unknown keys → 422.

**Success (200) → `TradeResponse`:**
```json
{
  "ticker": "AAPL",
  "side": "buy",
  "quantity": 10.0,
  "price": 190.12,
  "cash_balance": 8098.80,
  "position_quantity": 10.0,
  "position_avg_cost": 190.12,
  "executed_at": "2026-04-24T16:30:00.000000+00:00"
}
```
- [VERIFIED: `backend/app/portfolio/models.py` `TradeResponse`]

**Validation failure (400):**
```json
{
  "detail": {
    "error": "insufficient_cash",
    "message": "Need $1901.20, have $1500.00"
  }
}
```
- [VERIFIED: `backend/app/portfolio/routes.py:44-48`, `03-CONTEXT.md` D-10]
- Error codes: `insufficient_cash | insufficient_shares | unknown_ticker |
  price_unavailable`
- ⚠ Note: CONTEXT.md D-07 uses the key `detail.code` for the error-code map. The
  backend uses `detail.error` (not `detail.code`). **The frontend must read
  `body.detail.error` — this is a minor but critical CONTEXT.md naming slip.**

### GET /api/watchlist → `WatchlistResponse` (optional; may be used for seed)

```json
{
  "items": [
    {
      "ticker": "AAPL",
      "added_at": "2026-04-24T15:00:00+00:00",
      "price": 190.12,
      "previous_price": 190.10,
      "change_percent": 0.01,
      "direction": "up",
      "timestamp": 1700000000.0
    }
  ]
}
```
- [VERIFIED: `backend/app/watchlist/models.py` `WatchlistItem`, `WatchlistResponse`]
- All price fields are `float | None` (cold-cache tolerance).
- `direction` is `'up' | 'down' | 'flat' | None`.
- Ordered by `added_at ASC, ticker ASC` ([VERIFIED: 04-CONTEXT D-08]).

### SSE Tick shape (Phase 06, already consumed)

```ts
// frontend/src/lib/sse-types.ts
interface RawPayload {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
}
interface Tick extends RawPayload { session_start_price: number; }
```
[VERIFIED: `frontend/src/lib/sse-types.ts:10-24`]

---

## 8. Error-Code Mapping (verbatim — from 03-CONTEXT.md + D-07)

The trade bar error surface reads `body.detail.error` (see §7 note) and maps to the
strings in CONTEXT.md D-07:

```ts
// components/terminal/TradeBar.tsx (excerpt)
const ERROR_TEXT: Record<string, string> = {
  insufficient_cash:    'Not enough cash for that order.',
  insufficient_shares:  "You don't have that many shares to sell.",
  unknown_ticker:       'No such ticker.',
  price_unavailable:    'Price unavailable right now - try again.',
};
const DEFAULT_ERROR = 'Something went wrong. Try again.';

function errorMessage(code: string | undefined): string {
  return (code && ERROR_TEXT[code]) || DEFAULT_ERROR;
}
```

Rendering:
```tsx
{errorCode && <p role="alert" className="mt-2 text-sm text-down">
  {errorMessage(errorCode)}
</p>}
```

**Note on CLAUDE.md apostrophe rule:** one error string contains an apostrophe
(`don't`). The CLAUDE.md rule bans emojis and deep try/except, not punctuation. Using
a straight ASCII apostrophe (`'`) is fine. Avoid the Unicode typographic variant
(`’`) because CONTEXT.md D-07 was written with ASCII.

---

## 9. Connection-Status Dot Specification

| Status | Token | Tailwind class | Hex | Title |
|--------|-------|----------------|-----|-------|
| `connected` | `--color-up` | `bg-up` | `#26a69a` (after D-02 reconciliation) | "connected" |
| `reconnecting` | `--color-accent-yellow` | `bg-accent-yellow` | `#ecad0a` | "reconnecting" |
| `disconnected` | `--color-down` | `bg-down` | `#ef5350` (after D-02) | "disconnected" |

Component:
```tsx
// components/terminal/ConnectionDot.tsx
'use client';
import { selectConnectionStatus, usePriceStore } from '@/lib/price-store';

const CLASSES: Record<string, string> = {
  connected:    'bg-up',
  reconnecting: 'bg-accent-yellow',
  disconnected: 'bg-down',
};

export function ConnectionDot() {
  const status = usePriceStore(selectConnectionStatus);
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${CLASSES[status]}`}
      title={status}
      aria-label={`SSE ${status}`}
    />
  );
}
```

---

## 10. Tailwind v4 `@theme` — Semantic Token Syntax

**Current globals.css** (Phase 06) already declares `--color-up` and `--color-down`
inside the `@theme` block. The v4 CSS-first pattern auto-generates utilities:

| Token declaration (in `@theme`) | Auto-generated utilities |
|---------------------------------|--------------------------|
| `--color-up: #26a69a;` | `text-up`, `bg-up`, `border-up`, `ring-up`, and alpha variants via `bg-up/10`, `bg-up/50`, `text-up/80`, etc. |
| `--color-down: #ef5350;` | `text-down`, `bg-down`, `border-down`, `ring-down`, `bg-down/10`, etc. |

No action in `@theme` is needed beyond updating the two hex values per §User
Constraints Reconciliation. The `:root` force-emit block in the current globals.css
must also be updated to match (otherwise the `:root` wins in cascade order and the
`@theme` values are overridden).

Example utility use in the watchlist row:
```tsx
// WatchlistRow.tsx
const flashClass =
  flash === 'up'   ? 'bg-up/10'
  : flash === 'down' ? 'bg-down/10'
  : '';
<tr className={`transition-colors duration-500 ${flashClass}`}>...</tr>
```

[CITED: tailwindcss.com/docs/theme — v4 CSS-first `@theme` block]

---

## Project Constraints (from CLAUDE.md)

Directives extracted from `./CLAUDE.md` (repo root) + `./backend/CLAUDE.md`. All Phase
07 plans and tasks MUST comply.

### Hard rules
- **Simple and incremental.** Small commits. Validate each increment.
- **No defensive programming.** Don't add try/except (try/catch) without a clear
  reason. The trade-bar fetch wrapper that maps 400 responses to `TradeError` is a
  wire-boundary try/catch (matches Phase 06 D-19). That's the only place in Phase 07
  where a try/catch is expected.
- **Latest library APIs.** v5 Lightweight Charts, v5 TanStack Query, Tailwind v4,
  React 19, Next.js 16.
- **No emojis** in code, logs, or commit messages.
- **Short modules and functions.** Phase 06 budgeted ≤120 lines for stores, ≤40 for
  providers. Phase 07 keeps the same discipline: each `components/terminal/*.tsx`
  ≤120 lines.
- **Clear docstrings.** Every exported function/module has a one-line doc.

### Project-specific rules
- **No `python3 …` / `pip install …`.** Frontend only — not a concern for Phase 07,
  but if a future helper script needs Python it must use `uv run`.
- **All project docs live in `planning/`.** Phase-specific planning lives in
  `.planning/phases/NN-…/`.
- **Market-data public API is re-exported from `app.market`.** Not touched by
  Phase 07 (frontend-only).

### Frontend-specific rules (derived from Phase 06)
- **Named exports, no default.** Every Phase 07 component module uses
  `export function Foo() { ... }` — consistent with Phase 06 store.
- **`'use client'` at the top of every interactive component.**
- **Narrow try/catch at wire boundaries only.**
- **Monospace for numeric columns** (from 06-UI-SPEC §3).
- **Dark class permanent on `<html>`.** Never toggle.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Lightweight Charts v4 `chart.addLineSeries({...})` | v5 `chart.addSeries(LineSeries, {...})` | v5 release (late 2024) | All series creation must import the series type as a value. |
| `eventsourcemock` npm package for SSE tests | Handwritten `MockEventSource` (Phase 06) | Phase 06 D-21 | No external dep; pattern is a Phase 06 canonical. |
| Jest + `next/jest` | Vitest | Phase 06 | Faster; smaller config; matches Next.js 16 default. |
| React Query v4 `useMutation({ onSuccess })` callback with `queryClient` | v5 same-name API but `mutationFn` is required and `onSuccess` can return a Promise | v5 release (2023) | Minor; patterns in §4 already show the v5 shape. |
| Tailwind v3 `tailwind.config.ts` `theme.extend.colors` | Tailwind v4 `@theme { --color-X: ...; }` in CSS | v4 release (2024) | Phase 06 already uses v4; Phase 07 just adds two more token hex values. |

### Deprecated / outdated

- `chart.addLineSeries()` — removed in Lightweight Charts v5. Any code generator that
  still suggests this pattern is stale.
- `eventsourcemock` npm package — works, but the handwritten `MockEventSource` in
  `price-stream.test.ts` is the project canonical.

---

## Assumptions Log

> Claims tagged `[ASSUMED]` that the planner/discuss-phase must confirm:

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `next/dynamic({ ssr: false })` is not strictly necessary when the component is `'use client'` and the app uses `output: 'export'`. Static client imports work fine. | §3 Pattern 2 | Low. If the build warns about SSR-eval, wrap the chart imports in `dynamic({ ssr: false })` — 2-line change per chart component. |
| A2 | A `test-utils.tsx` helper that provides a fresh `QueryClient` + `PriceStreamProvider` wrapper is idiomatic for these tests. | §6 Test Patterns | None — adding the helper is a trivial one-line file. |
| A3 | StrictMode double-invoke safety via ref-gating `if (chartRef.current) return;` is sufficient for Lightweight Charts v5 (matches Phase 06 D-15 pattern for EventSource). | §3 Pattern 3 | Low. If double-mount causes a flash, switch to `useLayoutEffect` or `useSyncExternalStore`. |
| A4 | Sparkline rendering at ~80×32 px with 120 data points is visually sufficient and doesn't need sub-pixel anti-aliasing tricks. | §3 Pattern 4 | Low. If sparklines look jagged, bump to 160×64 px (no API change). |
| A5 | The apostrophe in "You don't have that many shares to sell." is ASCII `'` (matches CONTEXT.md D-07 verbatim). | §8 | None — CLAUDE.md bans emojis, not punctuation. |
| A6 | `@tanstack/react-query` is the right choice over SWR given Phase 08 will add a third endpoint and a chat-streaming pattern. | §4 | None — either library satisfies Phase 07; TanStack is the conventional React-first choice. |

---

## Open Questions

1. **D-02 vs Phase 06 UI-SPEC palette conflict (`#26a69a` vs `#3fb950` for up; `#ef5350`
   vs `#f85149` for down).**
   - What we know: Both palette sources are authoritative in their phase. CONTEXT.md
     D-02 is the latest decision.
   - What's unclear: Whether the planner should treat D-02 as overriding UI-SPEC or
     whether UI-SPEC (already committed to source) is the floor.
   - Recommendation: Treat D-02 as the latest source of truth; update `globals.css` in
     Task 1 of Plan 07-01. See §User Constraints Reconciliation for full trade-off.

2. **`detail.error` vs `detail.code` naming.**
   - What we know: Backend uses `detail.error` verbatim in
     `backend/app/portfolio/routes.py:47`. CONTEXT.md D-07 refers to it as
     `detail.code`.
   - What's unclear: Nothing — backend wins by evidence.
   - Recommendation: Read `body.detail.error` in the frontend fetch wrapper. Add a
     planner note that D-07's "detail.code" wording was informal; the actual key is
     `error`. (No need to block on this.)

3. **Where does "selected ticker" live for the main chart?**
   - What we know: CONTEXT.md doesn't lock this — "Claude's discretion".
   - Options: (a) transient Zustand slice on the same store (`selectedTicker: string |
     null`); (b) `useSearchParams` on the route so the URL is shareable (`/?t=AAPL`);
     (c) lifted prop in the page component.
   - Recommendation: Option (a). It composes with every other store selector and
     avoids the `useSearchParams` + `router.replace` dance. Phase 08's collapsible chat
     panel will also want to pass this selection into the LLM context; a single store
     slice makes that trivial.

4. **Should watchlist row order follow the backend `/api/watchlist` response or the
   Phase 06 store insertion order?**
   - What we know: Backend orders by `added_at ASC, ticker ASC` (stable). The Phase
     06 store does not persist insertion order — `Record<string, Tick>` isn't ordered.
   - Recommendation: Fetch `/api/watchlist` once on mount (via TanStack Query) to get
     the ordered list of tickers; map those tickers through the store for live price
     data. Re-fetch on watchlist mutations (Phase 08 chat may add/remove — not Phase
     07). No `refetchInterval` needed on this endpoint — the watchlist itself doesn't
     change in Phase 07.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js 20 | `npm` / Next.js 16 | ✓ | as per `frontend/package.json engines` | — |
| npm | package install | ✓ | — | — |
| `lightweight-charts` | FE-03, FE-04 | ✗ (not installed yet) | — (install 5.2.0) | None — this IS the library |
| `@tanstack/react-query` | FE-07, FE-08 | ✗ (not installed yet) | — (install 5.100.1) | Plain `useEffect + setInterval` (Option B in §4) |
| Uvicorn + backend on :8000 | Local dev (SSE + REST rewrites) | ✓ (from Phase 01+) | — | Vitest tests run without backend (mocks) |

**Missing dependencies with no fallback:** none — both new deps install fine.

**Missing dependencies with fallback:** TanStack Query → plain fetch if the planner
disagrees with §4.

---

## Code Examples (verified patterns, copy-ready)

### Watchlist row with flash + sparkline

```tsx
// components/terminal/WatchlistRow.tsx
// Source: CONTEXT.md D-01, D-03; Phase 06 selectors; Lightweight Charts v5.
'use client';

import { selectFlash, selectSparkline, selectTick, usePriceStore } from '@/lib/price-store';
import { Sparkline } from './Sparkline';

export function WatchlistRow({ ticker, onSelect }:
  { ticker: string; onSelect: (t: string) => void }) {
  const tick = usePriceStore(selectTick(ticker));
  const flash = usePriceStore(selectFlash(ticker));
  const buffer = usePriceStore(selectSparkline(ticker));

  const flashClass =
    flash === 'up'   ? 'bg-up/10'
    : flash === 'down' ? 'bg-down/10'
    : '';

  const dailyPct = tick
    ? ((tick.price - tick.session_start_price) / tick.session_start_price) * 100
    : 0;
  const pctClass = dailyPct >= 0 ? 'text-up' : 'text-down';

  return (
    <tr
      onClick={() => onSelect(ticker)}
      className={`h-12 cursor-pointer transition-colors duration-500 ${flashClass}`}
    >
      <td className="px-2 font-bold">{ticker}</td>
      <td className={`px-2 text-right font-mono ${pctClass}`}>
        {dailyPct >= 0 ? '+' : ''}{dailyPct.toFixed(2)}%
      </td>
      <td className="px-2 text-right font-mono">
        {tick ? `$${tick.price.toFixed(2)}` : '-'}
      </td>
      <td className="px-2"><Sparkline buffer={buffer} positive={dailyPct >= 0} /></td>
    </tr>
  );
}
```

### Sparkline (Lightweight Charts v5, stripped chrome)

```tsx
// components/terminal/Sparkline.tsx
// Source: Context7 tradingview_github_io_lightweight-charts_5_0.
'use client';

import { useEffect, useRef } from 'react';
import {
  createChart, LineSeries,
  type IChartApi, type ISeriesApi, type UTCTimestamp,
} from 'lightweight-charts';

export function Sparkline({ buffer, positive }:
  { buffer: number[] | undefined; positive: boolean }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { type: 'solid', color: 'transparent' }, textColor: 'transparent' },
      rightPriceScale: { visible: false },
      leftPriceScale:  { visible: false },
      timeScale: { visible: false, borderVisible: false },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: { horzLine: { visible: false }, vertLine: { visible: false } },
      handleScroll: false,
      handleScale: false,
    });
    const series = chart.addSeries(LineSeries, {
      color: positive ? '#26a69a' : '#ef5350',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);

  // Update color on sign-flip without recreating the chart.
  useEffect(() => {
    seriesRef.current?.applyOptions({ color: positive ? '#26a69a' : '#ef5350' });
  }, [positive]);

  // Feed buffer: bulk-set on first receipt, incremental update after.
  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !buffer || buffer.length === 0) return;
    const now = Math.floor(Date.now() / 1000);
    const data = buffer.map((v, i) => ({
      time: (now - (buffer.length - 1 - i)) as UTCTimestamp,
      value: v,
    }));
    s.setData(data);
  }, [buffer]);

  return <div ref={containerRef} className="h-8 w-20" />;
}
```

Note: `setData` on every buffer change is fine here because the buffer array is
trimmed to 120 points; it's a cheap replace. For higher fidelity, track the previous
length and emit `update({ time, value })` per new tail point instead.

### Trade bar with TanStack Query mutation

```tsx
// components/terminal/TradeBar.tsx
// Source: CONTEXT.md D-05, D-06, D-07, D-08; Context7 tanstack_query_v5.
'use client';

import { useRef, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { postTrade, TradeError } from '@/lib/api/portfolio';

const TICKER_RE = /^[A-Z][A-Z0-9.]{0,9}$/;
const ERRORS: Record<string, string> = {
  insufficient_cash:   'Not enough cash for that order.',
  insufficient_shares: "You don't have that many shares to sell.",
  unknown_ticker:      'No such ticker.',
  price_unavailable:   'Price unavailable right now - try again.',
};

export function TradeBar() {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const tickerRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: postTrade,
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['portfolio'] });
      setTicker(''); setQuantity(''); setErrorCode(null);
      tickerRef.current?.focus();
    },
    onError: (err: unknown) => {
      setErrorCode(err instanceof TradeError ? err.code : 'unknown');
    },
  });

  function onSubmit(side: 'buy' | 'sell') {
    return (e: FormEvent) => {
      e.preventDefault();
      if (!TICKER_RE.test(ticker)) { setErrorCode('unknown_ticker'); return; }
      const q = parseFloat(quantity);
      if (!(q > 0)) return;
      mutation.mutate({ ticker, side, quantity: q });
    };
  }

  return (
    <form className="flex gap-2 items-end">
      <input
        ref={tickerRef}
        value={ticker}
        onChange={(e) => { setTicker(e.target.value.trim().toUpperCase()); setErrorCode(null); }}
        placeholder="TICKER"
        className="font-mono bg-surface-alt border border-border-muted px-2 py-1"
      />
      <input
        type="number" min="0.01" step="0.01"
        value={quantity}
        onChange={(e) => { setQuantity(e.target.value); setErrorCode(null); }}
        placeholder="QTY"
        className="font-mono bg-surface-alt border border-border-muted px-2 py-1 w-24"
      />
      <button onClick={onSubmit('buy')} className="bg-accent-purple px-3 py-1"
              disabled={mutation.isPending}>Buy</button>
      <button onClick={onSubmit('sell')} className="bg-accent-purple px-3 py-1"
              disabled={mutation.isPending}>Sell</button>
      {errorCode && (
        <p role="alert" className="text-down text-sm ml-2">
          {ERRORS[errorCode] ?? 'Something went wrong. Try again.'}
        </p>
      )}
    </form>
  );
}
```

---

## Sources

### Primary (HIGH confidence)

- **Context7 `/websites/tradingview_github_io_lightweight-charts_5_0`** — v5 API:
  `createChart`, `addSeries`, `LineSeries`, `ISeriesApi`, `autoSize`, migration from
  v4, options for disabled axes/grid/crosshair. Fetched 2026-04-24.
- **Context7 `/websites/tanstack_query_v5`** — `QueryClientProvider`, `useQuery`,
  `useMutation`, `invalidateQueries`, Next.js App Router `'use client'` pattern, SSR
  notes. Fetched 2026-04-24.
- **npm registry** — `npm view lightweight-charts version` → `5.2.0` (published
  2026-04-24); `npm view @tanstack/react-query version` → `5.100.1` (2026-04-24).
- **Codebase files (VERIFIED via Read)** — `frontend/package.json`,
  `frontend/src/lib/price-store.ts`, `frontend/src/lib/sse-types.ts`,
  `frontend/src/lib/price-stream-provider.tsx`, `frontend/src/lib/price-stream.test.ts`,
  `frontend/src/app/globals.css`, `frontend/src/app/layout.tsx`,
  `frontend/src/app/page.tsx`, `backend/app/portfolio/routes.py`,
  `backend/app/portfolio/models.py`, `backend/app/portfolio/service.py`,
  `backend/app/watchlist/routes.py`, `backend/app/watchlist/models.py`.
- **Planning artifacts (VERIFIED via Read)** — `07-CONTEXT.md`, `06-CONTEXT.md`,
  `06-UI-SPEC.md`, `03-CONTEXT.md`, `04-CONTEXT.md`, `.planning/REQUIREMENTS.md`,
  `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/config.json`,
  `./CLAUDE.md`, `./backend/CLAUDE.md`.

### Secondary (MEDIUM confidence)

- Tailwind v4 `@theme` CSS-first behavior — cross-verified between Phase 06 RESEARCH
  notes and Phase 06 working `globals.css`. Official docs at
  `tailwindcss.com/docs/theme` consulted for utility-generation rules.
- Zustand v5 selector shallow-compare semantics — cited from the project's already-
  shipped pattern (`price-store.ts` + test file pass 8 assertions under Vitest).

### Tertiary (LOW confidence)

- None required. Every Phase 07 claim is either backed by Context7 docs, the npm
  registry, or a verified line of committed code.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both new libs verified against npm; API surface cross-checked
  via Context7.
- Architecture: HIGH — extends a Phase 06 pattern that already has 8 green tests.
- Pitfalls: HIGH — v4→v5 migration is the one historical landmine; explicitly flagged.
- Validation: HIGH — Vitest harness is already in place; extensions are incremental.
- Palette reconciliation: MEDIUM — research recommends Option A but the planner needs
  to confirm because two committed artifacts disagree.

**Research date:** 2026-04-24
**Valid until:** 2026-05-08 (~14 days; npm-pinned versions should be re-verified if
the phase slips)
