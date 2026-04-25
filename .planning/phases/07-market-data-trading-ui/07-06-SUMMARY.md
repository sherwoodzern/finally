---
plan: 07-06
phase: 07-market-data-trading-ui
status: complete
completed: 2026-04-24
---

# Plan 07-06 — Trade Bar (FE-08)

## Objective
Render the market-order trade bar: ticker (regex-gated upper-case input), quantity (HTML number), Buy + Sell (both purple), inline `<p role="alert">` error, and TanStack Query `useMutation` that invalidates `['portfolio']` on success.

## Outcome
- `frontend/src/components/terminal/TradeBar.tsx` (102 lines) — `'use client'`. Ticker regex literal `/^[A-Z][A-Z0-9.]{0,9}$/` (verbatim from `backend/app/watchlist/models.py:10` `_TICKER_RE`). Quantity `<input type="number" min="0.01" step="0.01">`. Both buttons styled `bg-accent-purple text-white`. `useMutation({ mutationFn: postTrade, onSuccess, onError })`: on success invalidates `['portfolio']`, clears both inputs, focuses ticker; on error sets `errorCode = err.code` (or `'unknown'` for non-TradeError). Error map keys → UI-SPEC §8 strings; default fallback `Something went wrong. Try again.`. Error rendered inside `<p role="alert" className="text-sm text-down">`.
- `frontend/src/components/terminal/TradeBar.test.tsx` — 11 tests: renders four interactives; rejects bad ticker regex BEFORE fetching with `No such ticker.`; POSTs `{ticker, side: 'buy', quantity}` to `/api/portfolio/trade`; POSTs with `side: 'sell'` on Sell click; maps each of the four backend error codes to its UI-SPEC §8 copy; falls back to `Something went wrong. Try again.` on unmapped code; on success clears both inputs + returns focus to ticker; on success triggers `['portfolio']` re-fetch (verified by counting `/api/portfolio` calls before and after the trade).

## Verification
- `npm run test:ci -- TradeBar` → 11/11 pass.
- `npm run test:ci` → **54 passed (54)** across 8 files.
- `npm run build` → exit 0.

## Files
- Created: `frontend/src/components/terminal/TradeBar.tsx`
- Created: `frontend/src/components/terminal/TradeBar.test.tsx`

## Key Decisions
- **Buttons are `type="button"` + `onClick`** (not `type="submit"` + form `onSubmit`). Clicking either button dispatches the specific `side`. Pressing Enter inside an input does NOT auto-submit — defensive against accidental Buy when the user meant Sell.
- **`pendingSide` state in addition to `mutation.isPending`** — covers the brief synchronous window between click and React Query state update where rapid double-click could fire a second mutation. Cheap, correct.
- **The backend-supplied `message` is NOT rendered.** Only the hard-coded copy table maps `code` → text. This is the T-07-03 (XSS) mitigation and the user-experience consistency point.

## Notes
- Wave 3 complete with all four parallel plans (07-03 Watchlist, 07-04 MainChart, 07-05 PositionsTable, 07-06 TradeBar) green. 11 + 6 + 5 + 11 = 33 new tests for FE-03/04/07/08; total 54 across the project.
