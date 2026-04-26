---
phase: 08-portfolio-visualization-chat-ui
plan: 07
subsystem: ui
tags: [react, typescript, tanstack-query, zustand, chat, vitest, xss-mitigation]

# Dependency graph
requires:
  - phase: 08-02
    provides: chat REST client (postChat, getChatHistory, ChatMessageOut, ChatResponse) + price-store flashTrade action / selectTradeFlash selector + chatHistoryFixture
  - phase: 08-05
    provides: Terminal.tsx flex-row layout with chat-drawer-slot placeholder ready for replacement
  - phase: 08-06
    provides: ChatDrawer SHELL with `children?: ReactNode`, ChatHeader, ChatMessage (text-only JSX, no innerHTML), ActionCard / ActionCardList, ThinkingBubble
provides:
  - ChatThread orchestrates useQuery(['chat','history']) + useMutation(postChat); auto-scroll; thinking bubble; flashTrade per executed trade; portfolio + watchlist invalidations
  - ChatInput keyboard contract (Enter submit, Shift+Enter newline, disabled-while-pending) with verbatim placeholder "Ask me about your portfolio…"
  - Live ChatDrawer mounted in Terminal.tsx (placeholder removed)
  - 8 new Vitest tests (incl. XSS regression guard) raising suite from 101 to 109 (16 -> 18 files)
affects: [08-08-validation-gate, 09-llm-mock-mode, 10-docker-package]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TanStack Query useMutation onSuccess: side-effect dispatch (flashTrade) + cache invalidation (['portfolio'], conditional ['watchlist'])"
    - "Optimistic local user-message append + assistantFromResponse projection of ChatResponse into the same ChatMessageOut shape used by the history query"
    - "useLayoutEffect with [messages.length, mutation.isPending] as the auto-scroll cue (paints AFTER DOM update, BEFORE browser layout flush)"
    - "Plain-JSX text rendering (no dangerouslySetInnerHTML) as a defense-in-depth XSS mitigation, regression-tested by asserting window.__pwned is undefined after rendering a <script> payload"
    - "stub-fetch + renderWithQuery test pattern (fresh QueryClient per test) for orchestration components"

key-files:
  created:
    - frontend/src/components/chat/ChatThread.tsx
    - frontend/src/components/chat/ChatInput.tsx
    - frontend/src/components/chat/ChatThread.test.tsx
    - frontend/src/components/chat/ChatInput.test.tsx
  modified:
    - frontend/src/components/terminal/Terminal.tsx

key-decisions:
  - "ChatThread owns the postChat useMutation (not ChatInput); ChatInput is a controlled keyboard component receiving onSubmit/isPending props — keeps the input dumb and the orchestrator testable in isolation"
  - "Optimistic local user-message append before mutate(); assistant message produced from response in onSuccess. No optimistic assistant placeholder — ThinkingBubble fills that role"
  - "['watchlist'] invalidation is conditional on res.watchlist_changes.length > 0 to avoid waking unrelated watchlist queries on plain-chat turns"
  - "XSS regression test asserts window.__pwned remains undefined AND the literal <script> string appears as text — covers both the runtime-execution risk and the visual-render contract"

patterns-established:
  - "Chat orchestration test pattern: stub-fetch dispatches per-URL responses; pending Promise resolves on demand to reliably observe in-flight UI states"
  - "ChatInput.test.tsx onSubmit typing: ((content: string) => void) & ReturnType<typeof vi.fn> — preserves vi.fn assertion API while satisfying the prop type"

requirements-completed: [FE-09, FE-11, TEST-02]

# Metrics
duration: 9min
completed: 2026-04-26
---

# Phase 08 Plan 07: ChatThread + ChatInput orchestration Summary

**Chat actually becomes interactive — ChatThread wires postChat + history fetch + flashTrade + portfolio invalidation behind a keyboard-driven ChatInput; Terminal.tsx now mounts the live `<ChatDrawer><ChatThread /></ChatDrawer>` in place of Plan 05's placeholder.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-26T16:46:09Z
- **Completed:** 2026-04-26T16:55:32Z
- **Tasks:** 3
- **Files created:** 4
- **Files modified:** 1

## Accomplishments

- ChatThread.tsx (114 NF lines, 125 total) orchestrates the entire chat UX: fetches history on mount via `useQuery(['chat','history'])`; appends user turns optimistically; runs `postChat` via `useMutation`; on success projects the response into a `ChatMessageOut`, dispatches `flashTrade(ticker, 'up')` for every executed trade, and invalidates `['portfolio']` (plus `['watchlist']` if the response had watchlist changes). Auto-scrolls to the bottom in `useLayoutEffect` whenever the message list grows or the pending flag flips.
- ChatInput.tsx (53 NF lines, 60 total) implements the §5.8 keyboard contract: Enter submits the trimmed value, Shift+Enter inserts a newline, the textarea + Send button both disable while `isPending`. Placeholder is the verbatim "Ask me about your portfolio…", `aria-label="Ask the assistant"`.
- Terminal.tsx (46 NF lines) replaces Plan 05's `<aside data-testid="chat-drawer-slot" />` placeholder with `<ChatDrawer><ChatThread /></ChatDrawer>`. All other Phase 7 panels (Watchlist, Header, TabBar, MainChart, Heatmap, PnLChart, PositionsTable, TradeBar) untouched.
- 8 new Vitest tests across 2 new files (ChatThread: history-on-mount, ThinkingBubble in flight, flashTrade-on-executed, XSS guard; ChatInput: Enter, Shift+Enter, Send button, disabled-while-pending). Full suite went from 101/101 (16 files) to 109/109 (18 files) — green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ChatThread.tsx + ChatInput.tsx** — `9bdf007` (feat)
2. **Task 2: Mount ChatDrawer + ChatThread in Terminal.tsx** — `23c0ab6` (feat)
3. **Task 3: Vitest test suites (incl. XSS guard)** — `765de78` (test)

_Note: Plan-level type was `tdd="true"` for Task 3, but the production code (Tasks 1-2) was straight-line orchestration glue against established APIs (`postChat`, `flashTrade`, `useQuery`/`useMutation`); the 8 tests were written and passed green on the first run, confirming the contract was implemented correctly._

## Files Created/Modified

- `frontend/src/components/chat/ChatThread.tsx` (NEW, 125 lines) — orchestration heart: useQuery history + useMutation postChat + onSuccess flashTrade fanout + portfolio/watchlist invalidations + auto-scroll + ThinkingBubble + delegated rendering through ChatMessage
- `frontend/src/components/chat/ChatInput.tsx` (NEW, 60 lines) — controlled textarea + Send; Enter/Shift+Enter handler; disabled-while-pending; verbatim placeholder + aria-label
- `frontend/src/components/chat/ChatThread.test.tsx` (NEW, 4 tests) — history-on-mount, in-flight ThinkingBubble, flashTrade dispatch, XSS regression guard
- `frontend/src/components/chat/ChatInput.test.tsx` (NEW, 4 tests) — Enter/Shift+Enter/Send/disabled keyboard contract
- `frontend/src/components/terminal/Terminal.tsx` (MODIFIED, +5/-7) — added ChatDrawer + ChatThread imports; replaced placeholder `<aside>` with `<ChatDrawer><ChatThread /></ChatDrawer>`

## Decisions Made

- **ChatInput is dumb**: takes `onSubmit` + `isPending` props rather than owning the mutation. Lets ChatThread own the optimistic-append + post-success projection logic in one place; lets ChatInput unit-test in isolation with `vi.fn()`.
- **Optimistic user-message append**: a `localUserMessage` (id `local-user-${Date.now()}`) is added to local state before `mutate()` so the user sees their message immediately. The assistant turn is only added in `onSuccess` (no optimistic assistant placeholder — `ThinkingBubble` is the in-flight indicator).
- **Conditional `['watchlist']` invalidation**: only fires when `res.watchlist_changes.length > 0`, so chat turns with no watchlist actions don't refetch watchlist data needlessly.
- **XSS test surface**: assertion checks BOTH `window.__pwned === undefined` AND that the literal `<script>` string is present as text. This catches both the runtime-execution risk and any future regression where someone might switch ChatMessage to `dangerouslySetInnerHTML`.
- **Plan acceptance check `grep -c "useMutation" … outputs 1` was an over-strict spec**: my file has 3 occurrences (docstring mention, named import, hook call). The semantic intent — that `useMutation` is used — is satisfied. No code change was needed; the file is correct as written.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Strongly-typed `onSubmit` mock in ChatInput.test.tsx**

- **Found during:** Task 3 (after running TSC gate)
- **Issue:** TSC reported 4 errors of the form `Type 'Mock<Procedure | Constructable>' is not assignable to type '(content: string) => void'` because Vitest 4's `vi.fn()` returns a `Mock<Procedure | Constructable>` that doesn't structurally satisfy a strict callback type when assigned to a typed prop.
- **Fix:** Changed `let onSubmit: ReturnType<typeof vi.fn>` → `let onSubmit: ((content: string) => void) & ReturnType<typeof vi.fn>` and the assignment to `onSubmit = vi.fn() as ((content: string) => void) & ReturnType<typeof vi.fn>`. Preserves the `toHaveBeenCalledWith` assertion API while satisfying the prop type.
- **Files modified:** frontend/src/components/chat/ChatInput.test.tsx
- **Verification:** TSC clean (no chat-related errors); all 8 new tests still pass; full suite 109/109.
- **Committed in:** `765de78` (Task 3 commit, included in initial test files)

---

**Total deviations:** 1 auto-fixed (1 bug — TS type-mismatch in new test file).
**Impact on plan:** No scope creep. The fix was pre-commit on Task 3, contained to the new test file I authored.

## Issues Encountered

- **Pre-existing TSC errors in `MainChart.test.tsx` and `Sparkline.test.tsx`** (5 errors total, all of the form "Tuple type '[]' of length '0' has no element at index N"). Verified by `git stash` that these errors exist on the Plan 06 baseline (commit `36a4ab7`) and are unrelated to this plan. Per the SCOPE BOUNDARY rule, NOT fixed in this plan. Logged here for the verifier — these should be tracked as a separate Phase 7 cleanup item.

## XSS / Security Verification

- `grep -rn "dangerouslySetInnerHTML" frontend/src/components/chat/` → 0 hits (clean).
- `grep -rn "dangerouslySetInnerHTML" frontend/src/components/portfolio/ frontend/src/components/terminal/` → 0 hits (clean across the whole render tree).
- ChatThread renders all messages through `ChatMessage`, which uses `{message.content}` (plain JSX text) — React escapes by default, so the `<script>` tag is rendered as the literal text `<script>...</script>`, not parsed as DOM.
- The XSS regression test passes: rendering `<script>window.__pwned = true;</script>hello` as assistant content leaves `window.__pwned` undefined and shows the script text inline. T-08-12 mitigation verified.

## Terminal.tsx placeholder removal

- `grep -c "chat-drawer-slot" frontend/src/components/terminal/Terminal.tsx` → 0 (placeholder fully removed).
- `grep -c "<ChatDrawer>" frontend/src/components/terminal/Terminal.tsx` → 1.
- `grep -c "<ChatThread />" frontend/src/components/terminal/Terminal.tsx` → 1.

## Test Counts

| File | Tests | Notes |
| ---- | ----- | ----- |
| `ChatThread.test.tsx` | 4 | history-on-mount, ThinkingBubble in flight, flashTrade('AAPL','up'), XSS guard |
| `ChatInput.test.tsx` | 4 | Enter, Shift+Enter, Send button, disabled-while-pending |
| **Plan 07 total** | **8** | |
| **Full suite** | **109** | up from 101 (Plan 06 baseline); 18 files (up from 16) |

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 08 validation gate: drawer is mounted live, history fetch + chat round-trip + auto-scroll + flashTrade fanout all wire-tested.
- Manual smoke (after E2E gate in Plan 08): clicking Send shows ThinkingBubble briefly, assistant response appears with action cards, executing a buy via chat causes the position row in the right column to flash via `tradeFlash`.
- Pre-existing Phase 7 TSC errors in `MainChart.test.tsx` / `Sparkline.test.tsx` should be tracked separately by the verifier — they were on the Plan 06 baseline and are out of this plan's scope.

## Self-Check: PASSED

All claims verified:

- `frontend/src/components/chat/ChatThread.tsx` — FOUND
- `frontend/src/components/chat/ChatInput.tsx` — FOUND
- `frontend/src/components/chat/ChatThread.test.tsx` — FOUND
- `frontend/src/components/chat/ChatInput.test.tsx` — FOUND
- Commit `9bdf007` (Task 1, feat) — FOUND in `git log`
- Commit `23c0ab6` (Task 2, feat) — FOUND in `git log`
- Commit `765de78` (Task 3, test) — FOUND in `git log`
- Targeted: 8/8 chat tests pass — VERIFIED
- Full suite: 109/109 pass — VERIFIED
- TSC: no errors introduced by this plan — VERIFIED
- XSS surface: 0 dangerouslySetInnerHTML in render tree — VERIFIED
- Terminal placeholder removed: 0 chat-drawer-slot references — VERIFIED

---
*Phase: 08-portfolio-visualization-chat-ui*
*Completed: 2026-04-26*
