---
phase: 7
slug: market-data-trading-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source of truth: §6 of `07-RESEARCH.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1.5 + @testing-library/react 16.3.2 + jsdom 29 |
| **Config file** | `frontend/vitest.config.mts` (landed in Plan 06-03) |
| **Quick run command** | `cd frontend && npm run test:ci` |
| **Full suite command** | `cd frontend && npm run test:ci && npm run build` |
| **Estimated runtime** | ~5 seconds (Phase 06 baseline ~380ms + ~15 new tests) |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run test:ci`
- **After every plan wave:** Run `cd frontend && npm run test:ci && npm run build`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

Plan-task IDs are placeholders pending Step 8 planner output. The requirement→behavior mapping below is the contract the planner MUST satisfy (one or more tasks per row).

| Requirement | Behavior | Test Type | Command | File Exists |
|-------------|----------|-----------|---------|-------------|
| FE-03 | Watchlist row renders ticker, price, daily-change % from `session_start_price` | component | `npm run test:ci -- Watchlist` | ❌ W0 |
| FE-03 | Tick up → `bg-up/10` applied; 500ms later (fake timers) class removed | component | `npm run test:ci -- Flash` | ❌ W0 |
| FE-03 | `sparklineBuffers[ticker]` appends and trims to 120 entries | unit | `npm run test:ci -- price-store` | ❌ W0 |
| FE-03 | Sparkline component calls `chart.addSeries(LineSeries, ...)` + `series.update()` (lib mocked) | component | `npm run test:ci -- Sparkline` | ❌ W0 |
| FE-04 | Clicking a `WatchlistRow` dispatches select-ticker; `MainChart` re-renders for new ticker | component | `npm run test:ci -- MainChart` | ❌ W0 |
| FE-04 | `MainChart` calls `series.setData` on ticker-change and `series.update` on subsequent ticks | component | `npm run test:ci -- MainChart` | ❌ W0 |
| FE-07 | `PositionsTable` renders one row per `/api/portfolio` position with client-side P&L = (store_price − avg_cost) × quantity | component | `npm run test:ci -- PositionsTable` | ❌ W0 |
| FE-07 | Cold-start fallback: when store has no tick for a held ticker, display `unrealized_pnl` from backend | component | `npm run test:ci -- PositionsTable` | ❌ W0 |
| FE-08 | `TradeBar` rejects ticker not matching `^[A-Z][A-Z0-9.]{0,9}$` before fetching | component | `npm run test:ci -- TradeBar` | ❌ W0 |
| FE-08 | `TradeBar` POSTs `{ticker, side, quantity}` to `/api/portfolio/trade` with correct body | component | `npm run test:ci -- TradeBar` | ❌ W0 |
| FE-08 | `TradeBar` maps each backend `detail.error` code to the D-07 error string | component | `npm run test:ci -- TradeBar` | ❌ W0 |
| FE-08 | Successful submit: inputs cleared, `/api/portfolio` invalidated (re-fetch triggered) | component | `npm run test:ci -- TradeBar` | ❌ W0 |
| FE-10 | Header renders total portfolio value = `cash_balance + Σ(qty × store_price)` | component | `npm run test:ci -- Header` | ❌ W0 |
| FE-10 | Header re-renders on store tick (cash unchanged, price changes) | component | `npm run test:ci -- Header` | ❌ W0 |
| FE-10 | Connection dot: `connected` → `bg-up`, `reconnecting` → `bg-accent-yellow`, `disconnected` → `bg-down` | component | `npm run test:ci -- Header` | ❌ W0 |
| — | Build gate: `npm run build` exits 0; `frontend/out/` produced; no type errors | integration | `cd frontend && npm run build` | ✅ |

*Status on each row: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky (set by executor, not here).*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/price-store.test.ts` — extend Phase 06 `price-stream.test.ts` or add a sibling file covering D-01 `flashDirection` and D-03 `sparklineBuffers` behavior
- [ ] `frontend/src/lib/api/portfolio.test.ts` — fetch wrappers + TradeError mapping (`detail.error` → D-07 copy)
- [ ] `frontend/src/components/terminal/*.test.tsx` — component tests for `WatchlistRow`, `Sparkline`, `MainChart`, `PositionsTable`, `TradeBar`, `Header`
- [ ] `frontend/src/test-utils.tsx` — small helper exposing a `wrap()` that provides a fresh `QueryClient` (and optional `PriceStreamProvider`) per test
- [x] Vitest config + jest-dom setup — landed in Plan 06-03 (no action)

*`lightweight-charts` must be mocked per test via `vi.mock('lightweight-charts', ...)` (see Pattern in `07-RESEARCH.md` §6).*

---

## Manual-Only Verifications

*All Phase 7 behaviors have automated verification via Vitest component tests + `npm run build` gate. No manual gates required.*

---

## Validation Sign-Off

- [ ] All planned tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all ❌ W0 references
- [ ] No watch-mode flags (`test:ci` is non-watch)
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter after plans land and cover every row above

**Approval:** pending
