---
status: partial
phase: 07-market-data-trading-ui
source: [07-VERIFICATION.md]
started: 2026-04-25
updated: 2026-04-25
---

## Current Test

[awaiting human testing]

## Tests

### 1. Watchlist price-flash on tick
expected: On every SSE tick, the price cell briefly flashes green (uptick) or red (downtick) and fades out within ~500ms; the visual feel must look smooth and Bloomberg-like.
how: Open http://localhost:8000 with backend running; observe the watchlist tickers.
why_human: CSS transition feel and browser repaint cadence cannot be verified by Vitest mocks of lightweight-charts.
result: [pending]

### 2. Watchlist sparklines fill in
expected: Each sparkline draws progressively from left to right as new ticks arrive over ~30 seconds; line color flips between teal `#26a69a` and coral `#ef5350` as the daily-% sign changes.
how: Watch the sparklines beside watchlist tickers fill in over ~30 seconds of streaming.
why_human: Canvas rendering of Lightweight Charts cannot run in jsdom; only browser produces the actual line.
result: [pending]

### 3. Click-to-select main chart
expected: The main chart panel mounts a larger Lightweight Charts canvas labelled `Chart: <TICKER>` and renders the currently buffered points; subsequent ticks extend the line.
how: Click a watchlist row, observe the main chart area.
why_human: Click-to-select cross-panel flow requires real DOM event dispatch and canvas rendering.
result: [pending]

### 4. Trade end-to-end (POST + invalidate + clear + focus)
expected: `POST /api/portfolio/trade` fires with body `{ticker, side, quantity}`; on 200 the inputs clear, focus returns to ticker input, header Total/Cash recompute, and positions table shows the new row within milliseconds.
how: Open DevTools network tab, place a Buy order via the trade bar, observe the header and positions table.
why_human: End-to-end UX of instant-fill + invalidation timing is felt, not asserted.
result: [pending]

### 5. SSE disconnect → reconnect dot color machine
expected: Dot transitions from green (`#26a69a`) → yellow (`#ecad0a`) while EventSource attempts reconnect → red (`#ef5350`) when CLOSED; tooltip text matches `Live` / `Reconnecting…` / `Disconnected`.
how: Disconnect the backend (stop uvicorn) and observe the header connection dot.
why_human: EventSource reconnect state machine in a real browser cannot be reproduced in Vitest without an integration harness.
result: [pending]

### 6. Three-column terminal aesthetic
expected: Watchlist on the left (320px), Header + MainChart in the centre (flex), PositionsTable + TradeBar on the right (360px); panels have the dark Bloomberg-style aesthetic with the project palette.
how: Open the page on a desktop ≥1024px wide and inspect the three-column layout.
why_human: Visual aesthetic / "Bloomberg-style" look-and-feel is subjective and only verifiable in a browser.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
