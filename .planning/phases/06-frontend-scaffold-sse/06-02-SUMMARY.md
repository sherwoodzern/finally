---
phase: 06-frontend-scaffold-sse
plan: 02
subsystem: frontend
tags: [nextjs, typescript, zustand, sse, eventsource, app-router, tailwindcss-v4]

# Dependency graph
requires:
  - phase: 06-frontend-scaffold-sse
    plan: 01
    provides: "frontend/ Next.js App Router scaffold, zustand installed, dark theme, layout.tsx with html/body classes and metadata"
  - phase: 01-app-shell-config
    provides: "/api/stream/prices SSE endpoint emitting JSON dict of PriceUpdate.to_dict() values at ~500ms cadence"
provides:
  - "Zustand price store (usePriceStore) with ticker-keyed Record<string, Tick>, ConnectionStatus, lastEventAt timestamp"
  - "Idempotent single-EventSource lifecycle (connect/disconnect) owned by PriceStreamProvider"
  - "Frontend-computed session_start_price frozen on first-seen-per-ticker (D-14)"
  - "Connection-status state machine: onopen->connected, onerror readyState 0->reconnecting, readyState 2->disconnected"
  - "Narrow log-and-drop error boundary at JSON.parse+ingest wire edge (D-19)"
  - "Test-only DI hook __setEventSource for Plan 06-03 Vitest + MockEventSource suite"
  - "Named exports: usePriceStore, selectTick, selectConnectionStatus, __setEventSource"
  - "Root layout wired: <PriceStreamProvider>{children}</PriceStreamProvider> wraps app body; preserves Plan 01 dark class and bg-surface text-foreground"
affects: [06-03-debug-page-tests, 07-frontend-panels, 08-ai-chat-frontend]

# Tech tracking
tech-stack:
  added: []  # No new deps; zustand already installed in Plan 06-01
  patterns:
    - "Zustand 5 double-parens TS: create<State>()((set, get) => ({ ... }))"
    - "Module-level es: EventSource | null singleton (private to price-store.ts)"
    - "Module-level EventSourceCtor with SSR-safe window guard; test DI via __setEventSource()"
    - "First-seen-value freeze: session_start_price: prior?.session_start_price ?? raw.price"
    - "Narrow try/catch at JSON.parse+ingest only - no outer wrappers, no rethrow"
    - "Structured console.warn args (err, event.data) - never template-literal"
    - "Idempotent lifecycle: if (es && es.readyState !== 2) return"
    - "useEffect(() => { connect(); return () => disconnect(); }, []) empty-deps mount/unmount"

key-files:
  created:
    - "frontend/src/lib/sse-types.ts"
    - "frontend/src/lib/price-store.ts"
    - "frontend/src/lib/price-stream-provider.tsx"
  modified:
    - "frontend/src/app/layout.tsx"
    - ".gitignore"

key-decisions:
  - "D-11 implemented: PriceStreamProvider is the sole EventSource lifecycle owner; mounted outermost in layout.tsx so Plan 06-03 /debug will inherit it"
  - "D-12 verified: Zustand 5 selected and applied with double-parens TS pattern (not v3 single-parens, which deprecates slice inference)"
  - "D-13 canonical: store shape is prices + status + lastEventAt + connect/disconnect/ingest/reset exactly as specified; no extras, no rename"
  - "D-14 encoded: session_start_price frozen via nullish-coalescing - prior?.session_start_price ?? raw.price - Tick extends RawPayload keeps backend-emitted keys intact"
  - "D-15 idempotent connect: if (es && es.readyState !== 2) return - single-line guard, StrictMode-safe in dev"
  - "D-16 relative URL: const SSE_URL = '/api/stream/prices' - no env var, no absolute URL"
  - "D-17 event parsing: onmessage JSON.parse -> ingest -> status flips to connected on first successful parse"
  - "D-18 state machine encoded verbatim: onopen connected; onerror readyState===0 reconnecting; onerror readyState===2 disconnected"
  - "D-19 narrow boundary: single try/catch around JSON.parse+ingest, console.warn with structured args, no rethrow; inner isValidPayload skips per-ticker malformed entries silently"
  - "D-23 layout: price-stream-provider.tsx lives in src/lib/ (not src/components/ as UI-SPEC section 7 suggested); D-23 explicitly names src/lib/price-stream-provider.tsx as authoritative, and plan 06-02 frontmatter reinforces this"
  - "Claude's Discretion on provider placement: outermost in layout.tsx body so any future route (including Plan 06-03 /debug) inherits the live EventSource without remounting"

requirements-completed: []  # FE-02 is PARTIAL per plan SC; store + provider implemented, test+debug-page verification arrive in Plan 06-03

# Metrics
duration: "15m 28s"
completed: 2026-04-24
---

# Phase 6 Plan 2: SSE Client and Price Store Summary

**Three-file SSE client lands: sse-types.ts pins the wire contract, price-store.ts owns the idempotent EventSource lifecycle with D-14 session-start freeze and D-19 narrow log-and-drop, price-stream-provider.tsx is the 22-line React analog of SimulatorDataSource.start/stop, and layout.tsx wraps {children} with it - build remains green with all four brand hex values still in the chunks CSS.**

## Performance

- **Duration:** 15m 28s
- **Started:** 2026-04-24T04:46:47Z
- **Completed:** 2026-04-24T05:02:15Z
- **Tasks:** 4 of 4 (Task 4 is the verification gate; no source commit)
- **Files modified:** 3 created, 2 modified

## Accomplishments

- `frontend/src/lib/sse-types.ts` (24 lines, budget 40) exports Direction, ConnectionStatus, RawPayload, Tick. RawPayload mirrors backend/app/market/models.py PriceUpdate.to_dict() verbatim (seven keys). Tick extends RawPayload with one client-only field session_start_price.
- `frontend/src/lib/price-store.ts` (103 lines, budget 120) creates the Zustand store with:
  - Store shape exactly per D-13: prices, status, lastEventAt, connect, disconnect, ingest, reset.
  - D-14 first-seen freeze encoded at one line: `session_start_price: prior?.session_start_price ?? raw.price`.
  - D-15 idempotent connect guard: `if (es && es.readyState !== 2) return`.
  - D-16 relative URL: `const SSE_URL = '/api/stream/prices'`.
  - D-17 onmessage JSON.parse -> ingest -> status flips to connected when still reconnecting or disconnected.
  - D-18 state machine: onopen -> connected, onerror readyState 0 -> reconnecting, readyState 2 -> disconnected.
  - D-19 single narrow try/catch wrapping JSON.parse + ingest with structured console.warn args (err, event.data); no rethrow; inner isValidPayload silently skips per-ticker malformed entries while valid entries in the same batch ingest.
  - Named exports only: usePriceStore, __setEventSource, selectTick, selectConnectionStatus. No default export.
  - Zustand 5 TypeScript double-parens: `create<PriceStoreState>()((set, get) => ({...}))`.
  - SSR-safe EventSourceCtor initialization: `typeof window !== 'undefined' ? window.EventSource : (undefined as unknown as typeof EventSource)`.
- `frontend/src/lib/price-stream-provider.tsx` (22 lines, budget 40) is a `'use client'` React component that calls `usePriceStore.getState().connect()` on mount and returns `() => disconnect()` as cleanup. useEffect has empty deps so it runs once per mount under production; the store's D-15 idempotent guard makes StrictMode double-invoke in dev a no-op.
- `frontend/src/app/layout.tsx` edited (18 lines, two changes exactly as planned):
  1. Added `import { PriceStreamProvider } from '@/lib/price-stream-provider';` after the globals.css import.
  2. Wrapped `{children}` with `<PriceStreamProvider>{children}</PriceStreamProvider>` inside `<body>`.
  Preserved: metadata export, `className="dark"` on `<html>`, `className="bg-surface text-foreground"` on `<body>`, and `import './globals.css'`.
- Wave-2 gate GREEN:
  - `npx tsc --noEmit` exits 0.
  - `npm run build` exits 0, produces `frontend/out/index.html`, benign `rewrites + output: 'export'` warning noted (RESEARCH G2).
  - `npm run lint` exits 0.
  - Tailwind tokens preserved: all four brand hex values (#ecad0a, #0d1117, #209dd7, #753991) still present in `out/_next/static/chunks/0iotgua87fvey.css`.
  - Bundle baseline: 636K in `out/_next/static/chunks/` total, 836K in `out/` overall.

## Task Commits

1. **Task 1: Write sse-types.ts + price-store.ts** - `669195f` (feat)
2. **Task 2: Write price-stream-provider.tsx** - `288bbf6` (feat)
3. **Task 3: Wire PriceStreamProvider into root layout** - `6f942a7` (feat)
4. **Task 4: Wave-2 merge gate** - verification-only, no source commit (tsc + build + lint + token preservation all green)

Each commit follows Conventional Commits with phase-plan scope `(06-02)`. No emojis in any commit message. No amendments. No force-pushes.

## Files Created/Modified

### Created
- `frontend/src/lib/sse-types.ts` - 24 lines. Direction (up/down/flat union), ConnectionStatus (connected/reconnecting/disconnected union), RawPayload (7 keys mirroring backend PriceUpdate.to_dict()), Tick (extends RawPayload with session_start_price).
- `frontend/src/lib/price-store.ts` - 103 lines. Zustand store with EventSource lifecycle, selectors, and test DI. Single module-level es and EventSourceCtor. 80% of code is the store creator; remainder is selectors and type plumbing.
- `frontend/src/lib/price-stream-provider.tsx` - 22 lines. 'use client' React component that calls connect() in useEffect mount, disconnect() in cleanup. Empty deps. No state, no JSX beyond Fragment wrapper around children.

### Modified
- `frontend/src/app/layout.tsx` - 18 lines (was 17). One import added, `{children}` replaced with `<PriceStreamProvider>{children}</PriceStreamProvider>`. Dark class, body class, metadata, and globals.css import all preserved.
- `.gitignore` - 2 lines added (`!frontend/src/lib/` and `!frontend/src/lib/**`) to un-ignore the Phase 06 contract directory from the Python template's `lib/` rule. See Deviations below.

## Decisions Made

- **PriceStreamProvider lives in `src/lib/` not `src/components/`** - UI-SPEC section 7 lists `src/components/PriceStreamProvider.tsx` but CONTEXT.md D-23 and the plan 06-02 frontmatter both specify `src/lib/price-stream-provider.tsx`. Per the phase_specific_notes and D-23's authoritative directory layout, the plan path wins. Plans 06-03/07/08 will import from `@/lib/price-stream-provider`.
- **No new dependencies** - zustand was already installed in Plan 06-01 per the lockfile. No npm install needed.
- **Dual-location D-18 CLOSED handling** - `set({ status: 'disconnected' })` appears twice in price-store.ts: once in onerror when readyState === 2, and once in disconnect() after closing the EventSource. Both required; both are explicit in D-18. Not a duplicate - one reacts to involuntary CLOSED, the other commits to voluntary CLOSED.
- **Task 4 is verification-only** - no source commit. The plan gates it on tsc + build + lint + token preservation; the evidence is captured in this SUMMARY, not in a commit message.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Root `.gitignore` Python template's `lib/` rule blocked `frontend/src/lib/` tracking**

- **Found during:** Task 1 commit staging (`git status --short` showed no `frontend/src/lib/` entries even though the files existed)
- **Root cause:** The project's root `.gitignore` is the standard Python template (`__pycache__/`, `*.py[codz]`, `build/`, `dist/`, `eggs/`, `lib/`, `lib64/`, ...). The `lib/` line at `.gitignore:17` is intended for Python distutils build output (next to `build/`, `eggs/`, etc.), but git's ignore patterns apply to any matching directory name anywhere in the tree. The frontend's `src/lib/` matched and git silently excluded it. Confirmed with `git check-ignore -v frontend/src/lib/sse-types.ts` -> `.gitignore:17:lib/`.
- **Fix:** Added an exception to `.gitignore` immediately after the `lib/`/`lib64/` pair: `!frontend/src/lib/` and `!frontend/src/lib/**`. This un-ignores the Phase 06 contract directory without touching the Python build-dir intent. Verified with `git check-ignore` - files now show the negation rule (`.gitignore:21:!frontend/src/lib/**`) instead of the ignore rule.
- **Files modified:** `.gitignore` (1 line of context + 2 new lines)
- **Verification:** `git status --short` shows `frontend/src/lib/` as untracked (available to add), `git check-ignore` confirms the negation applies. Files committed successfully in `669195f`.
- **Committed in:** `669195f` (Task 1 commit - the fix ships with the files it enabled)
- **Classification:** Rule 3 (blocking issue directly caused by current task - cannot commit new files without it). Not a pre-existing issue because no Phase 1-5 Python code lives under a `lib/` path and no earlier frontend plan created a `src/lib/` directory. This deviation could have been caught in Plan 06-01 if the scaffold had tried to create `src/lib/`, but Plan 06-01's acceptance intentionally left `src/lib/` empty for Plan 06-02 (per Plan 06-01 summary "Next Phase Readiness").

### Acceptance-Criteria Regex Adaptations

- **Task 2 empty-deps regex (non-deviation, documentation note):** The acceptance criterion `grep -Eq "useEffect\(.*,\s*\[\]\s*\)"` is a single-line regex but the final RESEARCH.md template places `useEffect(` on one line and `}, []);` on another. The semantic criterion (empty deps array) is verified by `perl -0777 -ne 'exit(0) if /useEffect\(.*,\s*\[\]\s*\)/s'` (multi-line match) which passes. Not a source-code deviation - the template is the RESEARCH.md lift verbatim; only the verification regex would need to become multi-line aware. Planner note for future iteration, not a fix.

- **Task 4.4 CSS path (non-deviation, Plan 06-01 precedent):** The acceptance criterion globs `frontend/out/_next/static/css/*.css` but Turbopack 16 emits CSS under `out/_next/static/chunks/`. Plan 06-01's summary Deviation #2 already established this path convention and recommended downstream plans adopt it. Applied the `chunks/*.css` path in Task 4 verification.

---

**Total deviations:** 1 auto-fixed (Rule 3 gitignore blocker). No architectural changes. No user permission needed.
**Impact on plan:** Plan ran end-to-end in 15m 28s with zero plan-spec rework. The gitignore fix is additive and does not alter any Python build-dir exclusion semantics.

## Issues Encountered

- **Benign rewrites warning:** `npm run build` prints `Specified "rewrites" will not automatically work with "output: export"`. Documented in RESEARCH G2 and already established as benign in Plan 06-01 summary. The rewrites array is empty in production (NODE_ENV guard) so the warning is informational.
- **Node engine version mismatch (cosmetic):** Dev machine runs Node 24; package.json pins `>=20.0.0 <21`. npm emits EBADENGINE warnings during any install. Not encountered this plan because no install was performed - zustand was already in the lockfile from Plan 06-01.

## User Setup Required

None. All verification in this plan is automated (tsc, build, lint, grep). Manual `/debug` browser verification is explicitly Plan 06-03's concern per VALIDATION.md.

## Next Phase Readiness

- **Plan 06-03 (debug page + Vitest tests):** ready to start. All artifacts this plan committed are the contract Plan 06-03 depends on:
  - `usePriceStore`, `selectTick`, `selectConnectionStatus` for the /debug page subscription.
  - `__setEventSource` for MockEventSource DI in Vitest.
  - `PriceStreamProvider` already mounted in layout.tsx so /debug inherits the live EventSource on first render.
  - Plan 06-03 still needs to create `frontend/vitest.config.mts`, `frontend/vitest.setup.ts`, `frontend/src/lib/price-stream.test.ts`, and `frontend/src/app/debug/page.tsx` - none of which overlap with this plan's surface.
- **Phase 7 (frontend panels):** the store and selectors are the stable public contract. Phase 7's watchlist (FE-03), main chart, positions table, trade bar, and header dot (FE-10) will import `usePriceStore` with selectors - no new EventSource, no new state owner. D-14 session_start_price is available for FE-03's daily-change % computation without a backend change.
- **Phase 8 (AI chat + heatmap + P&L):** same contract as Phase 7 - read-only subscriptions to `usePriceStore`.

## Threat Flags

None. All surface added this plan is internal to the frontend process and reads only from the `/api/stream/prices` SSE endpoint (stable since Phase 1 APP-04). No new network endpoints, no auth paths, no file access, no schema changes. All STRIDE threats from the plan's threat_model are mitigated as specified (T-06-02-01 input validation, T-06-02-02 DoS via StrictMode, T-06-02-03 info disclosure - all encoded in the shipping code).

## TDD Gate Compliance

This plan's Task 1 and Task 2 have `tdd="true"` but the plan itself is `type: execute`, not `type: tdd`. The `<behavior>` block in Task 1 explicitly defers test authorship to Plan 06-03 with the note "Writing the store BEFORE the test is acceptable because Plan 06-03 has exhaustive spec coverage already authored in RESEARCH.md section 13." Test assertions for all 11 behaviors exist in RESEARCH.md and will be lifted verbatim into `frontend/src/lib/price-stream.test.ts` by Plan 06-03. RED gate arrives with Plan 06-03; GREEN is already satisfied by this plan's source; REFACTOR is unlikely given 22-line / 103-line module budgets.

## Self-Check: PASSED

- [x] `frontend/src/lib/sse-types.ts` exists (24 lines, budget 40)
- [x] `frontend/src/lib/price-store.ts` exists (103 lines, budget 120)
- [x] `frontend/src/lib/price-stream-provider.tsx` exists (22 lines, budget 40)
- [x] `frontend/src/app/layout.tsx` modified with PriceStreamProvider wrapping {children}
- [x] `.gitignore` modified with frontend/src/lib negation pair
- [x] `cd frontend && npx tsc --noEmit` exits 0
- [x] `cd frontend && npm run build` exits 0; `out/index.html` exists
- [x] `cd frontend && npm run lint` exits 0
- [x] All four brand hex values present in `out/_next/static/chunks/*.css`
- [x] Commit `669195f` (feat 06-02 sse-types+price-store) in `git log`
- [x] Commit `288bbf6` (feat 06-02 PriceStreamProvider) in `git log`
- [x] Commit `6f942a7` (feat 06-02 layout wire) in `git log`
- [x] No emojis in any of the three new source files, the edited layout.tsx, or any commit message

---
*Phase: 06-frontend-scaffold-sse*
*Completed: 2026-04-24*
