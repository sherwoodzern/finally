---
plan: 07-02
phase: 07-market-data-trading-ui
status: complete
completed: 2026-04-24
---

# Plan 07-02 — Portfolio + Watchlist API wrappers + test helper

## Objective
Create the REST-wire layer used by Wave 3: `fetchPortfolio`, `postTrade` (with `TradeError`), `fetchWatchlist`, and a `renderWithQuery` test helper. Pin the `body.detail.error` contract in code + tests.

## Outcome
- `frontend/src/lib/api/portfolio.ts` — `TradeBody`, `PositionOut`, `PortfolioResponse`, `TradeResponse`, `TradeError`, `fetchPortfolio`, `postTrade`. Named exports only. Wire-boundary `try/.catch(() => ({}))` micro-pattern in `postTrade` only.
- `frontend/src/lib/api/watchlist.ts` — `WatchlistItem`, `WatchlistResponse`, `fetchWatchlist`. Named exports.
- `frontend/src/test-utils.tsx` — `renderWithQuery(ui)` builds a fresh `QueryClient({defaultOptions:{queries:{retry:false}}})` per call (no module-level singleton).
- `frontend/src/lib/api/portfolio.test.ts` — 6 tests: fetchPortfolio happy + 500-error; postTrade body+URL assertion + 400-with-detail.error → TradeError + malformed body → code="unknown" + `instanceof TradeError` with readable `code`.

## Verification
- `npm run test:ci` → **21 passed (21)** across 3 files (8 price-stream + 7 price-store + 6 portfolio).
- `npm run build` → exit 0, static export generated.
- No regression in Phase 06 tests (`price-stream.test.ts`).

## Key Decisions
- **`detail.error` is authoritative.** CONTEXT.md D-07 used `detail.code` informally; backend evidence (`backend/app/portfolio/routes.py:47` → `detail = {"error": exc.code, "message": str(exc)}`) wins. Tests pin `detail.error`; a future rename surfaces as a test failure.
- **No `credentials: 'include'`** — same-origin (Next export served by FastAPI in Phase 8). No CORS, no cookies.
- **Fresh `QueryClient` per `renderWithQuery` call** — avoids inter-test cache leakage on assertions of 4xx behavior.

## Files
- Created: `frontend/src/lib/api/portfolio.ts`
- Created: `frontend/src/lib/api/watchlist.ts`
- Created: `frontend/src/lib/api/portfolio.test.ts`
- Created: `frontend/src/test-utils.tsx`

## Next
Wave 3 components (Watchlist, MainChart, PositionsTable, TradeBar) import from these modules.
