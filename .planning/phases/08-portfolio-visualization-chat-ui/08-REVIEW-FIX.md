---
phase: 08-portfolio-visualization-chat-ui
fixed_at: 2026-04-26T22:20:00Z
review_path: .planning/phases/08-portfolio-visualization-chat-ui/08-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 08: Code Review Fix Report

**Fixed at:** 2026-04-26T22:20:00Z
**Source review:** `.planning/phases/08-portfolio-visualization-chat-ui/08-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (4 warnings; 8 info findings deferred per scope)
- Fixed: 4
- Skipped: 0

Frontend test suite: **114/114 passing** before, during, and after each fix.
TypeScript `tsc --noEmit` reports only pre-existing errors in
`MainChart.test.tsx` / `Sparkline.test.tsx` — those files were not touched by
this phase's fixes and the same errors exist on the parent commit.

## Fixed Issues

### WR-01: TradeBar swallows non-numeric quantity with no user feedback

**Files modified:** `frontend/src/components/terminal/TradeBar.tsx`
**Commit:** `d632110`
**Applied fix:** Added an `invalid_quantity` entry to `ERROR_TEXT`
("Enter a positive quantity.") and replaced the silent `if (!(q > 0))
return;` early-exit with `if (!Number.isFinite(q) || q <= 0) {
setErrorCode('invalid_quantity'); return; }`. The existing
`<p role="alert">` surface now renders the error to the user instead
of the click handler appearing to do nothing.

### WR-02: Collapsing ChatDrawer unmounts ChatThread and drops optimistic messages

**Files modified:** `frontend/src/components/chat/ChatDrawer.tsx`,
`frontend/src/components/chat/ChatDrawer.test.tsx`
**Commit:** `72da988`
**Applied fix:** Replaced `{isOpen && children}` with a wrapper
`<div data-testid="chat-drawer-body" className={isOpen ? 'flex flex-col flex-1 min-h-0' : 'hidden'}>`
so children stay mounted across the collapse toggle. Updated the
existing collapse test to assert the body remains in the DOM and the
wrapper has the `hidden` class. ChatThread's `appended` array,
`freshAssistantId`, and `submitError` local state now all survive
collapse-then-expand without flicker or refetch races.

### WR-03: ChatThread always flashes trades green, even on sell

**Files modified:** `frontend/src/components/chat/ChatThread.tsx`,
`frontend/src/components/terminal/TradeBar.tsx`
**Commit:** `11e5e61`
**Applied fix:** Chose Option B (keep current behavior, document it) per
the explicit intent in `08-UI-SPEC.md` §4.2 row D-12: "Position-row
trade-flash … `bg-up/20` for ~800ms after a chat-driven `executed`
BUY card lands; **also** for any `executed` SELL card lands and total
cash increases (the agentic 'wow') | `bg-down/20` if the card is
`failed`; failed trades flash on the action card only (no position row
to flash; row may not exist)." The same paragraph also locks manual
trades to always 'up'. Added short comments at both sites explaining
that direction means executed (up) vs failed (down), not buy/sell, so
future readers don't "fix" it the wrong way.

### WR-04: TabBar uses button + aria-pressed instead of true tab semantics

**Files modified:** `frontend/src/components/terminal/TabBar.tsx`,
`frontend/src/components/terminal/Terminal.tsx`,
`frontend/src/components/terminal/TabBar.test.tsx`
**Commit:** `3211188`
**Applied fix:** Replaced `<nav>` + `<button aria-pressed>` with the
WAI-ARIA Tabs pattern: a `<div role="tablist" aria-label="Center column tabs">`
wrapping `<button role="tab" id="tab-<id>" aria-selected aria-controls="panel-<id>" tabIndex={active ? 0 : -1}>`.
Wrapped each conditionally rendered panel in `Terminal.tsx` with
`<div role="tabpanel" id="panel-<id>" aria-labelledby="tab-<id>">` so
screen readers announce the relationship. Updated `TabBar.test.tsx` to
query by `getByRole('tab')` / `getByRole('tablist')` and assert the new
ARIA attributes (aria-selected, aria-controls, id, tabindex). Arrow-key
navigation between tabs is left as a future enhancement per the review
note ("ARIA roles + labels alone resolve the accessibility regression").

---

_Fixed: 2026-04-26T22:20:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
