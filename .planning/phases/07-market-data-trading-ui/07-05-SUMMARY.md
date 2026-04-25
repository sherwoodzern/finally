---
plan: 07-05
phase: 07-market-data-trading-ui
status: complete
completed: 2026-04-24
---

# Plan 07-05 — Positions Table (FE-07)

## Objective
Render the positions table panel: one row per position from `GET /api/portfolio` with live client-side P&L driven by the store tick, cold-start fallback to backend `unrealized_pnl`, default sort by weight descending, and click-to-select-chart wiring.

## Outcome
- `frontend/src/components/terminal/PositionRow.tsx` (60 lines) — six columns (Ticker, Qty, Avg Cost, Price, P&L, %); P&L = `(tick.price - avg_cost) * quantity` with backend `unrealized_pnl` as cold-start fallback; flash class `bg-up/10` / `bg-down/10` on store flash; click + Enter/Space dispatch `usePriceStore.getState().setSelectedTicker(ticker)`; all numeric cells `font-mono tabular-nums text-right`.
- `frontend/src/components/terminal/PositionsTable.tsx` (88 lines) — `useQuery({ queryKey: ['portfolio'], queryFn: fetchPortfolio, refetchInterval: 15_000 })`; 4-state body (loading, error, empty, rows); column headers `Ticker / Qty / Avg Cost / Price / P&L / %` (P&L via JSX entity); empty/loading/error copy verbatim from UI-SPEC §8; default sort `b.qty*b.price - a.qty*a.price`.
- `frontend/src/components/terminal/PositionsTable.test.tsx` — 6 tests: loading state, empty state, error state, client-side P&L from store tick (`+$50.00` and `+2.63%`), cold-start fallback to backend (`+$5.00`, `$190.50`), and weight-descending sort (`GOOGL → MSFT → AAPL`).

## Verification
- `npm run test:ci -- PositionsTable` → 6/6 pass.
- `npm run test:ci` → **43 passed (43)** across 7 files.
- `npm run build` → exit 0.

## Files
- Created: `frontend/src/components/terminal/PositionRow.tsx`
- Created: `frontend/src/components/terminal/PositionsTable.tsx`
- Created: `frontend/src/components/terminal/PositionsTable.test.tsx`

## Notes
- `['portfolio']` queryKey is the cache shared with the Header (Plan 07-07) — both subscribe to the same data; TradeBar (Plan 07-06) invalidates this key on success.
- TanStack Query `refetchInterval: 15_000` complements the store's tick stream — store gives second-by-second price; portfolio refetch gives quantity/cash updates and reconciles with backend on every tick window.
- PositionRow does NOT take a `setSelectedTicker` prop (unlike WatchlistRow's `onSelect`); it pulls the action straight from the store via `getState()`. This keeps the props surface minimal and preserves Plan 07-03 readability without adding indirection.
