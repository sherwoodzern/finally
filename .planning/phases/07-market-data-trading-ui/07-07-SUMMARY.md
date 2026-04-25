---
plan: 07-07
phase: 07-market-data-trading-ui
status: complete
completed: 2026-04-24
---

# Plan 07-07 — Header + ConnectionDot + Terminal layout (FE-10) + phase gate

## Objective
Complete FE-10 with the header strip, connection-status dot, and the three-column terminal layout that composes all five panels. Replace the Phase 06 placeholder body of `app/page.tsx` so `/` renders the trading terminal end-to-end. Run the phase-level `npm run build` gate.

## Outcome
- `frontend/src/components/terminal/ConnectionDot.tsx` (32 lines) — `'use client'`, 10×10 (`w-2.5 h-2.5 rounded-full`); class map `connected → bg-up`, `reconnecting → bg-accent-yellow`, `disconnected → bg-down`; titles `Live` / `Reconnecting…` / `Disconnected`; `aria-label` `SSE {status}`.
- `frontend/src/components/terminal/Header.tsx` (53 lines) — `'use client'`, `useQuery({ queryKey: ['portfolio'], queryFn: fetchPortfolio, refetchInterval: 15_000 })` shared cache with PositionsTable; subscribes to `s.prices` for live recompute; total = `cash + Σ(qty * (store_price ?? avg_cost))`; format `$ X,XXX.XX` via `toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })`; copy `Total` and `Cash` verbatim from UI-SPEC §8; ConnectionDot rendered as the leftmost child.
- `frontend/src/components/terminal/Terminal.tsx` (32 lines) — three-column grid with classes verbatim from UI-SPEC §5.1: `min-h-screen min-w-[1024px] bg-surface text-foreground p-6`, `grid grid-cols-[320px_1fr_360px] gap-6`. Left col: `<Watchlist />`; center col (`min-w-0`): `<Header />` + `<MainChart />`; right col: `<PositionsTable />` + `<TradeBar />`.
- `frontend/src/app/page.tsx` — replaced Phase 06 placeholder body with `import { Terminal } ... export default function Page() { return <Terminal />; }`. Server Component (no `'use client'`); the client boundary lives at `Terminal`.
- `frontend/src/components/terminal/Header.test.tsx` — 6 tests: Total + Cash labels, total recompute on tick (8000 cash + 10×210 = 10100), cold-start fallback to avg_cost, three connection-dot states (`bg-up` / `bg-accent-yellow` / `bg-down` with matching aria-label).

## Verification
- `npm run test:ci -- Header` → 6/6 pass.
- `npm run test:ci` → **60 passed (60)** across 9 files.
- `npm run build` → exit 0; `frontend/out/` produced; only `/`, `/_not-found`, `/debug` routes.
- Compiled CSS bundle (`out/_next/static/chunks/0b11v32pkmxcb.css`): contains `#26a69a`, `#ef5350`, `#ecad0a`, `#209dd7`, `#753991`. Does NOT contain `#3fb950` or `#f85149` (old placeholders fully evicted by 07-00 globals.css edit).

## Files
- Created: `frontend/src/components/terminal/ConnectionDot.tsx`
- Created: `frontend/src/components/terminal/Header.tsx`
- Created: `frontend/src/components/terminal/Terminal.tsx`
- Created: `frontend/src/components/terminal/Header.test.tsx`
- Modified: `frontend/src/app/page.tsx` (Phase 06 placeholder body → `<Terminal />`)
- Unchanged: `frontend/src/app/debug/page.tsx`, `frontend/src/app/layout.tsx`

## Phase 7 Success Criteria — all 5 covered by automated tests + build gate
- **SC#1 Watchlist (FE-03):** WatchlistRow.test.tsx (em-dash, daily-%, bg-up/10, bg-down/10, click) + Sparkline.test.tsx (createChart + addSeries(LineSeries, ...), color, setData, remove) — Plan 07-03.
- **SC#2 Main chart on click-select (FE-04):** MainChart.test.tsx (empty-state copy, addSeries on select, h2, setData with buffer, remove on unmount) — Plan 07-04.
- **SC#3 Positions table live (FE-07):** PositionsTable.test.tsx (loading/error/empty, client-side P&L from store tick, cold-start fallback, weight sort) — Plan 07-05.
- **SC#4 Trade bar instant fill (FE-08):** TradeBar.test.tsx (regex pre-fetch reject, POST body shape Buy/Sell, four error codes mapped, default fallback, success clears + focus + invalidates ['portfolio']) — Plan 07-06.
- **SC#5 Header live totals + dot (FE-10):** Header.test.tsx (Total/Cash labels, tick recompute, cold-start fallback, three dot states) — this plan.

Total tests: 60 (8 price-stream + 7 price-store + 6 portfolio wire + 5 Sparkline + 6 WatchlistRow + 5 MainChart + 6 PositionsTable + 11 TradeBar + 6 Header).

## Deviations
None. Every UI-SPEC § directive landed verbatim — copy strings, class strings, hex tokens, layout grid.
