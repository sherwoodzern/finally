---
plan: 07-03
phase: 07-market-data-trading-ui
status: complete
completed: 2026-04-24
---

# Plan 07-03 — Watchlist panel + Sparkline (FE-03)

## Objective
Deliver the live-flashing watchlist with progressive sparklines: panel that seeds rows from `GET /api/watchlist`, row that subscribes to per-ticker selectors with flash + daily-% + price + sparkline cells, and an 80×32 Lightweight Charts v5 sparkline wrapper.

## Outcome
- `frontend/src/components/terminal/Sparkline.tsx` (80 lines) — `'use client'`, `createChart` + `chart.addSeries(LineSeries, {...})` v5 API; chrome fully stripped (no axes/grid/crosshair/scales/handlers); transparent background; stroke `#26a69a` (positive) / `#ef5350` (negative) reapplied via `applyOptions` on prop flip; `chart.remove()` on unmount.
- `frontend/src/components/terminal/WatchlistRow.tsx` (62 lines) — three narrow selectors (`selectTick(ticker)`, `selectFlash(ticker)`, `selectSparkline(ticker)`); flash class `bg-up/10` / `bg-down/10` with `transition-colors duration-500`; daily-% formula `(price - session_start_price) / session_start_price * 100`, signed two-decimal; em-dash empty cell; click + keyboard (Enter/Space) dispatches `onSelect(ticker)`.
- `frontend/src/components/terminal/Watchlist.tsx` (55 lines) — `useQuery({ queryKey: ['watchlist'], queryFn: fetchWatchlist })`; backend-authoritative row order; row click dispatches `setSelectedTicker`; loading and error inline states.
- `frontend/src/components/terminal/Sparkline.test.tsx` — 5 tests (mounts createChart + addSeries(LineSeries, ...), down color, setData with buffer, no setData when undefined, remove on unmount).
- `frontend/src/components/terminal/WatchlistRow.test.tsx` — 6 tests (em-dash empty, formatted price/%, bg-up/10 flash, bg-down/10 flash, click dispatch, daily-% formula).

`lightweight-charts` mocked in both test files so jsdom does not need real canvas.

## Verification
- `npm run test:ci` → **32 passed (32)** across 5 files.
- `npm run build` → exit 0; static export generated.
- Lightweight Charts v5 API used; no `addLineSeries` anywhere.

## Files
- Created: `frontend/src/components/terminal/Sparkline.tsx`
- Created: `frontend/src/components/terminal/WatchlistRow.tsx`
- Created: `frontend/src/components/terminal/Watchlist.tsx`
- Created: `frontend/src/components/terminal/Sparkline.test.tsx`
- Created: `frontend/src/components/terminal/WatchlistRow.test.tsx`

## Notes
- StrictMode ref-gate `if (!containerRef.current || chartRef.current) return;` mirrors Phase 06 D-15 idempotent-connect pattern.
- The Sparkline `layout.background.type: 'solid'` value is cast through `as never` — Lightweight Charts v5's exported `BackgroundStyle` enum is not exposed on the public API surface and `'solid'` is the documented literal.
- `Watchlist.tsx` `Loading watchlist…` uses U+2026 ellipsis to mirror UI-SPEC §8 `Loading positions…`.
