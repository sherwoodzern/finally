---
phase: 07-market-data-trading-ui
verified: 2026-04-24T23:45:00Z
status: human_needed
human_acceptance: indefinite
human_acceptance_recorded: 2026-04-28
human_acceptance_rationale: |
  All 6 human_verification items are visual-feel checks (CSS price-flash cadence,
  Lightweight Charts sparkline canvas, click-to-select cross-panel flow, instant-fill
  UX, EventSource reconnect state-machine dot, three-column Bloomberg-style aesthetic).
  The runtime behavior underlying every item is exercised by the canonical Phase 10
  harness (7 specs x 3 browsers x 2 consecutive runs = 21 passed x 2, 0 failed, 0 flaky,
  Container test-appsvc-1 Healthy). The "feel" is the only deferred item. Recorded
  here as accepted policy debt for v1.0 milestone closure (Phase 11 G3).
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: 0/0
  gaps_closed: []
  gaps_remaining: []
  regressions: []
requirements:
  - FE-03
  - FE-04
  - FE-07
  - FE-08
  - FE-10
created: 2026-04-24
human_verification:
  - test: "Open http://localhost:8000 with backend running; observe the watchlist tickers"
    expected: "On every tick, the price cell briefly flashes green (uptick) or red (downtick) and fades out within ~500ms; the actual visual feel of the flash animation must look smooth and Bloomberg-like"
    why_human: "CSS transition feel and browser repaint cadence cannot be verified by Vitest mocks of lightweight-charts"
  - test: "Watch the sparklines beside watchlist tickers fill in over ~30 seconds of streaming"
    expected: "Each sparkline draws progressively from left to right as new ticks arrive; line color flips between teal #26a69a and coral #ef5350 as the daily-% sign changes"
    why_human: "Canvas rendering of Lightweight Charts cannot run in jsdom; only browser produces the actual line"
  - test: "Click a watchlist row, observe the main chart area"
    expected: "The main chart panel mounts a larger Lightweight Charts canvas labelled 'Chart: <TICKER>' and renders the currently buffered points; subsequent ticks extend the line"
    why_human: "Click-to-select cross-panel flow requires real DOM event dispatch and canvas rendering"
  - test: "Open DevTools network tab, place a Buy order via the trade bar, observe the header and positions table"
    expected: "POST /api/portfolio/trade fires with body {ticker, side, quantity}; on 200 the inputs clear, focus returns to ticker input, header Total/Cash recompute, and positions table shows the new row within milliseconds"
    why_human: "End-to-end UX of instant-fill + invalidation timing is felt, not asserted"
  - test: "Disconnect the backend (stop uvicorn) and observe the header connection dot"
    expected: "Dot transitions from green (#26a69a) → yellow (#ecad0a) while EventSource attempts reconnect → red (#ef5350) when CLOSED; tooltip text matches Live / Reconnecting… / Disconnected"
    why_human: "EventSource reconnect state machine in a real browser cannot be reproduced in Vitest without an integration harness"
  - test: "Open the page on a desktop ≥1024px wide and inspect the three-column layout"
    expected: "Watchlist on the left (320px), Header + MainChart in the centre (flex), PositionsTable + TradeBar on the right (360px); panels have the dark Bloomberg-style aesthetic with the project palette"
    why_human: "Visual aesthetic / 'Bloomberg-style' look-and-feel is subjective and only verifiable in a browser"
---

# Phase 7: Market Data & Trading UI Verification Report

**Phase Goal:** The user sees a working trading terminal — live-flashing watchlist with sparklines, a main ticker chart, a positions table, a trade bar, and a header with live totals and a connection-status dot.

**Verified:** 2026-04-24T23:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Watchlist renders each ticker with current price (green/red flash on tick), daily-change % computed from session-start, sparkline that fills progressively (FE-03) | VERIFIED | See SC#1 below |
| 2 | Clicking a watchlist row selects ticker and renders Lightweight Charts canvas in main chart area (FE-04) | VERIFIED | See SC#2 below |
| 3 | Positions table renders ticker, qty, avg cost, current price, unrealized P&L, % per `/api/portfolio` position; updates as prices tick (FE-07) | VERIFIED | See SC#3 below |
| 4 | Trade bar fills market orders instantly (no confirmation dialog) — Buy/Sell calls POST `/api/portfolio/trade` and reflects result in cash, positions, header (FE-08) | VERIFIED | See SC#4 below |
| 5 | Header continuously displays total portfolio value + cash + connection-status dot (green/yellow/red) (FE-10) | VERIFIED | See SC#5 below |

**Score:** 5/5 truths verified by automated checks. Human verification required for visual / browser-only behaviors.

---

## SC#1 — Watchlist with flash + sparkline + daily-% (FE-03)

**Status:** PASS

| Check | Evidence |
|-------|----------|
| Panel `Watchlist` renders rows from `GET /api/watchlist` with backend-authoritative order | `frontend/src/components/terminal/Watchlist.tsx:16-19` (`useQuery({ queryKey: ['watchlist'], queryFn: fetchWatchlist })`); `Watchlist.tsx:21` maps `data.items[].ticker` |
| Row subscribes to narrow per-ticker selectors (no full-`prices` re-render) | `frontend/src/components/terminal/WatchlistRow.tsx:25-27` (`selectTick(ticker)`, `selectFlash(ticker)`, `selectSparkline(ticker)`) |
| Price flash class toggle on tick (D-01) | `WatchlistRow.tsx:29-34` applies `bg-up/10` / `bg-down/10`; `WatchlistRow.tsx:53` includes `transition-colors duration-500` |
| 500ms flash auto-clear via module-level timer Map | `frontend/src/lib/price-store.ts:42-43` (`flashTimers`, `FLASH_MS = 500`); `price-store.ts:97-109` schedules per-ticker clear |
| Daily-% computed from session-start price | `WatchlistRow.tsx:36-38` formula `((price - session_start_price) / session_start_price) * 100`; verified by test `daily-% = (price - session_start) / session_start * 100` |
| Price formatted `$190.23` (2 dp) and signed % `+0.42%` | `WatchlistRow.tsx:59,62`; verified by test `renders signed daily-% and $price after tick` (line `+0.00%` and `$200.00`) |
| Sparkline buffer trims to 120 entries | `price-store.ts:44` (`SPARKLINE_WINDOW = 120`); `price-store.ts:82-86` trim logic; verified by test `sparklineBuffers trims to the last 120 entries` (asserts buf[0]=105, buf[119]=224 after 125 ticks) |
| Sparkline uses Lightweight Charts v5 `addSeries(LineSeries, ...)` (NOT v4 `addLineSeries`) | `frontend/src/components/terminal/Sparkline.tsx:11-13` imports `createChart, LineSeries`; `Sparkline.tsx:45` calls `chart.addSeries(LineSeries, {...})`; verified by `grep "addLineSeries" src/components/terminal/*.tsx` returns 0 hits |
| Sparkline 80×32 with all chrome disabled | `Sparkline.tsx:77` (`className="h-8 w-20"`); chrome flags at `Sparkline.tsx:34-43` |
| Sparkline cleans up via `chart.remove()` on unmount | `Sparkline.tsx:53-57`; verified by test `calls chart.remove on unmount` |
| Stroke flips between `#26a69a` and `#ef5350` based on sign | `Sparkline.tsx:46,62`; verified by tests `calls createChart and addSeries(LineSeries, ...) on mount` (color #26a69a) and `uses the down color when positive=false` (color #ef5350) |

**Vitest evidence:** 7 price-store flash/sparkline tests + 5 Sparkline tests + 6 WatchlistRow tests all passing.

---

## SC#2 — Main chart on click-select (FE-04)

**Status:** PASS

| Check | Evidence |
|-------|----------|
| MainChart subscribes to `selectedTicker` from store | `frontend/src/components/terminal/MainChart.tsx:21` (`usePriceStore(selectSelectedTicker)`) |
| Empty state when no ticker selected, copy verbatim | `MainChart.tsx:77-85` renders `Select a ticker from the watchlist to view its chart.`; verified by test `renders empty-state copy when no ticker is selected` |
| Chart created on selection via v5 API | `MainChart.tsx:33-50` (`createChart` + `chart.addSeries(LineSeries, { color: '#26a69a', lineWidth: 2 })`); verified by test `creates chart + addSeries(LineSeries, ...) when a ticker is selected` (asserts firstArg='LineSeries', lineWidth: 2) |
| h2 renders `Chart: {selectedTicker}` | `MainChart.tsx:90`; verified by test `renders h2 "Chart: AAPL" when AAPL selected` |
| `setData` called when buffer changes | `MainChart.tsx:59-68` driven by `[selectedTicker, buffer]`; verified by test `calls series.setData when buffer has data for selected ticker` (asserts values [190, 195]) |
| Color flip on sign change vs session-start | `MainChart.tsx:70-75` `applyOptions({ color: positive ? '#26a69a' : '#ef5350' })` |
| Click-select wired Watchlist→MainChart | Watchlist row `onSelect` calls `setSelectedTicker` (`Watchlist.tsx:46-50` → `WatchlistRow.tsx:43`); store action defined at `price-store.ts:158`; PositionRow also dispatches (`PositionRow.tsx:36-38`) |
| Cleanup on unmount and ticker change | `MainChart.tsx:52-56`; verified by test `calls chart.remove on unmount` |
| Main chart uses larger `lineWidth: 2` (vs sparkline 1) | `MainChart.tsx:48`; sparkline uses `lineWidth: 1` at `Sparkline.tsx:47` |

**Vitest evidence:** 5 MainChart tests passing.

---

## SC#3 — Positions table live (FE-07)

**Status:** PASS

| Check | Evidence |
|-------|----------|
| `useQuery(['portfolio'])` with 15s refetchInterval | `frontend/src/components/terminal/PositionsTable.tsx:15-19` |
| Six columns: Ticker, Qty, Avg Cost, Price, P&L, % | `PositionsTable.tsx:36-53` (column headers); `PositionRow.tsx:50-69` (cells) |
| Client-side P&L from store tick when present | `PositionRow.tsx:18-24` (`tick ? (tick.price - avg_cost) * quantity : position.unrealized_pnl`) |
| Cold-start fallback to backend `unrealized_pnl` and `change_percent` | `PositionRow.tsx:21,24` fallback branches; verified by test `cold-start fallback uses backend unrealized_pnl when store has no tick` (asserts `+$5.00`, `$190.50`) |
| Default sort by weight descending | `PositionsTable.tsx:22-25`; verified by test `sorts rows by weight descending (qty * current_price)` (asserts `['GOOGL', 'MSFT', 'AAPL']` order) |
| Loading / error / empty state copy verbatim | `PositionsTable.tsx:62, 71, 80` (`Loading positions…`, `Couldn't load positions. Retrying in 15s.`, `No positions yet — use the trade bar to buy shares.`); verified by 3 tests |
| Live tick updates row | Verified by test `renders one row per position with client-side P&L from store tick` (store tick at 195 wins over backend 190 → renders `+$50.00`, `+2.63%`, `$195.00`) |
| Click-row dispatches setSelectedTicker | `PositionRow.tsx:36-38` |
| Numeric cells use `font-mono tabular-nums text-right text-sm` | `PositionRow.tsx:51-69` |

**Vitest evidence:** 6 PositionsTable tests passing.

---

## SC#4 — Trade bar instant fill (FE-08)

**Status:** PASS

| Check | Evidence |
|-------|----------|
| Ticker regex `/^[A-Z][A-Z0-9.]{0,9}$/` matches backend `_TICKER_RE` | `frontend/src/components/terminal/TradeBar.tsx:14`; backend source at `backend/app/watchlist/models.py` (per plan reference) |
| Ticker upper-cased on change | `TradeBar.tsx:84` (`e.target.value.trim().toUpperCase()`) |
| Quantity input `<input type="number" min="0.01" step="0.01">` | `TradeBar.tsx:93-95` |
| Both Buy and Sell buttons use `bg-accent-purple text-white` | `TradeBar.tsx:110, 118` |
| POST body shape `{ticker, side, quantity}` to `/api/portfolio/trade` | `TradeBar.tsx:64` `mutation.mutate({ticker, side, quantity: q})` → `postTrade` at `frontend/src/lib/api/portfolio.ts:57-69` (POST + JSON content type); verified by test `POSTs {ticker, side, quantity} to /api/portfolio/trade on Buy` |
| Side toggling Buy vs Sell | `TradeBar.tsx:53-66` (`submit('buy')` / `submit('sell')`); verified by test `POSTs with side=sell on Sell click` |
| Error code map (D-07): all 4 mapped + default fallback | `TradeBar.tsx:16-22`; all 5 strings verified by 5 individual tests (`maps insufficient_cash → ...`, `insufficient_shares`, `unknown_ticker`, `price_unavailable`, `falls back to default copy on unmapped code`) |
| Error rendered via `<p role="alert">` with `text-down` | `TradeBar.tsx:124-126` |
| Reads `body.detail.error` (NOT `detail.code`) | `frontend/src/lib/api/portfolio.ts:64-67` (`j?.detail?.error ?? 'unknown'`); verified by test `throws TradeError with code from detail.error on 400` |
| Regex reject does NOT fetch | `TradeBar.tsx:56-58` (early return); verified by test `rejects ticker not matching regex BEFORE fetching` (`expect(fetchMock).not.toHaveBeenCalled()`) |
| onSuccess: clear inputs, refocus, invalidate `['portfolio']` | `TradeBar.tsx:39-46` (invalidateQueries + setTicker('') + setQuantity('') + tickerRef.current?.focus()); verified by tests `on success: clears inputs and returns focus to ticker` and `on success: invalidates ["portfolio"] (triggers re-fetch)` |
| `TradeError` malformed-body fallback to code='unknown' | `portfolio.ts:64,67`; verified by test `throws TradeError with code="unknown" when body is malformed` |

**Vitest evidence:** 11 TradeBar tests + 6 portfolio.ts tests passing.

---

## SC#5 — Header with live totals + connection-status dot (FE-10)

**Status:** PASS

| Check | Evidence |
|-------|----------|
| Header uses `useQuery(['portfolio'])` (cache shared with PositionsTable) | `frontend/src/components/terminal/Header.tsx:23-27` |
| Total formula = cash + Σ(qty × store_price ?? avg_cost) | `Header.tsx:31-36`; verified by test `total = cash + Σ(qty * store_price) and updates on tick` (cash 8000 + 10×200 = $10,000.00; tick to 210 → $10,100.00) |
| Cold-start fallback uses avg_cost when no tick | `Header.tsx:34` (`prices[p.ticker]?.price ?? p.avg_cost`); verified by test `cold-start fallback: uses avg_cost when no tick in store` |
| Money format `$X,XXX.XX` via toLocaleString en-US | `Header.tsx:15-20` |
| Labels `Total` and `Cash` verbatim | `Header.tsx:42, 48`; verified by test `renders Total and Cash labels` |
| ConnectionDot 10×10 (`w-2.5 h-2.5 rounded-full`) | `frontend/src/components/terminal/ConnectionDot.tsx:28` |
| Dot color map: connected→`bg-up`, reconnecting→`bg-accent-yellow`, disconnected→`bg-down` | `ConnectionDot.tsx:12-16`; verified by 3 tests in Header.test.tsx (`bg-up when connected`, `bg-accent-yellow when reconnecting`, `bg-down when disconnected`) |
| Title/aria-label per status | `ConnectionDot.tsx:18-22, 29-30` (`Live` / `Reconnecting…` / `Disconnected`; `aria-label="SSE ${status}"`) |
| Subscribes to `selectConnectionStatus` | `ConnectionDot.tsx:25` |

**Vitest evidence:** 6 Header tests passing.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/price-store.ts` | flashDirection + sparklineBuffers + selectedTicker slices + selectors | VERIFIED | All slices declared (price-store.ts:17-19), selectors at lines 171-183, FLASH_MS=500 / SPARKLINE_WINDOW=120 at lines 43-44 |
| `frontend/src/lib/api/portfolio.ts` | TradeError + fetchPortfolio + postTrade reading body.detail.error | VERIFIED | TradeError at line 40-47, fetchPortfolio at 50-54, postTrade at 57-70 reads `j?.detail?.error` at line 67 |
| `frontend/src/lib/api/watchlist.ts` | fetchWatchlist | VERIFIED | Lines 21-25 |
| `frontend/src/test-utils.tsx` | renderWithQuery helper | VERIFIED | Lines 11-18; fresh QueryClient with retry: false per call |
| `frontend/src/components/terminal/Watchlist.tsx` | Panel using useQuery(['watchlist']) | VERIFIED | 58 lines |
| `frontend/src/components/terminal/WatchlistRow.tsx` | Per-ticker selector subscriber + flash + daily-% + sparkline | VERIFIED | 69 lines |
| `frontend/src/components/terminal/Sparkline.tsx` | LWC v5 wrapper | VERIFIED | 78 lines, no v4 API |
| `frontend/src/components/terminal/MainChart.tsx` | Empty-state + LWC v5 main chart | VERIFIED | 100 lines |
| `frontend/src/components/terminal/PositionsTable.tsx` | useQuery(['portfolio']) + sort + 3-way state | VERIFIED | 92 lines |
| `frontend/src/components/terminal/PositionRow.tsx` | Client P&L + cold-start fallback + click-select | VERIFIED | 72 lines |
| `frontend/src/components/terminal/TradeBar.tsx` | Form + ticker regex + D-07 error map + invalidate-on-success | VERIFIED | 131 lines |
| `frontend/src/components/terminal/Header.tsx` | Total + Cash + ConnectionDot using shared cache | VERIFIED | 55 lines |
| `frontend/src/components/terminal/ConnectionDot.tsx` | 10×10 status-driven dot | VERIFIED | 33 lines |
| `frontend/src/components/terminal/Terminal.tsx` | 3-column grid composition | VERIFIED | 33 lines, classes match UI-SPEC §5.1 |
| `frontend/src/app/page.tsx` | Renders `<Terminal />` (no Phase 06 placeholder) | VERIFIED | 5 lines, imports + renders Terminal; no `'use client'`, no FinAlly placeholder copy |
| `frontend/src/app/globals.css` | D-02 palette `#26a69a` / `#ef5350` (no `#3fb950` / `#f85149`) | VERIFIED | Line 19-20 (@theme), 44-45 (:root); old placeholders absent (grep returns 0) |
| `frontend/src/app/providers.tsx` | QueryClientProvider + PriceStreamProvider | VERIFIED | Lines 13-31, named export, 'use client', useState singleton QueryClient |
| `frontend/src/app/layout.tsx` | Wraps children in `<Providers>` | VERIFIED | Line 14 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Watchlist.tsx | fetchWatchlist | `useQuery(['watchlist'], fetchWatchlist)` | WIRED | Watchlist.tsx:16-19 |
| WatchlistRow.tsx | usePriceStore | selectTick/selectFlash/selectSparkline | WIRED | WatchlistRow.tsx:25-27 |
| Sparkline.tsx | lightweight-charts | `addSeries(LineSeries, ...)` | WIRED (v5 API only) | Sparkline.tsx:11-13, 45 |
| MainChart.tsx | usePriceStore | selectSelectedTicker + inline sparkline/tick selectors | WIRED | MainChart.tsx:21-27 |
| MainChart.tsx | lightweight-charts | `addSeries(LineSeries, ...)` | WIRED (v5 API only) | MainChart.tsx:11-13, 46 |
| PositionsTable.tsx | fetchPortfolio | `useQuery(['portfolio'], fetchPortfolio, { refetchInterval: 15000 })` | WIRED | PositionsTable.tsx:15-19 |
| PositionRow click | setSelectedTicker | `usePriceStore.getState().setSelectedTicker(position.ticker)` | WIRED | PositionRow.tsx:36-38, 41-43 |
| TradeBar submit | POST /api/portfolio/trade | `useMutation({ mutationFn: postTrade })` | WIRED | TradeBar.tsx:37-51 |
| TradeBar onSuccess | invalidateQueries(['portfolio']) | `qc.invalidateQueries({ queryKey: ['portfolio'] })` | WIRED | TradeBar.tsx:40 |
| Header | shared ['portfolio'] cache | `useQuery(['portfolio'])` | WIRED | Header.tsx:23-27 (matches PositionsTable queryKey) |
| ConnectionDot | usePriceStore | `selectConnectionStatus` | WIRED | ConnectionDot.tsx:25 |
| Terminal | all 5 panels | composition: Watchlist, Header, MainChart, PositionsTable, TradeBar | WIRED | Terminal.tsx:9-30 |
| app/page.tsx | Terminal | `import { Terminal } from '@/components/terminal/Terminal'` + `<Terminal />` | WIRED | page.tsx:1-5 |
| app/layout.tsx | providers.tsx | `import { Providers } from './providers'` + `<Providers>{children}</Providers>` | WIRED | layout.tsx:3, 14 |
| providers.tsx | @tanstack/react-query | `QueryClientProvider` + `new QueryClient(...)` | WIRED | providers.tsx:9-30 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Watchlist | `data.items[].ticker` | `fetchWatchlist()` → `GET /api/watchlist` (Phase 4 wired backend) | Yes — Phase 4 backend returns real `items[]` (verified Phase 4 PASS) | FLOWING |
| WatchlistRow flash/price | `tick`, `flash`, `buffer` | `usePriceStore.ingest()` populated by SSE in `price-store.ts:115-126` (`es.onmessage`) | Yes — backend SSE stream wired Phase 1, store ingest covered by 8 price-stream tests | FLOWING |
| MainChart series | `buffer` | `usePriceStore` `sparklineBuffers[selectedTicker]` populated on each tick | Yes — appended in `price-store.ts:82-86` per ingest | FLOWING |
| PositionsTable | `data.positions[]` | `fetchPortfolio()` → `GET /api/portfolio` (Phase 3 wired backend) | Yes — Phase 3 backend returns real positions (verified Phase 3 PASS) | FLOWING |
| PositionRow live P&L | `tick.price` | `usePriceStore` `selectTick(ticker)` | Yes — same ingest path as Watchlist | FLOWING |
| TradeBar | mutation result | `postTrade()` → `POST /api/portfolio/trade` (Phase 3 wired backend) | Yes — Phase 3 wired the trade endpoint | FLOWING |
| Header total | `data.cash_balance`, `data.positions`, `prices` | shared `['portfolio']` cache + `usePriceStore.prices` dict | Yes — both sources flowing | FLOWING |
| ConnectionDot | `status` | `usePriceStore.status` set in EventSource event handlers (`price-store.ts:116, 121, 130-131`) | Yes — driven by real EventSource state in product, by setState() in tests | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Vitest suite passes | `cd frontend && npm run test:ci` | `Test Files 9 passed (9)`; `Tests 60 passed (60)`; Duration ~890ms | PASS |
| Production build succeeds | `cd frontend && npm run build` | Compiled successfully in 718ms; static export produced; routes `/`, `/_not-found`, `/debug` prerendered | PASS |
| D-02 palette in compiled CSS | `grep -l "#26a69a" out/_next/static/chunks/*.css` | 1 file matches; same for `#ef5350` | PASS |
| Old placeholders removed | `grep -l "#3fb950\|#f85149" out/_next/static/chunks/*.css` | 0 files match | PASS |
| Brand palette retained | `grep -l "#ecad0a\|#209dd7\|#753991\|#0d1117"` | All 4 files match (1 each) | PASS |
| LWC v4 API absent | `grep "addLineSeries" frontend/src/components/terminal/*.tsx` | exit 1 (no matches) | PASS |
| LWC v5 API present | `grep -c "addSeries(LineSeries" frontend/src/components/terminal/{Sparkline,MainChart}.tsx` | Sparkline.tsx:1, MainChart.tsx:1 | PASS |
| Phase 7 deps installed at correct versions | `node -e 'p=require("./package.json"); console.log(p.dependencies["lightweight-charts"], p.dependencies["@tanstack/react-query"])'` | `^5.2.0 ^5.100.1` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FE-03 | 07-01-PLAN, 07-03-PLAN | Watchlist with flash + daily-% + progressive sparkline | SATISFIED | SC#1 above; 7 price-store tests + 5 Sparkline + 6 WatchlistRow tests |
| FE-04 | 07-04-PLAN | Main chart canvas + click-select | SATISFIED | SC#2 above; 5 MainChart tests |
| FE-07 | 07-05-PLAN | Positions table with live P&L | SATISFIED | SC#3 above; 6 PositionsTable tests |
| FE-08 | 07-06-PLAN | Trade bar with instant fill + D-07 error mapping | SATISFIED | SC#4 above; 11 TradeBar tests + 6 portfolio API tests |
| FE-10 | 07-07-PLAN | Header with totals + connection dot | SATISFIED | SC#5 above; 6 Header tests |

No orphaned requirements. All 5 declared requirements are covered by at least one plan and have implementing artifacts.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

`grep -rn -E "TODO\|FIXME\|XXX\|HACK\|PLACEHOLDER"` across all Phase 7 modified files (`src/components/terminal/`, `src/lib/api/`, `src/test-utils.tsx`) returns zero results. `grep -rn "dangerouslySetInnerHTML"` across `src/` returns zero results. No emojis observed in any modified file.

### Human Verification Required

The automated suite (60/60 Vitest tests + green production build + verified palette + verified v5 API usage) is comprehensive at the unit/component level, but several phase 7 truths reduce to browser-only behaviors that no Vitest mock of `lightweight-charts` can prove. Six items require human verification — see frontmatter `human_verification` for the full list, summarized:

1. Price-flash visual feel (does it actually look smooth and fade in ~500ms?)
2. Sparkline progressive draw on a real canvas (jsdom can't render lightweight-charts)
3. Click-watchlist → main chart cross-panel rendering
4. End-to-end trade flow (network → invalidation → header & positions update)
5. EventSource reconnect state machine driving the connection dot color in a real browser
6. Bloomberg-style aesthetic / three-column desktop layout look-and-feel

These are gating items 7 and 8 of the v0 verifier override list ("Visual appearance" and "Real-time behavior") — they MUST be confirmed before declaring the phase user-visible-complete, but they are not gaps in the implementation.

### Gaps Summary

No implementation gaps. All five ROADMAP Success Criteria pass automated checks with concrete file:line evidence. Status is `human_needed` rather than `passed` solely because the phase produces visible UI whose final acceptance requires opening a browser against a running backend — the same condition Phase 6's verification flagged.

If the developer prefers `passed` without the browser checks, they can be deferred to Phase 10 (E2E Validation) where Playwright will exercise these flows against the live container; the items below in `human_verification` would then be the de facto Phase 10 acceptance criteria for this phase's surfaces.

---

_Verified: 2026-04-24T23:45:00Z_
_Verifier: Claude (gsd-verifier)_
