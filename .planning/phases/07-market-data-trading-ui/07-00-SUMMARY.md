---
phase: 07-market-data-trading-ui
plan: 00
subsystem: ui
tags: [next, react, tanstack-query, lightweight-charts, tailwind, theme-tokens]

# Dependency graph
requires:
  - phase: 06-frontend-scaffold-sse
    provides: PriceStreamProvider, usePriceStore, @theme tokens, :root force-emit, vitest harness
provides:
  - lightweight-charts@^5.2.0 prod dep installed
  - "@tanstack/react-query@^5.100.1 prod dep installed"
  - Up/down palette aligned to Lightweight Charts defaults (#26a69a / #ef5350) in @theme + :root force-emit
  - app/providers.tsx — Providers shell composing QueryClientProvider over PriceStreamProvider
  - app/layout.tsx wired to Providers (Server Component preserved)
affects:
  - 07-01 (price-store extension — uses TanStack Query alongside store)
  - 07-02 (api/portfolio + api/watchlist wrappers — consumed by useQuery)
  - 07-03..07-07 (Watchlist, MainChart, Sparkline, PositionsTable, TradeBar, Header — all rely on these foundations)
  - 08 (chat panel — will reuse Providers shell)

# Tech tracking
tech-stack:
  added:
    - lightweight-charts ^5.2.0
    - "@tanstack/react-query ^5.100.1"
  patterns:
    - "Root client provider via useState-init singleton (StrictMode-safe QueryClient)"
    - "Server Component layout.tsx + single client boundary at providers.tsx"
    - "Theme token alignment: @theme + :root force-emit in lockstep"

key-files:
  created:
    - frontend/src/app/providers.tsx
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/app/globals.css
    - frontend/src/app/layout.tsx

key-decisions:
  - "Adopt Lightweight Charts default palette (#26a69a / #ef5350) per CONTEXT.md D-02 — visually cohesive across flash, sparkline, P&L text, main chart line"
  - "useState-init singleton for QueryClient — StrictMode-safe without useEffect lifecycle"
  - "Compose QueryClientProvider OUTSIDE PriceStreamProvider so SSE consumers can also access query cache"
  - "layout.tsx remains a Server Component; only providers.tsx carries 'use client'"

patterns-established:
  - "Pattern: Single Providers shell at app/providers.tsx — future cross-cutting providers (e.g., chat) compose here"
  - "Pattern: When extending @theme tokens, mirror the change in the :root force-emit block to defeat Tailwind v4 tree-shaking"

requirements-completed: []

# Metrics
duration: 19m
completed: 2026-04-25
---

# Phase 7 Plan 00: Foundations Summary

**Phase 7 dependency + theme + provider foundation: lightweight-charts + @tanstack/react-query installed, up/down palette aligned to Lightweight Charts defaults in both @theme and :root, and a Providers shell composing QueryClientProvider over the existing PriceStreamProvider.**

## Performance

- **Duration:** 19m 4s
- **Started:** 2026-04-25T04:21:00Z
- **Completed:** 2026-04-25T04:40:04Z
- **Tasks:** 4
- **Files modified:** 4 (1 created, 3 modified — package-lock.json counted with package.json)

## Accomplishments

- Installed `lightweight-charts@^5.2.0` and `@tanstack/react-query@^5.100.1` as prod deps (no devtools, no Recharts, no Framer Motion — matches CONTEXT.md scope)
- Aligned `--color-up` to `#26a69a` and `--color-down` to `#ef5350` in BOTH the `@theme` block and the `:root` force-emit block (CONTEXT.md D-02)
- Created `frontend/src/app/providers.tsx` — `'use client'` named export composing `<QueryClientProvider>` over `<PriceStreamProvider>` with a useState-init QueryClient singleton (staleTime 10s, refetchOnWindowFocus false)
- Wired `<Providers>` into `app/layout.tsx` while preserving its Server Component status

## Task Commits

Each task was committed atomically:

1. **Task 1: Install lightweight-charts + @tanstack/react-query** — `2be3c40` (chore)
2. **Task 2: Align up/down palette to D-02 values in globals.css** — `02a2b81` (style)
3. **Task 3: Create providers.tsx and wire it into layout.tsx** — `fbb1cb8` (feat)
4. **Task 4: Wave merge gate — tests + build** — no file changes (verification gate only)

## Files Created/Modified

- `frontend/package.json` — Added two prod deps in `"dependencies"` (no devDependency leakage)
- `frontend/package-lock.json` — 471 transitive packages added (npm install lockfile delta)
- `frontend/src/app/globals.css` — `--color-up` and `--color-down` set to `#26a69a` / `#ef5350` in both `@theme` and `:root` blocks
- `frontend/src/app/providers.tsx` — NEW: `Providers` client component (33 lines, ≤120 budget)
- `frontend/src/app/layout.tsx` — Replaced `PriceStreamProvider` direct wrapper with `Providers`; import path now `./providers`

## Versions Installed (verbatim from package.json)

| Package | Range | Notes |
| --- | --- | --- |
| `lightweight-charts` | `^5.2.0` | Sparklines + main chart canvas (Phase 7 use only) |
| `@tanstack/react-query` | `^5.100.1` | `/api/portfolio` GET + `/api/portfolio/trade` mutation |

## Theme Verification (post-build)

Compiled CSS bundle: `frontend/out/_next/static/chunks/0qte9hl9bgo0w.css`

| Token | Value | In @theme | In :root | In compiled CSS | Old hex absent |
| --- | --- | --- | --- | --- | --- |
| `--color-up` | `#26a69a` | yes | yes | yes | `#3fb950` removed |
| `--color-down` | `#ef5350` | yes | yes | yes | `#f85149` removed |

The `grep` count for each new hex in `globals.css` is exactly 2 (one per block). The build asserts the new values appear in the compiled CSS bundle and the old values do not.

## Providers Shell Confirmation

- `'use client'` directive at line 1 of `providers.tsx`
- Named export only — `export function Providers(...)`. No default export.
- `useState(() => new QueryClient({ defaultOptions: { queries: { staleTime: 10_000, refetchOnWindowFocus: false } } }))` — StrictMode-safe singleton
- Composition order: `<QueryClientProvider client={queryClient}><PriceStreamProvider>{children}</PriceStreamProvider></QueryClientProvider>`
- `app/layout.tsx` is unchanged in shape: still a Server Component, no `'use client'` directive, `<html className="dark">` and `<body className="bg-surface text-foreground">` preserved

## Build / Test Output

- `npm run test:ci` — exit code 0; **8/8** Phase 06 tests pass (`price-stream.test.ts`); duration 1.69s
- `npm run build` — exit code 0; static export to `frontend/out/`; benign rewrites + output:export warning per Phase 06 RESEARCH G2 (ignored)

## Decisions Made

- **D-02 hex pair adopted exactly** — `#26a69a` (teal) / `#ef5350` (coral). These are the Lightweight Charts default series colors, so the same palette will drive flash, sparkline stroke, main chart line, P&L text. One palette, four surfaces — no theme drift later.
- **QueryClient defaults: staleTime 10s, refetchOnWindowFocus false** — matches RESEARCH §2 Pattern 5. Phase 7 portfolio endpoint pairs this with explicit 15s `refetchInterval` on the consuming `useQuery` calls (per CONTEXT.md "Claude's Discretion — Portfolio data flow").
- **Provider order: Query OUTSIDE Stream** — descendants subscribed to either the Zustand store or `useQuery` get the right context. Reversing the order would force `PriceStreamProvider` itself to depend on `QueryClient`, which it does not.

## Deviations from Plan

None — plan executed exactly as written.

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

- npm engine warning: project declares `"engines": { "node": ">=20.0.0 <21" }` but the local environment runs Node 24. This is a pre-existing config from Phase 06 (out of scope for this plan, deferred). No build or test impact.

## Threat Flags

None — no new endpoints, auth paths, file I/O, schema changes, or environment variables introduced by this plan. T-07-05 (build-output information disclosure) is `accept` per the plan's threat model and remains so: the two new packages are first-party TradingView/TanStack libraries fetched from npm with `package-lock.json` committed.

## Self-Check

- `frontend/package.json` — FOUND
- `frontend/src/app/globals.css` — FOUND
- `frontend/src/app/providers.tsx` — FOUND
- `frontend/src/app/layout.tsx` — FOUND
- Commit `2be3c40` — FOUND in `git log`
- Commit `02a2b81` — FOUND in `git log`
- Commit `fbb1cb8` — FOUND in `git log`

## Self-Check: PASSED

## Next Phase Readiness

- Plans 07-01 through 07-07 may now `import { useQuery, useMutation } from '@tanstack/react-query'` and `import { createChart, LineSeries } from 'lightweight-charts'` without further setup.
- The new up/down tokens are bundle-ready: any component using `text-up`, `text-down`, `bg-up/10`, `bg-down/10`, etc., will resolve to the locked D-02 hex values.
- The Providers shell is the single client boundary for cross-cutting state. Phase 8's chat panel can compose into it without touching `layout.tsx` again.

---
*Phase: 07-market-data-trading-ui*
*Completed: 2026-04-25*
