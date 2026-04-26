---
phase: 08-portfolio-visualization-chat-ui
plan: 06
subsystem: ui
tags: [react, nextjs, vitest, chat, drawer, action-card, xss-mitigation]

# Dependency graph
requires:
  - phase: 08-portfolio-visualization-chat-ui/02
    provides: ChatMessageOut / ChatResponse / ActionsBlock wire types in frontend/src/lib/api/chat.ts
  - phase: 08-portfolio-visualization-chat-ui/05
    provides: Terminal.tsx flex-row restructure with data-testid="chat-drawer-slot" placeholder slot
provides:
  - ThinkingBubble — 3-dot CSS-keyframed loading bubble (D-08)
  - ChatHeader — drawer title + Unicode-guillemet toggle (›/‹) (D-09)
  - ChatMessage — user/assistant bubble; renders content via plain JSX text only (T-08-12 mitigation)
  - ActionCard — 6-status card with 800ms first-mount pulse via useEffect+setTimeout (D-12)
  - ActionCardList — orders watchlist_changes BEFORE trades (D-09 / D-10)
  - ChatDrawer — collapsible <aside> shell with children-based open-state slot
  - 8 Vitest tests across 3 files
affects:
  - 08-07 (will mount ChatDrawer in Terminal.tsx, replacing the placeholder slot, and pass <ChatThread /> as children)
  - 08-08 (FE-11 polish + final build gate)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Status-driven className lookup: STATUS_STYLE Record<Status, {borderClass,textClass,label}> mirrors ConnectionDot.tsx CLASSES pattern"
    - "Per-component pulse timer: useState(initial) + useEffect setTimeout(800ms) clearing class — pure component-local, no store touch"
    - "XSS-safe content render: JSX text node only (no dangerouslySetInnerHTML, no markdown→HTML conversion); whitespace-pre-wrap preserves newlines without HTML interpretation"
    - "Children-as-slot drawer: ChatDrawer accepts ReactNode children for open-state body, decoupling shell from thread/input"
    - "Phase 7 ERROR_TEXT carry-forward + Phase 5 extension: 4 verbatim trade-error strings + 2 new (invalid_ticker, internal_error)"

key-files:
  created:
    - frontend/src/components/chat/ThinkingBubble.tsx
    - frontend/src/components/chat/ChatHeader.tsx
    - frontend/src/components/chat/ChatMessage.tsx
    - frontend/src/components/chat/ActionCard.tsx
    - frontend/src/components/chat/ActionCardList.tsx
    - frontend/src/components/chat/ChatDrawer.tsx
    - frontend/src/components/chat/ChatDrawer.test.tsx
    - frontend/src/components/chat/ActionCard.test.tsx
    - frontend/src/components/chat/ActionCardList.test.tsx
  modified: []

key-decisions:
  - "ChatDrawer is intentionally a shell with no ChatThread import — Plan 07 wires <ChatThread /> as children prop in Terminal.tsx. Decoupling lets primitives ship/test in isolation."
  - "ChatMessage renders {message.content} as a JSX text node only (whitespace-pre-wrap preserves newlines). No dangerouslySetInnerHTML, no markdown→HTML. Mitigates threat T-08-12 at the /api/chat → DOM trust boundary."
  - "ActionCard pulse is component-local: useEffect+setTimeout(800ms) toggles a CSS class. NOT shared with the price-store tradeFlash slice — different lifetimes (per-card mount vs. per-ticker debounced)."
  - "STATUS_STYLE collapses 'added' and 'removed' watchlist statuses into the same green visual treatment as 'executed' trades — matches UI-SPEC §5.7. 'exists' and 'not_present' get the muted gray treatment for idempotent no-ops."
  - "ChatDrawer's children?: ReactNode is optional so Plan 06's tests can render the shell standalone; Plan 07 will pass <ChatThread /> as the actual children."

patterns-established:
  - "STATUS_STYLE Record<Status, {borderClass, textClass, label}> — extends the ConnectionDot.tsx CLASSES idiom for any future status-driven render"
  - "Component-local pulse via useEffect/setTimeout(800ms) clearing a CSS animation class, decoupled from store flash timers"
  - "Children-slot drawer pattern: collapsible <aside> shell that takes the open-state body via ReactNode children — testable without coupling to its eventual occupant"
  - "Test selector pattern for prefix-querySelector matches: filter out parent-list testids when child testids share the same prefix (avoids false-positive in Array.from)"

requirements-completed: [FE-09, FE-11, TEST-02]

# Metrics
duration: ~13min
completed: 2026-04-26
---

# Phase 08 Plan 06: Chat Primitives + ChatDrawer Shell Summary

**Six render-only chat primitives (ThinkingBubble, ChatHeader, ChatMessage, ActionCard, ActionCardList, ChatDrawer) + 8 Vitest tests; XSS-safe content render, 6-status STATUS_STYLE map, 800ms first-mount action pulse, children-slot drawer shell ready for Plan 07's ChatThread wiring.**

## Performance

- **Duration:** ~13 min
- **Started:** 2026-04-26T12:14:00Z (approximate session start)
- **Completed:** 2026-04-26T12:27:00Z
- **Tasks:** 3 (5 primitives + drawer shell + 8 tests)
- **Files created:** 9

## Accomplishments
- 5 render-only chat primitives (ThinkingBubble / ChatHeader / ChatMessage / ActionCard / ActionCardList) all under the 120-LOC budget per file
- ChatDrawer SHELL with ReactNode children slot — deliberately decoupled from ChatThread (which Plan 07 builds)
- 8 Vitest tests across 3 files (2 ChatDrawer + 4 ActionCard + 2 ActionCardList) — full suite 101/101 (was 93)
- XSS mitigation T-08-12 enforced: zero `dangerouslySetInnerHTML` in `frontend/src/components/chat/`
- Phase 7 ERROR_TEXT inheritance: 4 verbatim strings + 2 new (`invalid_ticker`, `internal_error`)
- Action-pulse + thinking-dot CSS keyframes already wired in `frontend/src/app/globals.css` (Wave 1 prep) — primitives use them via class names

## Task Commits

1. **Task 1: Five render-only primitives** — `d56b701` (feat)
2. **Task 2: ChatDrawer SHELL** — `54e41e6` (feat)
3. **Task 3: 8 Vitest tests** — `f0576b4` (test)

## Files Created/Modified

### Created
- `frontend/src/components/chat/ThinkingBubble.tsx` (21 non-blank LOC) — 3-dot CSS animation bubble; aria-label "Assistant is thinking"; role="status"
- `frontend/src/components/chat/ChatHeader.tsx` (26 non-blank LOC) — drawer title strip; Unicode `›` (open) / `‹` (collapse) toggle button; aria-expanded reflects state
- `frontend/src/components/chat/ChatMessage.tsx` (36 non-blank LOC) — user/assistant bubble; `{message.content}` rendered as JSX text only; ActionCardList nested when actions != null
- `frontend/src/components/chat/ActionCard.tsx` (106 non-blank LOC) — STATUS_STYLE map for all 6 statuses + ERROR_COPY map (Phase 7 + Phase 5); 800ms first-mount pulse via useEffect+setTimeout
- `frontend/src/components/chat/ActionCardList.tsx` (27 non-blank LOC) — spreads watchlist_changes BEFORE trades; returns null on empty
- `frontend/src/components/chat/ChatDrawer.tsx` (28 non-blank LOC) — collapsible `<aside>` shell; default-open w-[380px]; collapses to w-12 with transition-[width] duration-300; ReactNode children slot
- `frontend/src/components/chat/ChatDrawer.test.tsx` (2 tests) — default open w-[380px]; toggle collapses to w-12 + hides children
- `frontend/src/components/chat/ActionCard.test.tsx` (4 tests) — executed (green border + text-up); failed (red border + text-down + mapped error); exists/not_present (muted gray); unknown error code → DEFAULT_ERROR
- `frontend/src/components/chat/ActionCardList.test.tsx` (2 tests) — watchlist before trades; empty arrays render nothing

## Decisions Made

- **D-1 (08-06): ChatDrawer is a shell, not a controller.** The drawer accepts `children?: ReactNode` rather than internally importing `<ChatThread />`. Plan 07 will mount `<ChatDrawer><ChatThread /></ChatDrawer>` inside Terminal.tsx, replacing the placeholder `<aside data-testid="chat-drawer-slot">` from Plan 05. Decoupling lets the shell ship and test independently of its eventual occupant.
- **D-2 (08-06): Component-local pulse timer for ActionCard.** Pulse class is held in component `useState` and cleared by a per-instance `setTimeout(800)` in `useEffect`. Different concern from the price-store `tradeFlash` slice (which spans positions table flash and persists longer). No shared timer infrastructure.
- **D-3 (08-06): JSX text node render for ChatMessage.content (T-08-12).** No `dangerouslySetInnerHTML`, no markdown→HTML. `whitespace-pre-wrap` preserves newlines without enabling HTML injection. Plan 07 will add a unit test asserting that `<script>` payloads in assistant content remain inert (no `window.__pwned`).
- **D-4 (08-06): STATUS_STYLE collapses added/removed/executed into one green treatment.** Per UI-SPEC §5.7: positive trade outcome (executed buy/sell) and positive watchlist outcome (added/removed) read identically. Failed reads red; idempotent (exists / not_present) reads muted gray. Six statuses, three visual treatments.
- **D-5 (08-06): Phase 7 error string inheritance.** ActionCard's ERROR_COPY copies the four overlapping codes verbatim from `TradeBar.tsx` (insufficient_cash, insufficient_shares, unknown_ticker, price_unavailable) and adds two Phase 5 codes (invalid_ticker, internal_error). Same default fallback string. Single source of truth for trade-error wording.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ActionCardList test prefix selector matched the list wrapper testid**
- **Found during:** Task 3 (running new ActionCardList test)
- **Issue:** `container.querySelectorAll('[data-testid^="action-card-"]')` matched 3 elements because both the list wrapper (`data-testid="action-card-list"`) and the individual cards (`data-testid="action-card-{status}"`) share the `action-card-` prefix. Test asserted length === 2 and failed.
- **Fix:** Filtered the result to drop elements whose `dataset.testid === 'action-card-list'`. Test now asserts only the per-card matches (2).
- **Files modified:** `frontend/src/components/chat/ActionCardList.test.tsx`
- **Verification:** Re-ran the 3 chat test files (8/8 pass) and the full suite (101/101 pass).
- **Committed in:** `f0576b4` (Task 3 commit)

**2. [Rule 1 - Cosmetic acceptance grep] Docstring substring matches inflated grep counts**
- **Found during:** Task 1 acceptance check (`grep -c dangerouslySetInnerHTML`) and Task 2 acceptance check (`grep -c ChatThread`, `grep -c w-\[380px\]`, `grep -c w-12`)
- **Issue:** The first-pass docstrings mentioned the literal token names (e.g., "no dangerouslySetInnerHTML, no markdown→HTML" and "w-[380px], collapses to w-12") to document the safety/sizing intent. The plan's grep acceptance asks for `outputs 0` (or exactly 1) — the docstring matches inflated those counts.
- **Fix:** Rewrote both docstrings to convey the same intent without naming the tokens literally. Substantive code is unchanged; only comments edited.
- **Files modified:** `frontend/src/components/chat/ChatMessage.tsx`, `frontend/src/components/chat/ChatDrawer.tsx`
- **Verification:** All grep acceptance counts now match the plan's expected values; tsc clean for chat/; tests pass.
- **Committed in:** `d56b701` (Task 1) and `54e41e6` (Task 2)

---

**Total deviations:** 2 auto-fixed (2 Rule-1 bugs)
**Impact on plan:** Neither deviation altered any production behavior — one fixed a test-only false positive, the other refined doc-string wording to match the plan's acceptance grep semantics. Zero scope creep.

## Issues Encountered

- Pre-existing tsc errors in `MainChart.test.tsx` and `Sparkline.test.tsx` (5 errors total) were observed when running `npx tsc --noEmit`. Confirmed they exist on the HEAD commit before any 08-06 changes — out-of-scope per the deviation Rule scope boundary, and Vitest does not run tsc. Logged here for awareness; not fixed.

## Self-Check

Verifying all claims before handoff to verifier.

### Files exist
- `frontend/src/components/chat/ThinkingBubble.tsx` — FOUND
- `frontend/src/components/chat/ChatHeader.tsx` — FOUND
- `frontend/src/components/chat/ChatMessage.tsx` — FOUND
- `frontend/src/components/chat/ActionCard.tsx` — FOUND
- `frontend/src/components/chat/ActionCardList.tsx` — FOUND
- `frontend/src/components/chat/ChatDrawer.tsx` — FOUND
- `frontend/src/components/chat/ChatDrawer.test.tsx` — FOUND
- `frontend/src/components/chat/ActionCard.test.tsx` — FOUND
- `frontend/src/components/chat/ActionCardList.test.tsx` — FOUND

### Commits exist
- `d56b701` (feat: 5 chat primitives) — FOUND in `git log --oneline`
- `54e41e6` (feat: ChatDrawer shell) — FOUND
- `f0576b4` (test: 8 vitest tests) — FOUND

### Acceptance gates
- `grep -r "dangerouslySetInnerHTML" frontend/src/components/chat/` returns 0 — VERIFIED (no actual usage and no docstring mentions)
- `grep -c "ChatThread" frontend/src/components/chat/ChatDrawer.tsx` returns 0 — VERIFIED (Plan 07 will wire ChatThread, not Plan 06)
- All 6 components ≤120 non-blank LOC — VERIFIED (max 106 in ActionCard.tsx)
- Full Vitest suite: 101/101 (was 93 + 8 new) — VERIFIED via `npm run test:ci`

## Self-Check: PASSED

## Next Phase Readiness

- All Plan 08-06 primitives are in place; Plan 08-07 can now create:
  - `ChatThread.tsx` (consumes ChatMessage + ThinkingBubble; useQuery(['chat','history']) + useMutation(postChat))
  - `ChatInput.tsx` (textarea + Enter-submit; useMutation onSuccess clears + refocuses)
  - Mount `<ChatDrawer><ChatThread /><ChatInput /></ChatDrawer>` in Terminal.tsx, replacing the `<aside data-testid="chat-drawer-slot">` placeholder at lines 44-48
  - Add the XSS-payload assertion test (window.__pwned remains undefined for `<script>` in assistant content)
  - Add the 2 ChatThread + ChatInput test cases (closing FE-09, FE-10, FE-12 + TEST-02 final scope)
- No blockers. The chat-drawer-slot placeholder in Terminal.tsx remains untouched as expected.

---
*Phase: 08-portfolio-visualization-chat-ui*
*Plan: 06*
*Completed: 2026-04-26*
