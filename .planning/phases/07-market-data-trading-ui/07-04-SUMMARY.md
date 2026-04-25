---
plan: 07-04
phase: 07-market-data-trading-ui
status: complete
completed: 2026-04-24
---

# Plan 07-04 — Main Chart panel (FE-04)

## Objective
Render a larger Lightweight Charts v5 line chart for the currently selected ticker. Empty-state when none selected. Wire through `selectSelectedTicker` so the click → chart loop is closed when this ships alongside the Watchlist (Plan 07-03).

## Outcome
- `frontend/src/components/terminal/MainChart.tsx` (94 lines) — `'use client'`, three useEffects: mount-on-select (createChart + `addSeries(LineSeries, {color: '#26a69a', lineWidth: 2})`), feed-on-buffer (setData with UTCTimestamp-mapped array), and color-on-tick (applyOptions to `#26a69a` / `#ef5350` based on `tick.price >= tick.session_start_price`). Empty state renders `Select a ticker from the watchlist to view its chart.` (UI-SPEC §8 verbatim). Header h2 renders `Chart: {selectedTicker}` plus current price in monospace.
- `frontend/src/components/terminal/MainChart.test.tsx` — 5 tests: empty-state copy + no createChart call, chart created + `addSeries(LineSeries, {color, lineWidth: 2})` on select, h2 text `Chart: AAPL`, `setData` called with buffer data on select, `chart.remove` called on unmount.

## Verification
- `npm run test:ci -- MainChart` → 5/5 pass.
- `npm run test:ci` → **37 passed (37)** across 6 files.
- `npm run build` → exit 0.
- Lightweight Charts v5 API only; no `addLineSeries`.

## Files
- Created: `frontend/src/components/terminal/MainChart.tsx`
- Created: `frontend/src/components/terminal/MainChart.test.tsx`

## Notes
- Click → chart loop covered in test by mutating store via `act(() => usePriceStore.getState().setSelectedTicker('AAPL'))` before render. End-to-end render path (Watchlist row click → store → MainChart) lives in 07-07's Terminal integration tests.
- Chart chrome colors are hex literals (`#0d1117`, `#e6edf3`, `#30363d`) because Lightweight Charts does not accept CSS variable references. Source-of-truth is `globals.css`; manual sync is the trade-off. If those tokens change, this file changes too.
