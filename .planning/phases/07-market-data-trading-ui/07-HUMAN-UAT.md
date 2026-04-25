---
status: complete_with_deferred
phase: 07-market-data-trading-ui
source: [07-VERIFICATION.md]
started: 2026-04-25
updated: 2026-04-25
---

## Note on URL

Tests originally read `http://localhost:8000`. FastAPI mounting the static
Next.js export at `/` is Phase 8 SC#4 — until that lands, the live UI is
served by `npm run dev` at `http://localhost:3000` (with `next.config.mjs`
rewriting `/api/*` to `:8000`). All `how:` lines below point to `:3000`.

## Current Test

[all tests resolved — see Summary]

## Tests

### 1. Watchlist price-flash on tick
expected: On every SSE tick, the price cell briefly flashes green (uptick) or red (downtick) and fades out within ~500ms; the visual feel must look smooth and Bloomberg-like.
how: Open http://localhost:3000 with backend running; observe the watchlist tickers.
why_human: CSS transition feel and browser repaint cadence cannot be verified by Vitest mocks of lightweight-charts.
result: fail — no flash visible on price changes (2026-04-25)
investigation: see Gaps section below.

### 2. Watchlist sparklines fill in
expected: Each sparkline draws progressively from left to right as new ticks arrive over ~30 seconds; line color flips between teal `#26a69a` and coral `#ef5350` as the daily-% sign changes.
how: Watch the sparklines beside watchlist tickers fill in over ~30 seconds of streaming.
why_human: Canvas rendering of Lightweight Charts cannot run in jsdom; only browser produces the actual line.
result: blocked (G1) — deferred to Phase 8 (FastAPI static mount removes the redirect chain).

### 3. Click-to-select main chart
expected: The main chart panel mounts a larger Lightweight Charts canvas labelled `Chart: <TICKER>` and renders the currently buffered points; subsequent ticks extend the line.
how: Click a watchlist row, observe the main chart area.
why_human: Click-to-select cross-panel flow requires real DOM event dispatch and canvas rendering.
result: blocked (G1) — buffer is empty without SSE; deferred to Phase 8.

### 4. Trade end-to-end (POST + invalidate + clear + focus)
expected: `POST /api/portfolio/trade` fires with body `{ticker, side, quantity}`; on 200 the inputs clear, focus returns to ticker input, header Total/Cash recompute, and positions table shows the new row within milliseconds.
how: Open DevTools network tab, place a Buy order via the trade bar, observe the header and positions table.
why_human: End-to-end UX of instant-fill + invalidation timing is felt, not asserted.
result: pass (2026-04-25) — trade POST 200, inputs cleared, focus returned, Cash/Total recomputed via /api/portfolio refetch, positions row appeared. Live-tick portion of header drift not exercised here (blocked by G1) but unrelated to trade-completion UX.

### 5. SSE disconnect → reconnect dot color machine
expected: Dot transitions from green (`#26a69a`) → yellow (`#ecad0a`) while EventSource attempts reconnect → red (`#ef5350`) when CLOSED; tooltip text matches `Live` / `Reconnecting…` / `Disconnected`.
how: Disconnect the backend (stop uvicorn) and observe the header connection dot.
why_human: EventSource reconnect state machine in a real browser cannot be reproduced in Vitest without an integration harness.
result: blocked (G1) — EventSource never opens, so the state machine has no green-state baseline; deferred to Phase 8.

### 6. Three-column terminal aesthetic
expected: Watchlist on the left (320px), Header + MainChart in the centre (flex), PositionsTable + TradeBar on the right (360px); panels have the dark Bloomberg-style aesthetic with the project palette.
how: Open the page on a desktop ≥1024px wide and inspect the three-column layout.
why_human: Visual aesthetic / "Bloomberg-style" look-and-feel is subjective and only verifiable in a browser.
result: pass (2026-04-25) — three-column layout, dark Bloomberg-style palette confirmed by user.

## Summary

total: 6
passed: 2     # UAT 4 (trade flow), UAT 6 (aesthetic)
issues: 1     # UAT 1 (price-flash); root cause = G1
pending: 0
skipped: 0
blocked: 3    # UAT 2 (sparklines), UAT 3 (main chart), UAT 5 (reconnect dot) — all on G1
deferred: 4   # UAT 1, 2, 3, 5 deferred to Phase 8 (FastAPI static mount makes SSE same-origin and removes the redirect chain)

## Gaps

### G1 — SSE is broken in the dev workflow (blocks UAT 1, 2, 3, 5)

Evidence (curl):

- `GET http://localhost:3000/api/stream/prices` returns **308 → /api/stream/prices/** because `frontend/next.config.mjs:5` sets `trailingSlash: true` (added in Phase 6 plan 06-03 so `out/debug/index.html` resolves).
- The retried `GET /api/stream/prices/` is rewritten to `http://localhost:8000/api/stream/prices/`, which FastAPI redirects with **307 → http://localhost:8000/api/stream/prices** (default `redirect_slashes=True`).
- That redirect crosses origin (3000 → 8000 absolute URL); EventSource will not follow it without CORS, so the stream never opens. The watchlist therefore sees no ticks → no flash, no sparklines, no main-chart data, no green-dot transition.
- Backend SSE itself is healthy: `curl http://localhost:8000/api/stream/prices` streams `text/event-stream` correctly.

Scope: dev only. In production (Phase 8 SC#4), FastAPI mounts the static export and EventSource is same-origin — no rewrite, no redirect chain.

Fix candidates (not applied here — Phase 7 is closed; this is `/gsd-insert-phase 7.1` material):

1. `next.config.mjs` — set `skipTrailingSlashRedirect: true` so Next.js does not 308 non-slashed requests, while keeping `trailingSlash: true` for the static export. Smallest blast radius.
2. Rewrite SSE source to match both forms or carry the trailing slash through to the backend with `redirect_slashes=False` on the FastAPI app. More surgery.
3. Have `EventSource` request `/api/stream/prices/` directly (with trailing slash) and disable FastAPI's slash-redirect. Couples the client to the dev quirk.

Recommendation: candidate (1).
