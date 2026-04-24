# Phase 7: Market Data & Trading UI - Pattern Map

**Mapped:** 2026-04-24
**Files analyzed:** 17 new/modified
**Analogs found:** 16 / 17 (one file — `lib/api/portfolio.ts` — has no exact analog; RESEARCH §4 pattern is the seed)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `frontend/src/lib/price-store.ts` (MODIFY) | store (Zustand) | in-memory, SSE-driven fan-out | *(self — extends existing module)* | exact |
| `frontend/src/lib/api/portfolio.ts` (NEW) | wire-boundary fetch wrapper | request-response (REST) | `frontend/src/lib/price-store.ts` lines 66-76 (narrow try/catch at wire boundary, D-19) | role-mismatch, flow-match |
| `frontend/src/lib/api/watchlist.ts` (NEW) | wire-boundary fetch wrapper | request-response (REST) | `frontend/src/lib/api/portfolio.ts` (sibling, new) | role-match |
| `frontend/src/app/providers.tsx` (NEW) | client component (provider shell) | composition / context | `frontend/src/lib/price-stream-provider.tsx` | exact |
| `frontend/src/app/globals.css` (MODIFY) | config / theme tokens | CSS custom-properties | *(self — `@theme` + `:root`)* | exact |
| `frontend/src/app/layout.tsx` (MODIFY) | server component (root layout) | composition | *(self — add one wrapper)* | exact |
| `frontend/src/app/page.tsx` (MODIFY) | route entry (replace body) | composition | `frontend/src/app/debug/page.tsx` (client store-subscriber) | role-match |
| `frontend/src/components/terminal/Header.tsx` (NEW) | client component | subscribes store + TanStack `useQuery` | `frontend/src/app/debug/page.tsx` lines 31-50 (`usePriceStore` selector subscribe + live render) | role-match |
| `frontend/src/components/terminal/ConnectionDot.tsx` (NEW) | client component | subscribes `selectConnectionStatus` | `frontend/src/lib/price-store.ts` lines 102-103 + `debug/page.tsx` line 33 | exact |
| `frontend/src/components/terminal/Watchlist.tsx` (NEW) | client component (panel) | TanStack `useQuery` (seed) + renders rows | `frontend/src/app/debug/page.tsx` (table-of-rows pattern) | role-match |
| `frontend/src/components/terminal/WatchlistRow.tsx` (NEW) | client component (row) | subscribes `selectTick` / `selectFlash` / `selectSparkline` | `frontend/src/app/debug/page.tsx` lines 73-84 (row subscribing to store) | role-match |
| `frontend/src/components/terminal/Sparkline.tsx` (NEW) | client component (canvas wrapper) | reads buffer prop, drives Lightweight Charts | *(none — first chart component)* — RESEARCH §3 Pattern 3 / §Code Examples | no-analog; seed is RESEARCH |
| `frontend/src/components/terminal/MainChart.tsx` (NEW) | client component (canvas wrapper) | reads selected ticker + buffer, drives Lightweight Charts | `frontend/src/components/terminal/Sparkline.tsx` (once written) / RESEARCH §3 Pattern 3 | sibling / RESEARCH seed |
| `frontend/src/components/terminal/PositionsTable.tsx` (NEW) | client component (panel) | TanStack `useQuery(['portfolio'])` | `frontend/src/app/debug/page.tsx` (table-of-rows) + RESEARCH §4 | role-match |
| `frontend/src/components/terminal/PositionRow.tsx` (NEW) | client component (row) | subscribes `selectTick` + reads row props | `frontend/src/app/debug/page.tsx` lines 73-84 | role-match |
| `frontend/src/components/terminal/TradeBar.tsx` (NEW) | client component (form) | TanStack `useMutation` → POST /api/portfolio/trade | `frontend/src/lib/price-store.ts` lines 66-76 (wire-boundary try/catch) + RESEARCH §Code Examples | role-mismatch, flow-match |
| `frontend/src/test-utils.tsx` (NEW) | test helper | QueryClientProvider wrap | `frontend/src/lib/price-stream.test.ts` (test harness conventions) | role-match |
| Test files (`*.test.tsx`, `*.test.ts`) (NEW) | tests | Vitest + RTL + MockEventSource | `frontend/src/lib/price-stream.test.ts` (the canonical analog) | exact |

---

## Pattern Assignments

### `frontend/src/lib/price-store.ts` (MODIFY — store extension)

**Analog:** `frontend/src/lib/price-store.ts` (self). Phase 7 surgically adds three slices + two selectors + an action without reshaping existing fields.

**Imports pattern** (lines 1-10):

```ts
/**
 * Price store - single source of truth for ticker-keyed live price state.
 * Owns ONE EventSource for the app lifetime; managed by PriceStreamProvider.
 *
 * Analog of backend/app/market/cache.py (first-seen-price + idempotent lifecycle).
 * Decision refs: D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19.
 */

import { create } from 'zustand';
import type { ConnectionStatus, RawPayload, Tick } from './sse-types';
```

**Existing state shape** (lines 12-20):

```ts
interface PriceStoreState {
  prices: Record<string, Tick>;
  status: ConnectionStatus;
  lastEventAt: number | null;
  connect: () => void;
  disconnect: () => void;
  ingest: (payload: Record<string, RawPayload>) => void;
  reset: () => void;
}
```

**Narrow-state ingest pattern to extend** (lines 48-60):

```ts
ingest: (payload) => {
  const existing = get().prices;
  const next: Record<string, Tick> = { ...existing };
  for (const [ticker, raw] of Object.entries(payload)) {
    if (!isValidPayload(raw)) continue; // D-19: skip malformed entries silently
    const prior = next[ticker];
    next[ticker] = {
      ...raw,
      session_start_price: prior?.session_start_price ?? raw.price, // D-14: freeze first-seen
    };
  }
  set({ prices: next, lastEventAt: Date.now() });
},
```

**Narrow selector pattern to copy** (lines 96-103):

```ts
/** Subscribe to a single ticker's Tick. Returns undefined before first tick. */
export const selectTick =
  (ticker: string) =>
  (s: PriceStoreState): Tick | undefined =>
    s.prices[ticker];

/** Subscribe to the connection status (for Phase 7 FE-10 header dot). */
export const selectConnectionStatus = (s: PriceStoreState) => s.status;
```

**Delta (Phase 7 additions on top of the existing file):**
- Add to interface: `sparklineBuffers: Record<string, number[]>`, `flashDirection: Record<string, 'up' | 'down'>`, `selectedTicker: string | null`, `setSelectedTicker: (t: string | null) => void`.
- Add module-level `const flashTimers = new Map<string, ReturnType<typeof setTimeout>>()` + constants `FLASH_MS = 500`, `SPARKLINE_WINDOW = 120`.
- Inside `ingest()` per-ticker loop: compute direction (`prior && raw.price !== prior.price ? ... : undefined`), on non-null direction set `flashDirection[ticker]`, `clearTimeout(flashTimers.get(ticker))`, `flashTimers.set(ticker, setTimeout(() => set(s => { const next = { ...s.flashDirection }; delete next[ticker]; return { flashDirection: next }; }), FLASH_MS))`.
- Append to `sparklineBuffers[ticker]` and trim to last `SPARKLINE_WINDOW` entries.
- `disconnect()` and `reset()` must also `flashTimers.forEach(clearTimeout); flashTimers.clear()` and zero the two new slices.
- Add selectors: `selectSparkline(ticker)`, `selectFlash(ticker)`, `selectSelectedTicker = (s) => s.selectedTicker`.
- Preserve the existing "narrow try/catch at wire boundary" rule: do NOT add any try/catch for the new slices.

---

### `frontend/src/lib/api/portfolio.ts` (NEW — wire-boundary fetch wrapper)

**Analog (role-mismatch, flow-match):** `frontend/src/lib/price-store.ts` lines 66-82 (the single narrow try/catch at the wire boundary — Phase 06 D-19). No existing REST fetch wrapper exists; this is the first.

**Wire-boundary try/catch pattern to mirror** (price-store.ts lines 66-76):

```ts
es.onmessage = (event: MessageEvent) => {
  try {
    const parsed = JSON.parse(event.data) as Record<string, RawPayload>;
    get().ingest(parsed);
    if (get().status !== 'connected') set({ status: 'connected' });
  } catch (err) {
    // D-19: narrow try/catch at the wire boundary. Log + drop frame, do NOT rethrow.
    console.warn('sse parse failed', err, event.data);
  }
};
```

**Phase 7 shape (from RESEARCH §4 + §7 + §8):**

```ts
// lib/api/portfolio.ts
export interface TradeBody { ticker: string; side: 'buy' | 'sell'; quantity: number; }

export interface PositionOut {
  ticker: string; quantity: number; avg_cost: number;
  current_price: number; unrealized_pnl: number; change_percent: number;
}

export interface PortfolioResponse {
  cash_balance: number; total_value: number; positions: PositionOut[];
}

export interface TradeResponse {
  ticker: string; side: 'buy' | 'sell'; quantity: number; price: number;
  cash_balance: number; position_quantity: number; position_avg_cost: number;
  executed_at: string;
}

export class TradeError extends Error {
  constructor(public code: string, message: string) { super(message); }
}

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch('/api/portfolio');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function postTrade(body: TradeBody): Promise<TradeResponse> {
  const res = await fetch('/api/portfolio/trade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    // Narrow try/catch at the wire boundary - matches price-store.ts D-19.
    const j = await res.json().catch(() => ({}));
    // Backend truth: detail.error (NOT detail.code). See 07-RESEARCH §7.
    throw new TradeError(j?.detail?.error ?? 'unknown', j?.detail?.message ?? '');
  }
  return res.json();
}
```

**Delta vs analog:**
- Same "one narrow try/catch at wire boundary; no outer wrappers" rule.
- Response shape types mirror `backend/app/portfolio/models.py` verbatim.
- The `.catch(() => ({}))` on `res.json()` is the equivalent defensive-but-narrow move that `console.warn` is in the SSE onmessage.

---

### `frontend/src/lib/api/watchlist.ts` (NEW — wire-boundary fetch wrapper, seed-only)

**Analog:** sibling `frontend/src/lib/api/portfolio.ts` (same file shape, simpler body — no mutation, no error class).

**Phase 7 shape:**

```ts
// lib/api/watchlist.ts
export interface WatchlistItem {
  ticker: string;
  added_at: string;
  price: number | null;
  previous_price: number | null;
  change_percent: number | null;
  direction: 'up' | 'down' | 'flat' | null;
  timestamp: number | null;
}
export interface WatchlistResponse { items: WatchlistItem[]; }

export async function fetchWatchlist(): Promise<WatchlistResponse> {
  const res = await fetch('/api/watchlist');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
```

**Delta:** GET-only, no mutation, no custom error class — the watchlist endpoint's failure modes are network-level only in Phase 7 (no DELETE/POST from UI).

---

### `frontend/src/app/providers.tsx` (NEW — client provider shell)

**Analog:** `frontend/src/lib/price-stream-provider.tsx` (exact — single-responsibility client provider).

**Full analog** (price-stream-provider.tsx lines 1-22):

```tsx
'use client';

import { useEffect } from 'react';
import { usePriceStore } from './price-store';

/**
 * Owns the single EventSource for the app lifetime.
 * Mount once in the root layout (D-11). StrictMode-safe via the store's
 * idempotent connect() (D-15) - double-invoke is a no-op.
 */
export function PriceStreamProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const { connect, disconnect } = usePriceStore.getState();
    connect();
    return () => disconnect();
  }, []);

  return <>{children}</>;
}
```

**Phase 7 shape (from RESEARCH §2 Pattern 5):**

```tsx
// src/app/providers.tsx
'use client';

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PriceStreamProvider } from '@/lib/price-stream-provider';

/**
 * Root client provider: TanStack Query client + SSE EventSource owner.
 * Mounted once from layout.tsx. StrictMode-safe via useState-init singleton.
 */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 10_000,
        refetchOnWindowFocus: false,
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

**Delta vs analog:**
- Same `'use client'`, named export, one-line doc, React 19 child pattern.
- Composes two providers (new outer `QueryClientProvider` + existing `PriceStreamProvider`).
- `useState(() => new QueryClient(…))` pattern replaces the analog's `useEffect(connect/disconnect)` — same StrictMode-safety intent, different API.

---

### `frontend/src/app/globals.css` (MODIFY — theme tokens)

**Analog:** self (lines 3-21 existing `@theme` block; lines 40-47 existing `:root` force-emit block).

**Existing pattern to preserve** (globals.css lines 3-21):

```css
@theme {
  --color-surface:      #0d1117;
  --color-surface-alt:  #1a1a2e;
  --color-border-muted: #30363d;
  --color-foreground:        #e6edf3;
  --color-foreground-muted:  #8b949e;
  --color-accent-yellow: #ecad0a;
  --color-accent-blue:   #209dd7;
  --color-accent-purple: #753991;
  /* Semantic up/down - declared for Phase 7; not rendered in Phase 6 */
  --color-up:   #3fb950;
  --color-down: #f85149;
}
```

**Force-emit block pattern** (globals.css lines 40-47):

```css
:root {
  --color-accent-purple: #753991;
  --color-surface-alt:   #1a1a2e;
  --color-border-muted:  #30363d;
  --color-up:            #3fb950;
  --color-down:          #f85149;
  --color-foreground-muted: #8b949e;
}
```

**Delta:** Exactly two hex substitutions in both blocks (see UI-SPEC §4.1):
- `--color-up: #3fb950` → `#26a69a` (Lightweight Charts default green, D-02)
- `--color-down: #f85149` → `#ef5350` (Lightweight Charts default red, D-02)

No new tokens added. Tailwind v4 auto-generates `text-up`, `bg-up`, `bg-up/10`, `border-up` etc. from these two (RESEARCH §10).

---

### `frontend/src/app/layout.tsx` (MODIFY — root layout)

**Analog:** self (lines 1-18).

**Existing file** (layout.tsx 1-18):

```tsx
import type { Metadata } from 'next';
import './globals.css';
import { PriceStreamProvider } from '@/lib/price-stream-provider';

export const metadata: Metadata = {
  title: 'FinAlly',
  description: 'AI trading workstation',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-surface text-foreground">
        <PriceStreamProvider>{children}</PriceStreamProvider>
      </body>
    </html>
  );
}
```

**Delta:** Replace the `<PriceStreamProvider>` wrapper with `<Providers>` (which internally composes `QueryClientProvider` over `PriceStreamProvider` — see `app/providers.tsx`). `<html className="dark">` and `<body className="bg-surface text-foreground">` stay unchanged.

```tsx
import { Providers } from './providers';
// ...
<body className="bg-surface text-foreground">
  <Providers>{children}</Providers>
</body>
```

---

### `frontend/src/app/page.tsx` (MODIFY — terminal route body)

**Analog:** `frontend/src/app/debug/page.tsx` (closest — a `'use client'` route that composes store-subscribing children into a grid/table layout).

**Debug page pattern to model** (debug/page.tsx lines 31-50):

```tsx
'use client';
// ...
export default function DebugPage() {
  const prices = usePriceStore((s) => s.prices);
  const status = usePriceStore((s) => s.status);
  const lastEventAt = usePriceStore((s) => s.lastEventAt);

  const rows = Object.values(prices).sort((a, b) => a.ticker.localeCompare(b.ticker));

  return (
    <main className="min-h-screen p-6">
      <h1 className="text-xl font-semibold">Price Stream Debug</h1>
      {/* ... table ... */}
    </main>
  );
}
```

**Delta (per UI-SPEC §5.1):**
- Replace body with three-column CSS grid: `min-h-screen min-w-[1024px] bg-surface text-foreground p-6` → `grid grid-cols-[320px_1fr_360px] gap-6`.
- Render five panels: `<Watchlist />` (left), `<Header />` + `<MainChart />` (center column, flex col), `<PositionsTable />` + `<TradeBar />` (right column, flex col).
- `page.tsx` can stay a Server Component (composition only — no store hooks) because every rendered child is `'use client'`. Prefer that over making `page.tsx` client.

---

### `frontend/src/components/terminal/Header.tsx` (NEW)

**Analog:** `frontend/src/app/debug/page.tsx` lines 32-34 (narrow selector subscribe pattern) + RESEARCH §Code Examples for TanStack layer.

**Store-subscribe pattern to mirror** (debug/page.tsx lines 32-34):

```tsx
const prices = usePriceStore((s) => s.prices);
const status = usePriceStore((s) => s.status);
const lastEventAt = usePriceStore((s) => s.lastEventAt);
```

**UI-SPEC §5.6 markup contract:**

```tsx
'use client';
// Header.tsx
import { useQuery } from '@tanstack/react-query';
import { usePriceStore } from '@/lib/price-store';
import { fetchPortfolio } from '@/lib/api/portfolio';
import { ConnectionDot } from './ConnectionDot';

export function Header() {
  const { data } = useQuery({ queryKey: ['portfolio'], queryFn: fetchPortfolio, refetchInterval: 15_000 });
  const prices = usePriceStore((s) => s.prices);

  const cashBalance = data?.cash_balance ?? 0;
  const totalValue = cashBalance + (data?.positions ?? []).reduce(
    (sum, p) => sum + p.quantity * (prices[p.ticker]?.price ?? p.avg_cost), 0,
  );

  return (
    <header className="h-16 bg-surface-alt border border-border-muted rounded px-4 flex items-center gap-6">
      <ConnectionDot />
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-foreground-muted">Total</span>
        <span className="font-mono tabular-nums text-lg">${totalValue.toFixed(2)}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-sm text-foreground-muted">Cash</span>
        <span className="font-mono tabular-nums text-lg">${cashBalance.toFixed(2)}</span>
      </div>
    </header>
  );
}
```

**Delta vs analog:** Adds `useQuery(['portfolio'])` alongside store subscription; combines both to derive `totalValue` on every render. Follows Phase 06 `'use client'` + named-export rule. Copy strings `Total` / `Cash` are verbatim from UI-SPEC §8.

---

### `frontend/src/components/terminal/ConnectionDot.tsx` (NEW)

**Analog:** `frontend/src/lib/price-store.ts` line 103 (the `selectConnectionStatus` selector it consumes) + `frontend/src/app/debug/page.tsx` line 33 pattern.

**Selector being consumed** (price-store.ts line 103):

```ts
export const selectConnectionStatus = (s: PriceStoreState) => s.status;
```

**Phase 7 shape (UI-SPEC §5.7 verbatim):**

```tsx
'use client';

import type { ConnectionStatus } from '@/lib/sse-types';
import { selectConnectionStatus, usePriceStore } from '@/lib/price-store';

const CLASSES: Record<ConnectionStatus, string> = {
  connected:    'bg-up',
  reconnecting: 'bg-accent-yellow',
  disconnected: 'bg-down',
};
const TITLES: Record<ConnectionStatus, string> = {
  connected:    'Live',
  reconnecting: 'Reconnecting…',
  disconnected: 'Disconnected',
};

export function ConnectionDot() {
  const status = usePriceStore(selectConnectionStatus);
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${CLASSES[status]}`}
      title={TITLES[status]}
      aria-label={`SSE ${status}`}
    />
  );
}
```

**Delta vs analog:** Uses the existing exported `selectConnectionStatus` unchanged. Pattern is a one-selector, zero-state client component — simplest possible consumer of the Phase 06 store.

---

### `frontend/src/components/terminal/Watchlist.tsx` (NEW — panel)

**Analog:** `frontend/src/app/debug/page.tsx` (lines 39-88 — the "fetch a list of rows from the store and render as table" shape).

**Table scaffold pattern to mirror** (debug/page.tsx lines 52-65):

```tsx
<table className="mt-4 w-full border-collapse font-mono text-sm">
  <thead>
    <tr>
      <th className="text-left px-2 py-2 border-b border-border-muted text-foreground-muted">Ticker</th>
      <th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Price</th>
      {/* ... */}
    </tr>
  </thead>
  <tbody>
    {rows.length === 0 ? /* empty state */ : rows.map((t) => <tr key={t.ticker}>...</tr>)}
  </tbody>
</table>
```

**Delta (per UI-SPEC §5.2):**
- Source of row order: `useQuery({ queryKey: ['watchlist'], queryFn: fetchWatchlist })` once on mount; map `data.items[].ticker` to `<WatchlistRow ticker=… />`. Do NOT iterate the store's `prices` dict (order is insertion-dependent, not authoritative).
- Panel chrome: `<aside className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col">` with `<h2>Watchlist</h2>` header.
- No `<thead>` in watchlist (unlike positions) — row layout is implicit.
- Rows are `<WatchlistRow>` children, not inline `<tr>` — decomposed for selector granularity.

---

### `frontend/src/components/terminal/WatchlistRow.tsx` (NEW — row)

**Analog:** `frontend/src/app/debug/page.tsx` lines 73-84 (row that subscribes to store and formats numeric columns).

**Row pattern to mirror** (debug/page.tsx lines 73-84):

```tsx
<tr key={t.ticker} className="border-b border-border-muted">
  <td className="px-2 py-2 text-foreground">{t.ticker}</td>
  <td className="text-right px-2 py-2 text-foreground">{t.price.toFixed(4)}</td>
  <td className="text-right px-2 py-2 text-foreground">{t.previous_price.toFixed(4)}</td>
  <td className="text-right px-2 py-2 text-foreground">{t.change.toFixed(4)}</td>
  <td className="text-right px-2 py-2 text-foreground">{t.change_percent.toFixed(4)}</td>
  <td className="px-2 py-2 text-foreground">{t.direction}</td>
  {/* ... */}
</tr>
```

**Delta (from UI-SPEC §5.2 + RESEARCH Code Examples):**

```tsx
'use client';
// WatchlistRow.tsx
import { selectFlash, selectSparkline, selectTick, usePriceStore } from '@/lib/price-store';
import { Sparkline } from './Sparkline';

export function WatchlistRow({ ticker, onSelect }: { ticker: string; onSelect: (t: string) => void }) {
  const tick = usePriceStore(selectTick(ticker));
  const flash = usePriceStore(selectFlash(ticker));
  const buffer = usePriceStore(selectSparkline(ticker));

  const flashClass =
    flash === 'up'   ? 'bg-up/10' :
    flash === 'down' ? 'bg-down/10' : '';
  const dailyPct = tick
    ? ((tick.price - tick.session_start_price) / tick.session_start_price) * 100
    : 0;
  const pctClass = dailyPct >= 0 ? 'text-up' : 'text-down';

  return (
    <tr
      onClick={() => onSelect(ticker)}
      tabIndex={0}
      role="button"
      aria-label={`Select ${ticker}`}
      className={`h-14 border-b border-border-muted cursor-pointer transition-colors duration-500 ${flashClass} focus-visible:outline-2 focus-visible:outline-accent-blue`}
    >
      <td className="px-4 font-semibold">{ticker}</td>
      <td className={`px-2 font-mono tabular-nums text-right text-sm ${pctClass}`}>
        {tick ? `${dailyPct >= 0 ? '+' : ''}${dailyPct.toFixed(2)}%` : '—'}
      </td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">
        {tick ? `$${tick.price.toFixed(2)}` : '—'}
      </td>
      <td className="px-2 w-[96px]"><Sparkline buffer={buffer} positive={dailyPct >= 0} /></td>
    </tr>
  );
}
```

**Delta vs analog:** Three narrow selector subscriptions per row (matches Phase 06 D-13 selector-granularity rule). Daily-% formula per UI-SPEC §5.2 column contract. Em-dash empty-state symbol per UI-SPEC §8. Row height 56px vs debug's row-height-auto.

---

### `frontend/src/components/terminal/Sparkline.tsx` (NEW — Lightweight Charts wrapper, small)

**Analog:** None exists yet. Seed is RESEARCH §3 Pattern 3 + §"Code Examples — Sparkline" (lines 1250-1310 of RESEARCH).

**Pattern to copy (RESEARCH §Code Examples Sparkline, verbatim):**

```tsx
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
    if (!containerRef.current || chartRef.current) return;  // StrictMode ref-gate (mirrors D-15)
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

  useEffect(() => {
    seriesRef.current?.applyOptions({ color: positive ? '#26a69a' : '#ef5350' });
  }, [positive]);

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

**Delta vs Phase 06 patterns:**
- StrictMode ref-gate (`if (chartRef.current) return;`) mirrors `price-store.ts` line 64 (D-15 idempotent connect). Same discipline, different resource (chart vs EventSource).
- Narrow try/catch rule still applies — no try/catch inside these useEffects; Lightweight Charts throws on truly-broken inputs only, which the ref-gate prevents.
- `'use client'` + named export + one-line doc — matches Phase 06 component conventions.

---

### `frontend/src/components/terminal/MainChart.tsx` (NEW — Lightweight Charts wrapper, large)

**Analog:** Sibling `Sparkline.tsx` (once written) + RESEARCH §3 Pattern 3 MainChart example (RESEARCH lines 420-471).

**Pattern to copy (RESEARCH §3 Pattern 3, verbatim):**

```tsx
'use client';

import { useEffect, useRef } from 'react';
import {
  createChart, LineSeries,
  type IChartApi, type ISeriesApi, type LineData, type UTCTimestamp,
} from 'lightweight-charts';
import { selectSparkline, selectSelectedTicker, usePriceStore } from '@/lib/price-store';

export function MainChart() {
  const selectedTicker = usePriceStore(selectSelectedTicker);
  const buffer = usePriceStore(
    selectedTicker ? selectSparkline(selectedTicker) : () => undefined,
  );
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;
    const chart = createChart(containerRef.current, {
      autoSize: true,
      layout: { background: { type: 'solid', color: '#0d1117' }, textColor: '#e6edf3' },
      grid: { vertLines: { color: '#30363d' }, horzLines: { color: '#30363d' } },
    });
    const series = chart.addSeries(LineSeries, { color: '#26a69a', lineWidth: 2 });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => { chart.remove(); chartRef.current = null; seriesRef.current = null; };
  }, []);

  // setData on first load / ticker change; update() per subsequent tick.
  useEffect(() => {
    const s = seriesRef.current;
    if (!s || !buffer || buffer.length === 0) return;
    const now = Math.floor(Date.now() / 1000);
    s.setData(buffer.map((v, i) => ({
      time: (now - (buffer.length - 1 - i)) as UTCTimestamp,
      value: v,
    })));
  }, [selectedTicker, buffer]);

  if (!selectedTicker) {
    return (
      <section className="flex-1 bg-surface border border-border-muted rounded p-4 min-h-[400px] flex items-center justify-center">
        <p className="text-sm text-foreground-muted text-center">
          Select a ticker from the watchlist to view its chart.
        </p>
      </section>
    );
  }
  return (
    <section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
      <header className="flex items-baseline gap-4 mb-3">
        <h2 className="text-xl font-semibold">Chart: {selectedTicker}</h2>
      </header>
      <div ref={containerRef} className="flex-1 w-full" />
    </section>
  );
}
```

**Delta vs Sparkline sibling:**
- Full chart chrome visible (grid, time/price scales, crosshair default).
- Subscribes to two store slices (`selectSelectedTicker` + `selectSparkline(selectedTicker)`) rather than accepting props — this is the selected-ticker consumer.
- Empty state when `selectedTicker === null` (UI-SPEC §5.3 copy verbatim).
- `line width: 2` (main) vs `1` (sparkline).

---

### `frontend/src/components/terminal/PositionsTable.tsx` (NEW — panel)

**Analog:** `frontend/src/app/debug/page.tsx` (table-of-rows scaffold, lines 52-87) + RESEARCH §4 TanStack pattern.

**Table scaffold pattern** (debug/page.tsx lines 52-65, shown above under Watchlist).

**Phase 7 shape (UI-SPEC §5.4):**

```tsx
'use client';
import { useQuery } from '@tanstack/react-query';
import { fetchPortfolio } from '@/lib/api/portfolio';
import { PositionRow } from './PositionRow';

export function PositionsTable() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 15_000,
  });

  const positions = data?.positions ?? [];
  const sorted = [...positions].sort(
    (a, b) => (b.quantity * b.current_price) - (a.quantity * a.current_price),
  );

  return (
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
              <th className="text-right px-2 py-2 border-b border-border-muted">P&amp;L</th>
              <th className="text-right px-4 py-2 border-b border-border-muted">%</th>
            </tr>
          </thead>
          <tbody>
            {isPending ? (
              <tr><td colSpan={6} className="text-center py-6 text-sm text-foreground-muted">Loading positions…</td></tr>
            ) : isError ? (
              <tr><td colSpan={6} className="text-center py-6 text-sm text-foreground-muted">Couldn&apos;t load positions. Retrying in 15s.</td></tr>
            ) : sorted.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-6 text-sm text-foreground-muted">No positions yet — use the trade bar to buy shares.</td></tr>
            ) : sorted.map(p => <PositionRow key={p.ticker} position={p} />)}
          </tbody>
        </table>
      </div>
    </section>
  );
}
```

**Delta vs analog:**
- Data source flipped — `useQuery` (portfolio REST), not the Zustand store.
- Three UI states (loading/error/empty) in the same `<tbody>` branch pattern as debug's `rows.length === 0` check.
- `colSpan={6}` matches the six header columns (UI-SPEC §5.4).

---

### `frontend/src/components/terminal/PositionRow.tsx` (NEW — row)

**Analog:** `frontend/src/components/terminal/WatchlistRow.tsx` (sibling, once written) + `frontend/src/app/debug/page.tsx` lines 73-84.

**Phase 7 shape:**

```tsx
'use client';
import { selectFlash, selectTick, setSelectedTicker, usePriceStore } from '@/lib/price-store';
import type { PositionOut } from '@/lib/api/portfolio';

export function PositionRow({ position }: { position: PositionOut }) {
  const tick = usePriceStore(selectTick(position.ticker));
  const flash = usePriceStore(selectFlash(position.ticker));

  const price = tick?.price ?? position.current_price;
  const pnl = tick ? (tick.price - position.avg_cost) * position.quantity : position.unrealized_pnl;
  const pct = tick ? ((tick.price - position.avg_cost) / position.avg_cost) * 100 : position.change_percent;

  const flashClass =
    flash === 'up'   ? 'bg-up/10' :
    flash === 'down' ? 'bg-down/10' : '';
  const pnlColor = pnl >= 0 ? 'text-up' : 'text-down';

  return (
    <tr
      onClick={() => usePriceStore.getState().setSelectedTicker(position.ticker)}
      tabIndex={0}
      role="button"
      className={`h-12 border-b border-border-muted cursor-pointer hover:bg-surface-alt transition-colors duration-500 ${flashClass}`}
    >
      <td className="px-4 font-semibold">{position.ticker}</td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">{position.quantity}</td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">${position.avg_cost.toFixed(2)}</td>
      <td className="px-2 font-mono tabular-nums text-right text-sm">${price.toFixed(2)}</td>
      <td className={`px-2 font-mono tabular-nums text-right text-sm ${pnlColor}`}>
        {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
      </td>
      <td className={`px-4 font-mono tabular-nums text-right text-sm ${pnlColor}`}>
        {pct >= 0 ? '+' : ''}{pct.toFixed(2)}%
      </td>
    </tr>
  );
}
```

**Delta vs WatchlistRow sibling:**
- Takes a `position` prop (from TanStack Query cache) instead of fetching its own seed.
- Cold-start fallback logic: when `tick` is undefined, use backend's `current_price` / `unrealized_pnl` / `change_percent` (per CONTEXT.md "Claude's Discretion" + UI-SPEC §5.4).
- Flash mechanics identical to WatchlistRow.

---

### `frontend/src/components/terminal/TradeBar.tsx` (NEW — form + mutation)

**Analog:** `frontend/src/lib/price-store.ts` lines 66-82 (wire-boundary try/catch) + RESEARCH §"Trade bar with TanStack Query mutation" example (RESEARCH lines 1316-1391).

**Wire-boundary pattern being mirrored** (price-store.ts lines 66-76, shown above under `lib/api/portfolio.ts`).

**Phase 7 shape (UI-SPEC §5.5 + RESEARCH §Code Examples verbatim):**

```tsx
'use client';

import { useRef, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { postTrade, TradeError } from '@/lib/api/portfolio';

const TICKER_RE = /^[A-Z][A-Z0-9.]{0,9}$/;
const ERROR_TEXT: Record<string, string> = {
  insufficient_cash:    'Not enough cash for that order.',
  insufficient_shares:  "You don't have that many shares to sell.",
  unknown_ticker:       'No such ticker.',
  price_unavailable:    'Price unavailable right now — try again.',
};
const DEFAULT_ERROR = 'Something went wrong. Try again.';

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

  function submit(side: 'buy' | 'sell') {
    return (e: FormEvent) => {
      e.preventDefault();
      if (!TICKER_RE.test(ticker)) { setErrorCode('unknown_ticker'); return; }
      const q = parseFloat(quantity);
      if (!(q > 0)) return;
      mutation.mutate({ ticker, side, quantity: q });
    };
  }

  return (
    <section className="bg-surface-alt border border-border-muted rounded p-4">
      <form className="flex flex-col gap-3">
        {/* ticker input, quantity input, buy/sell buttons — see UI-SPEC §5.5 markup */}
        {errorCode && (
          <p role="alert" className="text-sm text-down">
            {ERROR_TEXT[errorCode] ?? DEFAULT_ERROR}
          </p>
        )}
      </form>
    </section>
  );
}
```

**Delta vs analog:**
- The wire-boundary try/catch lives in `lib/api/portfolio.ts` `postTrade` (not in this component) — mutation reuses it via `mutationFn: postTrade`. Phase 06 D-19 rule: one try/catch per wire call; don't wrap around `mutation.mutate`.
- Error-code → copy map is in-component (D-07 authoritative map).
- Ticker input upper-cases on `onChange` via `e.target.value.trim().toUpperCase()` (D-05).
- Quantity input is `<input type="number" min="0.01" step="0.01">` (D-06).
- Post-success behavior is the `onSuccess` callback block: invalidate, clear, focus (D-08).

---

### `frontend/src/test-utils.tsx` (NEW — test helper)

**Analog:** `frontend/src/lib/price-stream.test.ts` (Phase 06 canonical test conventions — `__setEventSource` DI + `MockEventSource` + `beforeEach(() => usePriceStore.getState().reset())`).

**Test reset pattern to mirror** (price-stream.test.ts lines 60-69):

```ts
describe('price-store SSE lifecycle', () => {
  beforeEach(() => {
    __setEventSource(MockEventSource as unknown as typeof EventSource);
    MockEventSource.reset();
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    usePriceStore.getState().disconnect();
  });
  // ...
```

**Phase 7 helper shape (RESEARCH §6 Test Patterns):**

```tsx
// src/test-utils.tsx
import { type ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';

/** Wrap a component tree in a fresh QueryClient so tests don't share cache. */
export function renderWithQuery(ui: ReactElement): RenderResult {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}
```

**Delta vs analog:**
- Same "fresh singleton per test" discipline the Phase 06 test file uses for `MockEventSource.reset()` and `usePriceStore.getState().reset()`.
- Adds the TanStack Query equivalent: `new QueryClient()` per call. `retry: false` prevents test timeouts on deliberate 4xx cases.

---

### Component test files (`**/terminal/*.test.tsx`, `lib/api/*.test.ts`, `lib/price-store.test.ts` — all NEW)

**Analog:** `frontend/src/lib/price-stream.test.ts` (the canonical Phase 06 test harness — exact match).

**Full analog already shown above.** Key excerpts reused in Phase 7:

**MockEventSource emit pattern** (price-stream.test.ts lines 23-46):

```ts
emitOpen() { this.readyState = MockEventSource.OPEN; this.onopen?.(new Event('open')); }
emitMessage(data: unknown) { this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) })); }
```

**Payload builder pattern** (price-stream.test.ts lines 48-58):

```ts
function payload(ticker: string, price: number, prev = price): RawPayload {
  return {
    ticker, price, previous_price: prev, timestamp: 1_700_000_000,
    change: +(price - prev).toFixed(4),
    change_percent: prev ? +((price - prev) / prev * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}
```

**Test lifecycle pattern** (lines 60-69, shown above).

**Phase 7 deltas (RESEARCH §6 Test Patterns):**
- Add `vi.useFakeTimers()` / `vi.useRealTimers()` in `beforeEach`/`afterEach` for price-store test cases that advance past 500ms flash-clear boundary.
- Add `vi.mock('lightweight-charts', () => ({ createChart: vi.fn(() => mockChart), LineSeries: 'LineSeries' }))` in Sparkline/MainChart component tests to avoid jsdom's incomplete canvas mock.
- Add `vi.stubGlobal('fetch', vi.fn().mockResolvedValue(...))` in TradeBar / PositionsTable / Header tests to simulate `/api/portfolio` and `/api/portfolio/trade` responses without network.
- Wrap components under test via `renderWithQuery(<TradeBar />)` from `test-utils.tsx`.
- Reuse the same `payload()` helper verbatim.

---

## Shared Patterns

### Pattern A — Narrow try/catch at wire boundary (Phase 06 D-19)

**Source:** `frontend/src/lib/price-store.ts` lines 66-76

**Apply to:** `lib/api/portfolio.ts` (`postTrade`, `fetchPortfolio`), `lib/api/watchlist.ts` (`fetchWatchlist`), `components/terminal/TradeBar.tsx` (do NOT wrap `mutation.mutate` — the try/catch already lives inside `postTrade`).

```ts
// From price-store.ts lines 66-76
es.onmessage = (event: MessageEvent) => {
  try {
    const parsed = JSON.parse(event.data) as Record<string, RawPayload>;
    get().ingest(parsed);
    if (get().status !== 'connected') set({ status: 'connected' });
  } catch (err) {
    // D-19: narrow try/catch at the wire boundary. Log + drop frame, do NOT rethrow.
    console.warn('sse parse failed', err, event.data);
  }
};
```

**Rule:** one try/catch per wire call, placed at the lowest level that touches network / parsing. Do not wrap higher-level business logic in try/catch. See CLAUDE.md "No defensive programming" and 07-RESEARCH §"Frontend-specific rules".

---

### Pattern B — Client-component conventions (Phase 06 established)

**Source:** `frontend/src/lib/price-stream-provider.tsx` (whole file) + `frontend/src/app/debug/page.tsx` lines 1-13

**Apply to:** Every Phase 7 `.tsx` file in `components/terminal/`, plus `app/providers.tsx` and `app/page.tsx` (if it becomes client).

```tsx
'use client';

/**
 * One-line module docstring describing what the component does and why.
 * Decision refs: D-XX (link back to CONTEXT or UI-SPEC).
 */

// …named-export, no default…
export function ComponentName(/* props */) { /* … */ }
```

**Rules:**
- `'use client'` at the top of every interactive component (debug/page.tsx line 1).
- **Named exports only, no default.** (Matches Phase 06 `export function PriceStreamProvider`.)
- One-line module docstring at the top describing purpose + Decision refs.
- Module size budget: **≤120 lines per .tsx/.ts file** (Phase 06 budget, UI-SPEC §12).

---

### Pattern C — Narrow selector subscription (Phase 06 D-13)

**Source:** `frontend/src/lib/price-store.ts` lines 96-103 (selector definitions) + `frontend/src/app/debug/page.tsx` lines 32-34 (consumer pattern).

**Apply to:** Every Phase 7 component that reads from `usePriceStore` — Header, ConnectionDot, WatchlistRow, PositionRow, MainChart.

```ts
// Definition (price-store.ts lines 97-103)
export const selectTick =
  (ticker: string) =>
  (s: PriceStoreState): Tick | undefined =>
    s.prices[ticker];

export const selectConnectionStatus = (s: PriceStoreState) => s.status;

// Consumer (debug/page.tsx lines 32-34; WatchlistRow similar)
const tick = usePriceStore(selectTick(ticker));
const status = usePriceStore(selectConnectionStatus);
```

**Rule:** Each selector returns the smallest slice needed. Zustand's `Object.is` shallow-compare prevents unrelated re-renders at the 2 Hz tick cadence (RESEARCH §2 Pattern 1 "Re-render safety (critical)").

---

### Pattern D — Monospace numeric columns (Phase 06 UI-SPEC §3 + `/debug`)

**Source:** `frontend/src/app/debug/page.tsx` lines 52-83.

**Apply to:** WatchlistRow (daily-%, price cells), PositionRow (qty, avg cost, price, P&L, %), Header (total, cash).

```tsx
<th className="text-right px-2 py-2 border-b border-border-muted text-foreground-muted">Price</th>
{/* … */}
<td className="text-right px-2 py-2 text-foreground">{t.price.toFixed(4)}</td>
```

**Phase 7 refinement (UI-SPEC §3):** every numeric cell uses `font-mono tabular-nums text-right`. Phase 06 `/debug` uses `font-mono text-sm` at the table level; Phase 7 applies per-cell so numeric and non-numeric columns can differ.

---

### Pattern E — Dark-theme token usage (Phase 06 UI-SPEC §4)

**Source:** `frontend/src/app/globals.css` `@theme` block + `frontend/src/app/layout.tsx` line 13 (`bg-surface text-foreground`).

**Apply to:** Every Phase 7 component — use `bg-surface` / `bg-surface-alt` / `border-border-muted` / `text-foreground` / `text-foreground-muted` / `text-accent-*` / `bg-accent-*` only. Add derived `bg-up`, `bg-down`, `bg-up/10`, `bg-down/10`, `text-up`, `text-down` (auto-generated by Tailwind v4 from the two new `@theme` tokens).

```css
/* globals.css lines 5-21 */
--color-surface:      #0d1117;
--color-surface-alt:  #1a1a2e;
--color-border-muted: #30363d;
--color-foreground:        #e6edf3;
--color-foreground-muted:  #8b949e;
--color-accent-purple: #753991;
--color-up:   #26a69a;   /* Phase 7 D-02 */
--color-down: #ef5350;   /* Phase 7 D-02 */
```

**Rule:** No raw hex values in component className strings. No arbitrary `px-[Npx]` values (spacing scale 4px only, UI-SPEC §2).

---

### Pattern F — Vitest + RTL + MockEventSource + DI

**Source:** `frontend/src/lib/price-stream.test.ts` (whole file).

**Apply to:** Every new `*.test.tsx` / `*.test.ts` in Phase 7.

Key reusable pieces: the `MockEventSource` class (lines 5-46), the `payload()` builder (lines 48-58), the `beforeEach`/`afterEach` lifecycle (lines 60-69).

**Rule (Phase 7 additions, RESEARCH §6):**
- Use `vi.useFakeTimers()` for flash-clear tests (D-01 500ms).
- Use `vi.mock('lightweight-charts', …)` for Sparkline/MainChart tests (jsdom can't host a real canvas).
- Use `vi.stubGlobal('fetch', …)` for TanStack Query tests; pair with `renderWithQuery(ui)` from `test-utils.tsx`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/components/terminal/Sparkline.tsx` | canvas wrapper | Lightweight Charts canvas | No chart components exist yet in the repo. Seed pattern is RESEARCH §Code Examples (verbatim lines provided above). This is the first Lightweight Charts integration; once landed, `MainChart.tsx` uses it as the sibling analog. |

Even this file inherits three existing patterns: Pattern B (`'use client'`, named export, docstring), the D-15 StrictMode ref-gate (`if (chartRef.current) return;` — mirrors `price-store.ts:64`), and the `useEffect` cleanup discipline (`return () => chart.remove()` — mirrors `price-stream-provider.tsx:18`).

---

## Metadata

**Analog search scope:** `frontend/src/**/*.{ts,tsx}` (Phase 06 complete surface) + Phase 7 `07-RESEARCH.md` §Code Examples for files with no existing analog.

**Files scanned:** `frontend/src/lib/price-store.ts`, `frontend/src/lib/sse-types.ts`, `frontend/src/lib/price-stream-provider.tsx`, `frontend/src/lib/price-stream.test.ts`, `frontend/src/app/layout.tsx`, `frontend/src/app/page.tsx`, `frontend/src/app/debug/page.tsx`, `frontend/src/app/globals.css`, `frontend/package.json`, `frontend/vitest.config.mts` (10 files).

**Pattern extraction date:** 2026-04-24

---

## PATTERN MAPPING COMPLETE
