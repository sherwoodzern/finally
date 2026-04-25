# Phase 8: Portfolio Visualization & Chat UI - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 30 new + 9 modified = 39 total
**Analogs found:** 36 / 39 (3 net-new with no in-repo analog → use RESEARCH.md patterns)

This map answers, per Phase 8 file, "what existing file should this copy
from, and which exact lines?" The Phase 7 surface (Watchlist, MainChart,
PositionRow, PositionsTable, TradeBar, ConnectionDot, Header) is the dominant
analog source — Phase 8 components are the same pattern with different inner
content (Recharts SVG instead of lightweight-charts canvas; chat thread
instead of table rows).

---

## File Classification

### Frontend — NEW components

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `frontend/src/components/portfolio/Heatmap.tsx` | component | request-response | `frontend/src/components/terminal/PositionsTable.tsx` | exact (panel + `useQuery(['portfolio'])` + Recharts swap-in for table) |
| `frontend/src/components/portfolio/HeatmapCell.tsx` | component | render-only | `frontend/src/components/terminal/PositionRow.tsx` | role-match (small "cell" inside parent; reads ticker + computes display) |
| `frontend/src/components/portfolio/PnLChart.tsx` | component | request-response | `frontend/src/components/terminal/MainChart.tsx` | exact (chart panel pattern; swap lightweight-charts → recharts; swap store buffer → `useQuery(['portfolio','history'])`) |
| `frontend/src/components/portfolio/PnLTooltip.tsx` (research-recommended split) | component | render-only | (no existing tooltip in repo) | NEW — use RESEARCH.md Pattern 2 |
| `frontend/src/components/chat/ChatDrawer.tsx` | component | layout | `frontend/src/components/terminal/Watchlist.tsx` | role-match (panel chrome + child list) |
| `frontend/src/components/chat/ChatHeader.tsx` (research-recommended split) | component | render-only | `frontend/src/components/terminal/Header.tsx` lines 38-54 | role-match (header strip with toggle replacing total/cash slots) |
| `frontend/src/components/chat/ChatThread.tsx` | component | request-response + mutation | `frontend/src/components/terminal/PositionsTable.tsx` + `frontend/src/components/terminal/TradeBar.tsx` | role-match (PositionsTable for `useQuery` + loading/empty branches; TradeBar for `useMutation` + invalidation) |
| `frontend/src/components/chat/ChatInput.tsx` | component | event-driven | `frontend/src/components/terminal/TradeBar.tsx` lines 71-128 | exact (form + disabled-during-pending + focus management + named onSuccess) |
| `frontend/src/components/chat/ChatMessage.tsx` | component | render-only | `frontend/src/components/terminal/PositionRow.tsx` | role-match (single row/bubble in a list; reads its own props; conditional class application) |
| `frontend/src/components/chat/ActionCard.tsx` | component | render-only | `frontend/src/components/terminal/ConnectionDot.tsx` | role-match (status-driven class lookup table — `CLASSES[status]` pattern) |
| `frontend/src/components/chat/ActionCardList.tsx` | component | render-only | `frontend/src/components/terminal/PositionsTable.tsx` lines 34-87 | role-match (sort/order + `.map()` over typed array) |
| `frontend/src/components/chat/ThinkingBubble.tsx` | component | render-only | (no existing pure-CSS animation primitive) | NEW — use RESEARCH.md Pattern 6 |
| `frontend/src/components/skeleton/SkeletonBlock.tsx` (research-recommended; CONTEXT mentions `common/SkeletonBlock`) | component | render-only | (no existing skeleton primitive) | NEW — use RESEARCH.md Pattern 7 |
| `frontend/src/components/terminal/TabBar.tsx` | component | event-driven | `frontend/src/components/terminal/ConnectionDot.tsx` + `frontend/src/components/terminal/PositionRow.tsx` lines 35-49 | role-match (button-like surface; reads `selectedTab` from store, dispatches `setSelectedTab`) |

### Frontend — NEW API client + fixtures

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `frontend/src/lib/api/chat.ts` | api-client | REST | `frontend/src/lib/api/portfolio.ts` | exact (fetch + ok-check + JSON parse + `detail.error`/`detail.message` errors) |
| `frontend/src/lib/fixtures/portfolio.ts` | fixture | static | `frontend/src/components/terminal/PositionsTable.test.tsx` lines 64-76 (inline body) | role-match (extract inline test body to fixture file) |
| `frontend/src/lib/fixtures/history.ts` | fixture | static | (none — no existing history fixture) | NEW — straightforward `SnapshotOut[]` array |
| `frontend/src/lib/fixtures/chat.ts` | fixture | static | (none — no existing chat fixture) | NEW — `ChatMessageOut[]` covering all 6 statuses |

### Frontend — NEW test files

| New Test File | Closest Analog Test | Match Quality |
|---------------|---------------------|---------------|
| `frontend/src/components/portfolio/Heatmap.test.tsx` | `frontend/src/components/terminal/PositionsTable.test.tsx` | exact (same `useQuery` + `stubPortfolio` fetch stub harness) |
| `frontend/src/components/portfolio/HeatmapCell.test.tsx` | `frontend/src/components/terminal/Sparkline.test.tsx` | role-match (small render-only component, prop-driven assertions) |
| `frontend/src/components/portfolio/PnLChart.test.tsx` | `frontend/src/components/terminal/MainChart.test.tsx` | exact (mock chart lib + assert addSeries args; swap recharts for lightweight-charts) |
| `frontend/src/components/chat/ChatDrawer.test.tsx` | `frontend/src/components/terminal/Header.test.tsx` | role-match (state-driven className assertion) |
| `frontend/src/components/chat/ChatThread.test.tsx` | `frontend/src/components/terminal/PositionsTable.test.tsx` + `TradeBar.test.tsx` | exact (combined: fetch-stub + mutation roundtrip) |
| `frontend/src/components/chat/ChatInput.test.tsx` | `frontend/src/components/terminal/TradeBar.test.tsx` | exact (`fillAndClick` keyboard pattern) |
| `frontend/src/components/chat/ActionCard.test.tsx` | `frontend/src/components/terminal/Header.test.tsx` lines 91-128 | role-match (className-by-status assertions) |
| `frontend/src/components/chat/ActionCardList.test.tsx` | `frontend/src/components/terminal/PositionsTable.test.tsx` lines 114-133 | exact (DOM-order assertion via `tbody tr` querySelectorAll → `.map`) |
| `backend/tests/test_static_mount.py` | `backend/tests/test_lifespan.py` lines 66-73 (`test_includes_sse_router_during_startup`) | role-match (LifespanManager + assert routes/mounts on `app.router.routes`) |

### Modified files

| File | Change | Closest Analog (for the new behavior) | Match Quality |
|------|--------|---------------------------------------|---------------|
| `frontend/src/components/terminal/Terminal.tsx` | wrap existing 3-col grid in `flex flex-row` + add `<ChatDrawer />` sibling + insert `<TabBar />` in center column | itself (Phase 7); RESEARCH.md Pattern 3 for outer flex | exact for inner grid; NEW for outer flex |
| `frontend/src/components/terminal/PositionRow.tsx` | add 800ms `bg-up/20` / `bg-down/20` trade-flash class via `selectTradeFlash` selector | itself lines 26-31 (flashDirection → flashClass) | exact (mirror existing 500ms flash logic) |
| `frontend/src/lib/price-store.ts` | add `selectedTab` slice + `setSelectedTab` action; add `tradeFlash` slice + `flashTrade` action + `selectTradeFlash` selector + 800ms `tradeFlashTimers` map | itself: `flashDirection`/`flashTimers`/`FLASH_MS`/`selectFlash` (lines 42-43, 75-79, 96-110, 177-180); `selectedTicker` (lines 24, 58, 158) | exact (clone existing pattern with new constants) |
| `frontend/src/app/providers.tsx` | unchanged structurally; new query keys `['portfolio','history']` + `['chat','history']` will be used by new components, not by Providers | itself (lines 14-24) | exact (no change to Providers; query keys are component-side) |
| `frontend/vitest.setup.ts` | add 4-line `class ResizeObserverStub { observe() {} unobserve() {} disconnect() {} }` + `vi.stubGlobal('ResizeObserver', ResizeObserverStub)` | itself (current 1-line file: `import '@testing-library/jest-dom/vitest';`) | NEW (no existing global stub) |
| `frontend/next.config.mjs` | add `skipTrailingSlashRedirect: true` (one line, between `trailingSlash: true` and `async rewrites()`) | itself | exact (single-key addition) |
| `frontend/package.json` | add `"recharts": "^3.8.0"` to `dependencies` (research correction over CONTEXT's `^2.x`) | itself: `lightweight-charts: "^5.2.0"` | exact (add as a sibling chart dep) |
| `frontend/src/app/globals.css` | add `@keyframes` for `action-pulse-up`, `action-pulse-down`, `thinking-pulse`; add `.thinking-dot` rule; add `@media (prefers-reduced-motion: reduce)` block | itself (current `@theme` + `:root` blocks); RESEARCH.md Pattern 6 | NEW (no existing keyframes in globals.css) |
| `backend/app/lifespan.py` | add `from pathlib import Path`, `from fastapi.staticfiles import StaticFiles`; append `app.mount("/", StaticFiles(...), name="frontend")` AFTER the chat router include (line 78) | itself: `app.include_router(...)` calls at lines 73-78 | exact for placement; NEW for `StaticFiles` import |

---

## Pattern Assignments

### `frontend/src/components/portfolio/Heatmap.tsx` (component, request-response)

**Analog:** `frontend/src/components/terminal/PositionsTable.tsx`

**Imports + 'use client' header pattern** (PositionsTable.tsx lines 1-12):

```typescript
'use client';

/**
 * [one-line module description]
 * Decision refs: [...]
 */

import { useQuery } from '@tanstack/react-query';
import { fetchPortfolio } from '@/lib/api/portfolio';
import { PositionRow } from './PositionRow';
```

For Heatmap, swap `PositionRow` import for `HeatmapCell`, add Recharts:

```typescript
import { Treemap, ResponsiveContainer } from 'recharts';
import { fetchPortfolio } from '@/lib/api/portfolio';
import { selectTick, usePriceStore } from '@/lib/price-store';
import { HeatmapCell } from './HeatmapCell';
import { SkeletonBlock } from '@/components/skeleton/SkeletonBlock';
```

**useQuery + isPending/isError pattern** (PositionsTable.tsx lines 14-25):

```typescript
export function PositionsTable() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['portfolio'],
    queryFn: fetchPortfolio,
    refetchInterval: 15_000,
  });

  const positions = data?.positions ?? [];
  const sorted = [...positions].sort(
    (a, b) =>
      b.quantity * b.current_price - a.quantity * a.current_price,
  );
```

For Heatmap: same `useQuery(['portfolio'])` (note: shares cache with PositionsTable + Header — invalidation by chat/trade reaches all three). Branch on `isPending` → render `<SkeletonBlock />` (D-13); branch on `positions.length === 0` → empty-state copy.

**Panel chrome pattern** (PositionsTable.tsx lines 27-31):

```typescript
<section className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col min-h-[240px]">
  <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">
    Positions
  </h2>
```

**NEW for Phase 8 (no in-repo analog):** Recharts `<Treemap>` rendering. Use RESEARCH.md Pattern 1 verbatim:

```tsx
<ResponsiveContainer width="100%" height="100%">
  <Treemap
    data={treeData}
    dataKey="weight"
    stroke="#30363d"
    content={<HeatmapCell />}
    onClick={(node) => {
      usePriceStore.getState().setSelectedTicker((node as any).ticker);
      usePriceStore.getState().setSelectedTab('chart');
    }}
    isAnimationActive
    animationDuration={300}
  />
</ResponsiveContainer>
```

**Heatmap data builder** (RESEARCH.md §Code Examples — buildHeatmapData):

Mirrors PositionRow.tsx lines 18-24's client-side P&L pattern (price/pnl from `tick` if present, else from backend `current_price`/`avg_cost`).

---

### `frontend/src/components/portfolio/HeatmapCell.tsx` (component, render-only)

**Analog:** `frontend/src/components/terminal/PositionRow.tsx`

**Render-by-prop pattern** (PositionRow.tsx lines 14-32):

```typescript
export function PositionRow({ position }: { position: PositionOut }) {
  const tick = usePriceStore(selectTick(position.ticker));
  const flash = usePriceStore(selectFlash(position.ticker));

  const price = tick?.price ?? position.current_price;
  const pnl = tick
    ? (tick.price - position.avg_cost) * position.quantity
    : position.unrealized_pnl;
  const pct = tick
    ? ((tick.price - position.avg_cost) / position.avg_cost) * 100
    : position.change_percent;

  const flashClass =
    flash === 'up'
      ? 'bg-up/10'
      : flash === 'down'
        ? 'bg-down/10'
        : '';
  const pnlColor = pnl >= 0 ? 'text-up' : 'text-down';
```

**NEW for Phase 8:** Recharts passes datum + geometry merged into `TreemapNode` props. The cell does NOT call `usePriceStore` itself — the parent `<Heatmap>` builds enriched `treeData` via `buildHeatmapData()` (which subscribes to the store) and passes it through Recharts. HeatmapCell is a pure render-by-prop SVG `<g>` with `<rect>` + `<text>`. Use RESEARCH.md Pattern 1 (HeatmapCell threshold-hide + binary fill).

---

### `frontend/src/components/portfolio/PnLChart.tsx` (component, request-response)

**Analog:** `frontend/src/components/terminal/MainChart.tsx`

**Conditional render: empty state vs chart** (MainChart.tsx lines 77-99):

```typescript
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
      ...
```

For PnLChart: branch on `isPending` → `<SkeletonBlock />`; branch on `snapshots.length < 2` → empty state copy ("Snapshots accumulate as you trade — make a trade to begin.").

**Color-flip pattern** (MainChart.tsx lines 70-75):

```typescript
useEffect(() => {
  const s = seriesRef.current;
  if (!s || !tick) return;
  const positive = tick.price >= tick.session_start_price;
  s.applyOptions({ color: positive ? '#26a69a' : '#ef5350' });
}, [tick]);
```

For PnLChart (D-06): compute `lastTotal = snapshots[snapshots.length-1]?.total_value ?? 10000`, set `stroke = lastTotal >= 10000 ? 'var(--color-up)' : 'var(--color-down)'`, render once into `<Line stroke={stroke} ...>` (no `applyOptions` — Recharts re-renders declaratively; `isAnimationActive={false}` per RESEARCH.md Pattern 2).

**NEW for Phase 8:** Recharts `<LineChart>` + `<ReferenceLine y={10000}>` + custom `<Tooltip content={<PnLTooltip />}>`. Use RESEARCH.md Pattern 2 verbatim.

**Critical:** the parent `<section>` MUST have explicit min-height (Phase 7 MainChart already uses `min-h-[400px]`); Recharts `<ResponsiveContainer width="100%" height="100%">` requires a sized parent or it collapses to 0.

---

### `frontend/src/components/chat/ChatDrawer.tsx` (component, layout)

**Analog:** `frontend/src/components/terminal/Watchlist.tsx` (panel chrome) + RESEARCH.md Pattern 3 (NEW push-layout pattern).

**Panel chrome pattern** (Watchlist.tsx lines 24-28):

```typescript
<aside className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col">
  <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">
    Watchlist
  </h2>
  <div className="overflow-y-auto">
```

**NEW for Phase 8:** width-transition collapse + push-layout sibling to the existing 3-col grid. Use RESEARCH.md Pattern 3:

```tsx
<aside
  className={`
    bg-surface-alt border-l border-border-muted flex flex-col
    transition-[width] duration-300 ease-out
    ${isOpen ? 'w-[380px]' : 'w-12'}
  `}
  aria-label="AI assistant"
>
  <ChatHeader isOpen={isOpen} onToggle={() => setOpen(!isOpen)} />
  {isOpen && (
    <>
      <ChatThread />
      <ChatInput />
    </>
  )}
</aside>
```

Local `useState<boolean>(true)` for `isOpen` (default-open per D-07). Conditionally mount thread+input on `isOpen` so the `useQuery(['chat','history'])` only fires when visible (RESEARCH.md Pattern 3 rationale).

---

### `frontend/src/components/chat/ChatThread.tsx` (component, request-response + mutation)

**Analog:** `frontend/src/components/terminal/PositionsTable.tsx` (useQuery loading branches) + `frontend/src/components/terminal/TradeBar.tsx` (useMutation + invalidation).

**useMutation + onSuccess invalidate pattern** (TradeBar.tsx lines 37-51):

```typescript
const mutation = useMutation({
  mutationFn: postTrade,
  onSuccess: async () => {
    await qc.invalidateQueries({ queryKey: ['portfolio'] });
    setTicker('');
    setQuantity('');
    setErrorCode(null);
    setPendingSide(null);
    tickerRef.current?.focus();
  },
  onError: (err: unknown) => {
    setErrorCode(err instanceof TradeError ? err.code : 'unknown');
    setPendingSide(null);
  },
});
```

For ChatThread: same shape, but `mutationFn: postChat`. On `onSuccess`:
1. Append assistant message to local `fresh` state.
2. For each `executed` trade in `response.trades`, call `usePriceStore.getState().flashTrade(trade.ticker, 'up')`.
3. Call `qc.invalidateQueries({ queryKey: ['portfolio'] })` — propagates new cash/positions to Header + PositionsTable + Heatmap (all share `['portfolio']`).
4. Optionally invalidate `['watchlist']` if any `watchlist_changes` resolved.

**useQuery loading/error branches** (PositionsTable.tsx lines 56-86) — same `isPending` / `isError` / empty state pattern; render skeleton/empty/messages-list.

**NEW for Phase 8:** local `pending` + `fresh` state arrays merged with `historyQuery.data?.messages`. See RESEARCH.md Pattern 4 verbatim. `useLayoutEffect` for auto-scroll to bottom (RESEARCH.md Pattern 4 + Pitfall 5 — skip auto-scroll geometry assertion in tests).

---

### `frontend/src/components/chat/ChatInput.tsx` (component, event-driven)

**Analog:** `frontend/src/components/terminal/TradeBar.tsx`

**Form + disabled-during-pending + ref-focus** (TradeBar.tsx lines 71-128):

```tsx
<form className="flex flex-col gap-3">
  <label className="flex flex-col gap-1 text-sm text-foreground-muted">
    Ticker
    <input
      ref={tickerRef}
      type="text"
      ...
      onChange={(e) => {
        setTicker(e.target.value.trim().toUpperCase());
        setErrorCode(null);
      }}
      className="h-10 px-3 bg-surface border border-border-muted rounded text-foreground font-mono focus-visible:outline-2 focus-visible:outline-accent-blue"
    />
  </label>
  ...
  <button
    type="button"
    onClick={submit('buy')}
    disabled={isSubmitting}
    className="flex-1 h-10 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
  >
    Buy
  </button>
```

For ChatInput:
- Single `<textarea>` instead of two text/number inputs (multi-line composing).
- Single `Send` button (`bg-accent-purple` matches Phase 7 trade-bar — same primary CTA semantic per UI-SPEC §4.2).
- `disabled={mutation.isPending}` exactly like TradeBar's `disabled={isSubmitting}`.
- `focus-visible:outline-accent-blue` ring identical.
- `onKeyDown`: Enter → submit; Shift+Enter → newline (default textarea behavior). Cmd/Ctrl+Enter also submits per UI-SPEC §5.8.
- On success: clear textarea, refocus (TradeBar lines 41-46 pattern).

---

### `frontend/src/components/chat/ChatMessage.tsx` (component, render-only)

**Analog:** `frontend/src/components/terminal/PositionRow.tsx`

**Conditional class application by enum** (PositionRow.tsx lines 26-32):

```typescript
const flashClass =
  flash === 'up'
    ? 'bg-up/10'
    : flash === 'down'
      ? 'bg-down/10'
      : '';
const pnlColor = pnl >= 0 ? 'text-up' : 'text-down';
```

For ChatMessage: branch on `role === 'user'` vs `role === 'assistant'` for bubble alignment (left/right) and bg color (`bg-surface-alt` for assistant, `bg-accent-purple/20` for user). Render `<ActionCardList>` inside assistant bubbles when `actions != null`.

---

### `frontend/src/components/chat/ActionCard.tsx` (component, render-only)

**Analog:** `frontend/src/components/terminal/ConnectionDot.tsx`

**Status-driven className lookup table** (ConnectionDot.tsx lines 12-16):

```typescript
const CLASSES: Record<ConnectionStatus, string> = {
  connected: 'bg-up',
  reconnecting: 'bg-accent-yellow',
  disconnected: 'bg-down',
};
```

For ActionCard: use the verbatim STATUS_STYLE map from RESEARCH.md §Code Examples (it already defines `borderClass`, `textClass`, `label` for all 6 statuses). Mirror ConnectionDot's exact pattern of "lookup → apply className":

```typescript
const STATUS_STYLE: Record<Status, { borderClass: string; textClass: string; label: string }> = {
  executed:    { borderClass: 'border-l-up border-l-4 border-up/30', textClass: 'text-up', label: 'executed' },
  added:       { ... },
  // ... see RESEARCH.md §Code Examples
};

const ERROR_COPY: Record<string, string> = {
  insufficient_cash:   'Not enough cash for that order.',
  // ... reuses Phase 7 D-07 strings verbatim from TradeBar.tsx lines 16-22
};
```

**Phase 7 error-string carry-forward:** TradeBar.tsx lines 16-22 ERROR_TEXT object + DEFAULT_ERROR is the canonical map. ActionCard MUST reuse those exact strings for the 4 overlapping codes (`insufficient_cash`, `insufficient_shares`, `unknown_ticker`, `price_unavailable`) and add the Phase 5 codes (`invalid_ticker`, `internal_error`).

**NEW for Phase 8:** action-pulse keyframe class (`action-pulse-up`/`action-pulse-down`) applied for ~800ms on first render of an `executed` trade card. Local `useEffect` with `setTimeout(800)` + state to remove the class. Pattern mirrors `flashTimers` in price-store but is component-local (each card mounts once).

---

### `frontend/src/components/chat/ActionCardList.tsx` (component, render-only)

**Analog:** `frontend/src/components/terminal/PositionsTable.tsx`

**Sort + map pattern** (PositionsTable.tsx lines 21-25, 84-86):

```typescript
const positions = data?.positions ?? [];
const sorted = [...positions].sort(
  (a, b) =>
    b.quantity * b.current_price - a.quantity * a.current_price,
);
// ...
sorted.map((p) => <PositionRow key={p.ticker} position={p} />)
```

For ActionCardList: render `watchlist_changes` first, then `trades` (Phase 5 D-09 ordering — reflected in CONTEXT.md D-10):

```typescript
const all = [
  ...(actions.watchlist_changes ?? []).map((a) => ({ kind: 'watchlist' as const, action: a })),
  ...(actions.trades ?? []).map((a) => ({ kind: 'trade' as const, action: a })),
];
return all.map((item, i) => <ActionCard key={i} {...item} />);
```

---

### `frontend/src/components/chat/ChatHeader.tsx` (drawer header)

**Analog:** `frontend/src/components/terminal/Header.tsx`

**Header strip layout** (Header.tsx lines 38-54):

```tsx
<header className="h-16 bg-surface-alt border border-border-muted rounded px-4 flex items-center gap-6">
  <ConnectionDot />
  <div className="flex items-baseline gap-2">
    <span className="text-sm text-foreground-muted">Total</span>
    <span className="font-mono tabular-nums text-lg">
      {formatMoney(totalValue)}
    </span>
  </div>
  ...
```

For ChatHeader: replace Total/Cash with title "Assistant" + toggle button on the right. Toggle uses the unicode guillemet (`›` open / `‹` close) per UI-SPEC §5.5 (NOT emoji — just sans-serif glyphs). Same `bg-surface-alt border-border-muted` panel chrome + same `font-semibold` heading.

---

### `frontend/src/components/chat/ThinkingBubble.tsx` (component, render-only)

**Analog:** none in repo (NEW pure-CSS animation). Use RESEARCH.md Pattern 6.

**Implementation** (RESEARCH.md Pattern 6 verbatim):

```tsx
export function ThinkingBubble() {
  return (
    <div className="bg-surface-alt rounded p-3 inline-flex gap-1" aria-label="Assistant is thinking">
      <span className="thinking-dot" />
      <span className="thinking-dot" />
      <span className="thinking-dot" />
    </div>
  );
}
```

`.thinking-dot` keyframes live in `globals.css` (see globals.css modifications below).

---

### `frontend/src/components/skeleton/SkeletonBlock.tsx` (or `common/SkeletonBlock`)

**Analog:** none in repo. Use RESEARCH.md Pattern 7.

**Implementation:**

```tsx
export function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div className={`bg-border-muted/50 rounded animate-pulse ${className ?? ''}`} />
  );
}
```

`animate-pulse` is a Tailwind v4 built-in. **No new keyframes needed for the skeleton itself** (only for action-pulse + thinking-dot).

---

### `frontend/src/components/terminal/TabBar.tsx` (component, event-driven)

**Analog:** `frontend/src/components/terminal/PositionRow.tsx` (button-row pattern) + `frontend/src/components/terminal/ConnectionDot.tsx` (state lookup).

**Button-row click pattern** (PositionRow.tsx lines 35-49):

```typescript
<tr
  onClick={() =>
    usePriceStore.getState().setSelectedTicker(position.ticker)
  }
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      usePriceStore.getState().setSelectedTicker(position.ticker);
    }
  }}
  tabIndex={0}
  role="button"
  ...
  className={`... focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent-blue ${flashClass}`}
>
```

For TabBar: 3 buttons (`Chart` / `Heatmap` / `P&L`), each `onClick` dispatches `setSelectedTab`, with `aria-current="page"` on the active tab. Read `selectedTab` via new selector. Active tab gets `border-b-2 border-accent-blue` styling.

---

### `frontend/src/lib/api/chat.ts` (api-client, REST)

**Analog:** `frontend/src/lib/api/portfolio.ts`

**Module header + types** (portfolio.ts lines 1-37):

```typescript
/**
 * Wire-boundary REST client for the portfolio + trading API.
 * Phase 03 contract (03-CONTEXT.md D-10): failures return 400 with
 * detail = { error, message }. The key is `detail.error`, NOT `detail.code`.
 */

export interface TradeBody { ... }
export interface PositionOut { ... }
export interface PortfolioResponse { ... }
```

**Error class + fetch + ok-check + error-detail pattern** (portfolio.ts lines 40-70):

```typescript
export class TradeError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.name = 'TradeError';
    this.code = code;
  }
}

export async function fetchPortfolio(): Promise<PortfolioResponse> {
  const res = await fetch('/api/portfolio');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as PortfolioResponse;
}

export async function postTrade(body: TradeBody): Promise<TradeResponse> {
  const res = await fetch('/api/portfolio/trade', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = (await res.json().catch(() => ({}))) as {
      detail?: { error?: string; message?: string };
    };
    throw new TradeError(j?.detail?.error ?? 'unknown', j?.detail?.message ?? '');
  }
  return (await res.json()) as TradeResponse;
}
```

For chat.ts: same exact shape. Two functions:
- `getChatHistory(): Promise<HistoryResponse>` mirrors `fetchPortfolio` (GET, ok-check, parse).
- `postChat(body: { message: string }): Promise<ChatResponse>` mirrors `postTrade` (POST + JSON + 502 error path → use `Error` not a custom class — chat errors aren't user-validation errors but transport errors).

Verified types from `backend/app/chat/models.py` (lines 59-104): `TradeActionResult`, `WatchlistActionResult`, `ChatResponse`, `ChatMessageOut`, `HistoryResponse` — copy these into chat.ts as TypeScript interfaces. Use the verbatim struct in RESEARCH.md §Code Examples (`lib/api/chat.ts (NEW)` block).

**Important quirk:** the chat error contract is NOT `detail.error`/`detail.message` like trade — it's `detail.error="chat_turn_error"` for 502s (see `backend/app/chat/routes.py` line 49). Chat errors are transport-level, not user-validation. Throw a plain `Error` with the message string, not a custom class.

### Extend `frontend/src/lib/api/portfolio.ts` — add `getPortfolioHistory`

**Analog:** `fetchPortfolio` (same file lines 49-54).

**Add at end of portfolio.ts:**

```typescript
export interface SnapshotOut {
  recorded_at: string;
  total_value: number;
}

export interface HistoryResponse {
  snapshots: SnapshotOut[];
}

export async function getPortfolioHistory(): Promise<HistoryResponse> {
  const res = await fetch('/api/portfolio/history');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as HistoryResponse;
}
```

**Verified:** `backend/app/portfolio/models.py` lines 56-66 confirms the response key is `snapshots: list[SnapshotOut]` and each SnapshotOut has `total_value: float`, `recorded_at: str`. RESEARCH.md A1 assumption is now resolved — no key rename needed.

---

### `frontend/src/lib/price-store.ts` — extend with selectedTab + tradeFlash

**Analog:** itself — clone the `flashDirection` machinery (lines 42-43, 64, 75-79, 96-110, 140-142, 152-154, 177-180).

**Existing flashDirection pattern** (price-store.ts lines 42-43):

```typescript
const flashTimers = new Map<string, ReturnType<typeof setTimeout>>();
const FLASH_MS = 500;
```

**Existing flashDirection mutation in ingest** (price-store.ts lines 75-79):

```typescript
// D-01 flash direction
if (prior && raw.price !== prior.price) {
  nextFlash[ticker] = raw.price > prior.price ? 'up' : 'down';
  newFlashes.push(ticker);
}
```

**Existing flashTimers cleanup pattern** (price-store.ts lines 96-110):

```typescript
for (const ticker of newFlashes) {
  const prevTimer = flashTimers.get(ticker);
  if (prevTimer) clearTimeout(prevTimer);
  const handle = setTimeout(() => {
    set((s) => {
      const cleared = { ...s.flashDirection };
      delete cleared[ticker];
      return { flashDirection: cleared };
    });
    flashTimers.delete(ticker);
  }, FLASH_MS);
  flashTimers.set(ticker, handle);
}
```

**NEW for Phase 8 — clone the same shape with TRADE_FLASH_MS = 800:**

```typescript
const tradeFlashTimers = new Map<string, ReturnType<typeof setTimeout>>();
const TRADE_FLASH_MS = 800;

// in PriceStoreState interface:
selectedTab: 'chart' | 'heatmap' | 'pnl';
tradeFlash: Record<string, 'up' | 'down'>;
setSelectedTab: (t: 'chart' | 'heatmap' | 'pnl') => void;
flashTrade: (ticker: string, dir: 'up' | 'down') => void;

// in store body:
selectedTab: 'chart',
tradeFlash: {},
setSelectedTab: (t) => set({ selectedTab: t }),
flashTrade: (ticker, dir) => {
  set((s) => ({ tradeFlash: { ...s.tradeFlash, [ticker]: dir } }));
  const prev = tradeFlashTimers.get(ticker);
  if (prev) clearTimeout(prev);
  const handle = setTimeout(() => {
    set((s) => {
      const cleared = { ...s.tradeFlash };
      delete cleared[ticker];
      return { tradeFlash: cleared };
    });
    tradeFlashTimers.delete(ticker);
  }, TRADE_FLASH_MS);
  tradeFlashTimers.set(ticker, handle);
},
```

**Existing reset/disconnect cleanup** (price-store.ts lines 140-156) — extend to include `tradeFlashTimers.forEach(clearTimeout); tradeFlashTimers.clear();` and zero `tradeFlash: {}` + `selectedTab: 'chart'`.

**Existing selector pattern** (price-store.ts lines 177-183):

```typescript
export const selectFlash =
  (ticker: string) =>
  (s: PriceStoreState): 'up' | 'down' | undefined =>
    s.flashDirection[ticker];

export const selectSelectedTicker = (s: PriceStoreState): string | null => s.selectedTicker;
```

**Add new selectors:**

```typescript
export const selectTradeFlash =
  (ticker: string) =>
  (s: PriceStoreState): 'up' | 'down' | undefined =>
    s.tradeFlash[ticker];

export const selectSelectedTab = (s: PriceStoreState): 'chart' | 'heatmap' | 'pnl' => s.selectedTab;
```

**Critical:** do NOT modify the existing `flashDirection` slice. The Phase 7 price-flash test (`price-store.test.ts` lines 65-79) must stay green. CONTEXT.md D-12 + RESEARCH.md Pattern 5 explicitly require a separate slice.

---

### `frontend/src/components/terminal/PositionRow.tsx` — add tradeFlash

**Existing flashClass logic** (PositionRow.tsx lines 14-31):

```typescript
const tick = usePriceStore(selectTick(position.ticker));
const flash = usePriceStore(selectFlash(position.ticker));
// ...
const flashClass =
  flash === 'up'
    ? 'bg-up/10'
    : flash === 'down'
      ? 'bg-down/10'
      : '';
```

**Phase 8 extension — add tradeFlashClass alongside the existing flashClass:**

```typescript
import { selectFlash, selectTick, selectTradeFlash, usePriceStore } from '@/lib/price-store';

// inside component:
const flash = usePriceStore(selectFlash(position.ticker));
const tradeFlash = usePriceStore(selectTradeFlash(position.ticker));

const flashClass = flash === 'up' ? 'bg-up/10' : flash === 'down' ? 'bg-down/10' : '';
const tradeFlashClass = tradeFlash === 'up' ? 'bg-up/20' : tradeFlash === 'down' ? 'bg-down/20' : '';
```

Both classes apply simultaneously — Tailwind merges; the higher-alpha (/20) wins visually if both fire at once. Apply both to the `<tr className=...>` (line 48).

---

### `frontend/src/components/terminal/Terminal.tsx` — wrap for drawer + insert TabBar

**Existing 3-col grid** (Terminal.tsx lines 15-33):

```tsx
export function Terminal() {
  return (
    <main className="min-h-screen min-w-[1024px] bg-surface text-foreground p-6">
      <div className="grid grid-cols-[320px_1fr_360px] gap-6">
        <div className="flex flex-col gap-4">
          <Watchlist />
        </div>
        <div className="flex flex-col gap-4 min-w-0">
          <Header />
          <MainChart />
        </div>
        <div className="flex flex-col gap-4">
          <PositionsTable />
          <TradeBar />
        </div>
      </div>
    </main>
  );
}
```

**Phase 8 wrap — flex row outer, drawer sibling, TabBar+tabbed surface in center** (RESEARCH.md Pattern 3 + UI-SPEC §5.1):

```tsx
import { ChatDrawer } from '@/components/chat/ChatDrawer';
import { TabBar } from './TabBar';
import { Heatmap } from '@/components/portfolio/Heatmap';
import { PnLChart } from '@/components/portfolio/PnLChart';
import { selectSelectedTab, usePriceStore } from '@/lib/price-store';

export function Terminal() {
  const selectedTab = usePriceStore(selectSelectedTab);
  return (
    <main className="flex flex-row min-h-screen min-w-[1024px] bg-surface text-foreground">
      <div className="flex-1 min-w-0 p-6">
        <div className="grid grid-cols-[320px_1fr_360px] gap-6">
          <div className="flex flex-col gap-4">
            <Watchlist />
          </div>
          <div className="flex flex-col gap-4 min-w-0">
            <Header />
            <TabBar />
            {selectedTab === 'chart' && <MainChart />}
            {selectedTab === 'heatmap' && <Heatmap />}
            {selectedTab === 'pnl' && <PnLChart />}
          </div>
          <div className="flex flex-col gap-4">
            <PositionsTable />
            <TradeBar />
          </div>
        </div>
      </div>
      <ChatDrawer />
    </main>
  );
}
```

---

## Test Patterns

### `Heatmap.test.tsx`

**Analog:** `PositionsTable.test.tsx`

**Test harness setup** (PositionsTable.test.tsx lines 1-35):

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';
import { PositionsTable } from './PositionsTable';
import { usePriceStore } from '@/lib/price-store';
import type { RawPayload } from '@/lib/sse-types';

function payload(ticker: string, price: number, prev = price): RawPayload { ... }

function stubPortfolio(body: unknown, ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status: ok ? 200 : 500,
      json: () => Promise.resolve(body),
    }),
  );
}

describe('<PositionsTable />', () => {
  beforeEach(() => {
    usePriceStore.getState().reset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });
```

For Heatmap.test.tsx: same exact harness + same `stubPortfolio` helper. Tests assert against the `data` prop passed to `<Treemap>` (see RESEARCH.md Pitfall 2 — assert props, not SVG geometry, because jsdom collapses ResponsiveContainer to 0×0).

### `PnLChart.test.tsx`

**Analog:** `MainChart.test.tsx` — mock the chart library, assert library calls.

**Mock pattern** (MainChart.test.tsx lines 4-15):

```typescript
const mockSeries = { setData: vi.fn(), update: vi.fn(), applyOptions: vi.fn() };
const mockChart = {
  addSeries: vi.fn(() => mockSeries),
  remove: vi.fn(),
  applyOptions: vi.fn(),
};

vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => mockChart),
  LineSeries: 'LineSeries',
}));
```

For PnLChart.test.tsx: equivalent `vi.mock('recharts', ...)` ONLY IF the test needs visible SVG. RESEARCH.md Pitfall 2 prefers data-prop assertions — assert that `<Line>` received `stroke="var(--color-up)"` when latest>=10000 etc. Mock at module level if necessary; otherwise just stub `ResizeObserver` globally (already in `vitest.setup.ts` after the Phase 8 patch).

### `ChatInput.test.tsx`

**Analog:** `TradeBar.test.tsx`

**fillAndClick keyboard helper** (TradeBar.test.tsx lines 12-18):

```typescript
function fillAndClick(ticker: string, qty: string, side: 'Buy' | 'Sell') {
  const tickerInput = screen.getByPlaceholderText('AAPL') as HTMLInputElement;
  const qtyInput = screen.getByPlaceholderText('1') as HTMLInputElement;
  fireEvent.change(tickerInput, { target: { value: ticker } });
  fireEvent.change(qtyInput, { target: { value: qty } });
  fireEvent.click(screen.getByRole('button', { name: side }));
}
```

For ChatInput.test.tsx: `fireEvent.change(textarea, { target: { value: 'hello' } })` + `fireEvent.keyDown(textarea, { key: 'Enter' })` for Enter-submit; `fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })` for Shift+Enter newline (assert mutation NOT called).

**Mutation success → invalidates portfolio** (TradeBar.test.tsx lines 204-246) — duplicate this pattern for ChatInput's `flashTrade` + `invalidateQueries(['portfolio'])` on response.

### `backend/tests/test_static_mount.py`

**Analog:** `backend/tests/test_lifespan.py` lines 66-73:

```python
async def test_includes_sse_router_during_startup(self, db_path):
    """app.include_router(create_stream_router(cache)) ran in lifespan startup,
    so /api/stream/prices is registered on the app while the lifespan is active."""
    app = _build_app()
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            paths = {getattr(r, "path", None) for r in app.router.routes}
            assert "/api/stream/prices" in paths, paths
```

For Phase 8 static mount test: assert that an `app.router.routes` entry has `path="/"` and is a `Mount` (Starlette `routing.Mount` instance, type-check via `isinstance`); assert it appears AFTER all `/api/...` route entries (registration-order via list index comparison). Mirror the LifespanManager + db_path fixture pattern exactly.

---

## Shared Patterns

### Shared Pattern: TanStack Query usage

**Source:** `frontend/src/components/terminal/PositionsTable.tsx` lines 14-19, `frontend/src/components/terminal/Watchlist.tsx` lines 16-19, `frontend/src/components/terminal/Header.tsx` lines 23-27.

**Apply to:** Heatmap (`['portfolio']` — shares cache with PositionsTable + Header), PnLChart (`['portfolio','history']`), ChatThread (`['chat','history']` for fetch + `useMutation(postChat)` for posting).

```typescript
const { data, isPending, isError } = useQuery({
  queryKey: ['portfolio'],
  queryFn: fetchPortfolio,
  refetchInterval: 15_000,  // PositionsTable + Header use this; PnLChart + ChatThread do NOT (they invalidate explicitly on mutation)
});
```

**Invalidation pattern** (TradeBar.tsx lines 39-46) — Phase 8 ChatThread mutation reuses verbatim:

```typescript
const qc = useQueryClient();
// ... onSuccess:
await qc.invalidateQueries({ queryKey: ['portfolio'] });
```

---

### Shared Pattern: Zustand subscription with narrow selector

**Source:** `frontend/src/components/terminal/PositionRow.tsx` lines 15-16, `frontend/src/components/terminal/WatchlistRow.tsx` lines 25-27.

**Apply to:** All Phase 8 components that read store state.

```typescript
import { selectFlash, selectTick, usePriceStore } from '@/lib/price-store';

const tick = usePriceStore(selectTick(position.ticker));
const flash = usePriceStore(selectFlash(position.ticker));
```

**Critical (anti-pattern guard):** never re-open EventSource; never read whole-store; always one selector per slice (RESEARCH.md Anti-Patterns).

---

### Shared Pattern: Panel chrome

**Source:** `frontend/src/components/terminal/Watchlist.tsx` lines 25-28, `frontend/src/components/terminal/PositionsTable.tsx` lines 28-31, `frontend/src/components/terminal/MainChart.tsx` lines 87-89.

**Apply to:** Heatmap, PnLChart panel wrappers.

```tsx
<section className="flex-1 bg-surface border border-border-muted rounded overflow-hidden flex flex-col min-h-[NNNpx]">
  <h2 className="text-xl font-semibold px-4 py-3 border-b border-border-muted">
    {Title}
  </h2>
  <div className="overflow-y-auto"> {/* or "flex-1" for charts */}
    {body}
  </div>
</section>
```

---

### Shared Pattern: Color tokens (Phase 7 inheritance)

**Source:** `frontend/src/app/globals.css` lines 19-21 + lines 44-46.

**Apply to:** All Phase 8 surfaces — Heatmap fill, PnLChart stroke, ActionCard borders, position-row trade-flash.

```css
--color-up:   #26a69a;
--color-down: #ef5350;
```

Tailwind v4 derives `bg-up`, `bg-down`, `text-up`, `text-down`, `border-up`, `border-down`, `border-l-up`, `border-l-down`, `bg-up/10`, `bg-up/20`, `bg-up/30` directly from the CSS-var tokens. **No new tokens added in Phase 8.** Heatmap fill must use the literal CSS variable in SVG `fill={...}` attributes (`fill="var(--color-up)"`) because SVG attributes don't compile through Tailwind class names.

---

### Shared Pattern: Error string map (Phase 7 carry-forward)

**Source:** `frontend/src/components/terminal/TradeBar.tsx` lines 16-22.

**Apply to:** `frontend/src/components/chat/ActionCard.tsx` (D-11 `failed` cards).

```typescript
const ERROR_TEXT: Record<string, string> = {
  insufficient_cash: 'Not enough cash for that order.',
  insufficient_shares: "You don't have that many shares to sell.",
  unknown_ticker: 'No such ticker.',
  price_unavailable: 'Price unavailable right now — try again.',
};
const DEFAULT_ERROR = 'Something went wrong. Try again.';
```

**Phase 8 ADDS:** `invalid_ticker: "That ticker symbol isn't valid."` and `internal_error: 'Something went wrong on our side. Try again.'` (Phase 5 D-12 codes — RESEARCH.md §Code Examples ERROR_COPY).

---

### Shared Pattern: Test stubs (vitest + RTL)

**Source:** `frontend/src/components/terminal/PositionsTable.test.tsx` lines 17-35, `frontend/src/components/terminal/TradeBar.test.tsx` lines 7-10.

**Apply to:** All Phase 8 component tests.

```typescript
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithQuery } from '@/test-utils';

beforeEach(() => {
  usePriceStore.getState().reset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubFetch(impl: (url: string, init?: RequestInit) => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(impl));
  return fetch as unknown as ReturnType<typeof vi.fn>;
}
```

**Phase 8 ADDS to `vitest.setup.ts`** (RESEARCH.md Pattern 9):

```typescript
// vitest.setup.ts
import '@testing-library/jest-dom/vitest';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);
```

This unblocks Recharts `<ResponsiveContainer>` in jsdom for all Phase 8 tests (RESEARCH.md Pitfall 2).

---

### Shared Pattern: Backend lifespan router/mount registration

**Source:** `backend/app/lifespan.py` lines 73-78:

```python
app.include_router(create_stream_router(cache))
app.include_router(create_portfolio_router(conn, cache))
app.include_router(create_watchlist_router(conn, cache, source))
chat_client = create_chat_client()
app.state.chat_client = chat_client
app.include_router(create_chat_router(conn, cache, source, chat_client))
```

**Apply to:** APP-02 — append `app.mount(...)` AFTER line 78 (the chat router include — currently the LAST registration). Use RESEARCH.md Pattern 8 + §Code Examples backend/app/lifespan.py patch:

```python
# at the top (alongside existing imports):
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# inside lifespan, AFTER the chat router include (line 78):
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"
app.mount(
    "/",
    StaticFiles(directory=str(static_dir), html=True),
    name="frontend",
)
```

**Critical (anti-pattern guard):** mount MUST come AFTER all `app.include_router(...)` calls — registration-order matters (RESEARCH.md Pitfall 4). The new mount goes between line 78 and the `logger.info(...)` at line 80.

---

### Shared Pattern: Globals.css keyframes (NEW)

**Source:** `frontend/src/app/globals.css` (current file is 47 lines — `@theme` + `:root`). No existing keyframes.

**Apply to:** Action-card pulse (ActionCard.tsx) + thinking dots (ThinkingBubble.tsx). Use RESEARCH.md Pattern 6 verbatim:

```css
@keyframes action-pulse-up {
  0%   { background-color: rgb(38 166 154 / 0.30); }
  100% { background-color: rgb(38 166 154 / 0.00); }
}
@keyframes action-pulse-down {
  0%   { background-color: rgb(239 83 80 / 0.30); }
  100% { background-color: rgb(239 83 80 / 0.00); }
}
.action-pulse-up   { animation: action-pulse-up   800ms ease-out 1; }
.action-pulse-down { animation: action-pulse-down 800ms ease-out 1; }

.thinking-dot {
  width: 6px; height: 6px; border-radius: 9999px;
  background-color: var(--color-foreground-muted);
  animation: thinking-pulse 1200ms infinite ease-in-out;
}
.thinking-dot:nth-child(2) { animation-delay: 200ms; }
.thinking-dot:nth-child(3) { animation-delay: 400ms; }

@keyframes thinking-pulse {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30%           { opacity: 1.0; transform: translateY(-2px); }
}

@media (prefers-reduced-motion: reduce) {
  .action-pulse-up,
  .action-pulse-down,
  .thinking-dot,
  .animate-pulse,
  .transition-colors,
  .transition-\[width\] {
    animation: none !important;
    transition: none !important;
  }
}
```

---

## No Analog Found

Files with no close match in the codebase — planner uses RESEARCH.md patterns as the primary reference:

| File | Role | Data Flow | Reason | RESEARCH.md Reference |
|------|------|-----------|--------|-----------------------|
| `frontend/src/components/chat/ThinkingBubble.tsx` | render-only | none | First pure-CSS @keyframes animation in the project | RESEARCH.md Pattern 6 |
| `frontend/src/components/skeleton/SkeletonBlock.tsx` | render-only | none | First skeleton primitive in the project | RESEARCH.md Pattern 7 |
| `frontend/src/components/portfolio/PnLTooltip.tsx` (suggested split) | render-only | none | First Recharts custom tooltip in the project | RESEARCH.md Pattern 2 |

All three are < 30 LOC primitives with verbatim implementations in RESEARCH.md.

---

## Recharts in jsdom — special note for the planner

Recharts integration is the only NEW library in Phase 8. Two pitfalls and their mitigations:

1. **`ResponsiveContainer` collapses to 0×0 in jsdom** — RESEARCH.md Pitfall 2. Mitigation: stub `ResizeObserver` globally in `vitest.setup.ts` (4-line class). Tests assert against the data prop, not pixel geometry. If a specific test needs visible SVG, add `vi.mock('recharts', () => ({ ...original, ResponsiveContainer: <fixed-size-wrapper> }))` in JUST that test file.
2. **`TooltipProps` → `TooltipContentProps`** — Recharts 3.x rename. RESEARCH.md Pitfall 6. Use `TooltipContentProps<number, string>` for the typed PnLTooltip.

These are the only Phase 8 surfaces that need NEW patterns; everything else mirrors Phase 7 prior art.

---

## Metadata

**Analog search scope:** `frontend/src/components/terminal/`, `frontend/src/lib/`, `frontend/src/app/`, `backend/app/`, `backend/tests/`.
**Files scanned:** 30 frontend `.ts/.tsx`, 6 backend `.py`, 5 config files (next.config, package.json, vitest.setup, vitest.config, globals.css).
**Strong analogs found:** 36 of 39 (3 files have no in-repo analog and use RESEARCH.md patterns directly).
**Pattern extraction date:** 2026-04-25
