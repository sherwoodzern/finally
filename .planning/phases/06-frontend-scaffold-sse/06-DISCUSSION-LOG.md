# Phase 6: Frontend Scaffold & SSE - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 06-frontend-scaffold-sse
**Mode:** `--auto` (all gray areas auto-selected, recommended options auto-picked)
**Areas discussed:** Scaffolding & tooling, Static export & dev proxy, Theme & styling, SSE client & price store, Verification, Directory layout, Dependency budget

---

## Scaffolding & Tooling

| Option | Description | Selected |
|--------|-------------|----------|
| `create-next-app` TypeScript + Tailwind + App Router + `src/` + ESLint (**recommended**) | One-command scaffold, current defaults, matches Phase 9 Node 20 Docker stage | ✓ |
| Manual hand-rolled scaffold | Full control, zero unused files, but re-invents what the CLI gives for free | |
| `create-next-app` Pages Router | Legacy, complicates static export + root client provider pattern | |

**User's choice:** `create-next-app` TypeScript + Tailwind + App Router (`--typescript --tailwind --app --eslint --src-dir --use-npm`).
**Notes:** Auto-selected recommended option. Delivers D-01.

| Option | Description | Selected |
|--------|-------------|----------|
| `npm` + committed `package-lock.json` + Node `>=20 <21` in `engines` (**recommended**) | Matches PLAN.md §11 "Node 20 slim" image; fails fast on old Node | ✓ |
| `pnpm` | Faster installs, stricter dep graph, but adds a lockfile format the Docker stage doesn't expect | |
| `yarn` classic | Legacy, no real win | |

**User's choice:** `npm` with `engines.node` pin.
**Notes:** Auto-selected recommended option. Delivers D-02. Avoids mixing lockfiles with Phase 9's Dockerfile.

| Option | Description | Selected |
|--------|-------------|----------|
| ESLint only (create-next-app default), no Prettier (**recommended**) | No scope creep, matches PROJECT.md "no over-engineering" | ✓ |
| ESLint + Prettier + `.prettierrc` | Ergonomic but not a Phase 6 requirement | |

**User's choice:** ESLint only.
**Notes:** Auto-selected recommended. Delivers D-03.

---

## Static Export & Dev Proxy

| Option | Description | Selected |
|--------|-------------|----------|
| `next.config.mjs` with `output: 'export'`, `images.unoptimized: true`, `trailingSlash: true` (**recommended**) | Required for static export; smooth interop with FastAPI's `StaticFiles` mount in Phase 8 | ✓ |
| `output: 'export'` only, defaults elsewhere | Breaks when any `<Image>` is used; less predictable `/about/` vs `/about` serving | |

**User's choice:** Full config (`output: 'export'` + `images.unoptimized` + `trailingSlash`).
**Notes:** Auto-selected recommended. Delivers D-05, D-06.

| Option | Description | Selected |
|--------|-------------|----------|
| Dev-only `next.config.mjs` `rewrites()` for `/api/*` and `/api/stream/*` → `http://localhost:8000` (**recommended**) | Same-origin in all environments; no CORS, no conditional URL code | ✓ |
| Hardcoded `http://localhost:8000` in fetch/EventSource | Breaks prod (static files served by FastAPI on same origin) | |
| Enable CORS on the backend | Violates PLAN.md §3 "no CORS configuration"; adds server complexity | |

**User's choice:** Dev-only rewrites to localhost:8000.
**Notes:** Auto-selected recommended. Delivers D-07, D-08.

---

## Theme & Styling

| Option | Description | Selected |
|--------|-------------|----------|
| Tailwind theme tokens + CSS variables together (**recommended**) | One palette reused by utility classes and runtime-styled components (flash anim, heatmap) | ✓ |
| Tailwind tokens only | Loses runtime re-theming; slightly worse for Phase 7 flash animation colors | |
| CSS variables only, vanilla classes | Drops Tailwind utilities that make layout cheap | |

**User's choice:** Tokens + CSS variables together.
**Notes:** Auto-selected recommended. Delivers D-09.

| Option | Description | Selected |
|--------|-------------|----------|
| Permanent `dark` class on `<html>` (**recommended**) | PROJECT.md specifies dark theme; no light-mode scope | ✓ |
| Toggleable light/dark | Scope creep (not in FE-01) | |

**User's choice:** Permanent dark.
**Notes:** Auto-selected recommended. Delivers D-10.

---

## SSE Client & Price Store

| Option | Description | Selected |
|--------|-------------|----------|
| Root-level client provider owning `EventSource` lifecycle (**recommended**) | One connection per app lifetime; testable; Phase 7/8 components are pure subscribers | ✓ |
| Module-level singleton that auto-connects on import | Breaks SSR; hard to test; double-runs under StrictMode | |
| Per-hook-instance connection | Duplicates streams when multiple panels subscribe | |

**User's choice:** Root-level client provider.
**Notes:** Auto-selected recommended. Delivers D-11, D-15.

| Option | Description | Selected |
|--------|-------------|----------|
| Zustand (**recommended**) | ~1 KB, selector-based subscriptions, proven pattern for streaming stores | ✓ |
| `useSyncExternalStore` + handwritten store | No extra dep, but re-invents selector ergonomics Zustand already provides | |
| React Context + `useReducer` | Re-renders every subscriber on every tick; unacceptable at 500 ms × N tickers | |
| TanStack Query | Built for request/response, not streaming push | |

**User's choice:** Zustand.
**Notes:** Auto-selected recommended. Delivers D-12. `useSyncExternalStore` was the closest runner-up.

| Option | Description | Selected |
|--------|-------------|----------|
| `session_start_price` computed frontend-side (first price seen per ticker) (**recommended**) | No backend change; keeps Phase 6 frontend-only; conservative reading of PLAN.md §6 | ✓ |
| Extend backend `PriceUpdate` to emit `session_start_price` | Correct long-term but out of Phase 6 scope; touches `cache.py` + `models.py` + SSE shape | |

**User's choice:** Frontend-side computation.
**Notes:** Auto-selected recommended. Delivers D-14. Backend extension captured in Deferred Ideas.

| Option | Description | Selected |
|--------|-------------|----------|
| Connection status in the same store (`connected | reconnecting | disconnected`) driven by `EventSource` events (**recommended**) | Phase 7 header dot (FE-10) reads this verbatim; no second state surface | ✓ |
| Separate hook + state for connection status | Duplicates bookkeeping; two places to keep in sync | |
| Don't track it in Phase 6 at all | Phase 7 would need a follow-up edit to the store | |

**User's choice:** Track in the same store.
**Notes:** Auto-selected recommended. Delivers D-18.

| Option | Description | Selected |
|--------|-------------|----------|
| Relative `/api/stream/prices` URL (same-origin in all envs) (**recommended**) | Works in dev via rewrite and in prod via FastAPI `StaticFiles` mount | ✓ |
| `NEXT_PUBLIC_API_URL` env var | Extra configuration surface; unnecessary for same-origin setup | |

**User's choice:** Relative URL.
**Notes:** Auto-selected recommended. Delivers D-16.

| Option | Description | Selected |
|--------|-------------|----------|
| Try/catch around JSON.parse + ingest; `console.warn` malformed; do not rethrow (**recommended**) | Matches backend's narrow log-and-continue pattern; EventSource stays alive | ✓ |
| Crash on malformed payload | Kills stream for one bad frame; bad UX | |
| Silently swallow | Hides real bugs | |

**User's choice:** Narrow try/catch with warn.
**Notes:** Auto-selected recommended. Delivers D-19.

---

## Verification

| Option | Description | Selected |
|--------|-------------|----------|
| `/debug` page + Vitest + MockEventSource test (both) (**recommended**) | Satisfies success criterion #3 (real wire) AND #4 (pure-logic); minimal extra effort | ✓ |
| Debug page only | No regression coverage; Phase 7/8 could break the store silently | |
| Vitest test only | Doesn't prove the real wire works against a running backend | |

**User's choice:** Both.
**Notes:** Auto-selected recommended. Delivers D-20, D-21.

| Option | Description | Selected |
|--------|-------------|----------|
| Vitest (**recommended**) | Current Next.js 15 default for unit/component tests; smallest config surface | ✓ |
| Jest + `next/jest` | More config; feels heavier than the problem needs | |

**User's choice:** Vitest.
**Notes:** Auto-selected recommended. Delivers D-21 tooling.

---

## Directory Layout

| Option | Description | Selected |
|--------|-------------|----------|
| `src/app`, `src/lib`, `src/components` tree (**recommended**) | Matches `--src-dir` scaffold; `lib/` houses the price store cleanly | ✓ |
| Flat `app/`, `components/`, `lib/` at `frontend/` root | Pollutes project root with source dirs next to config files | |

**User's choice:** `src/`-based layout.
**Notes:** Auto-selected recommended. Delivers D-23.

---

## Dependency Budget

| Option | Description | Selected |
|--------|-------------|----------|
| Add `zustand` only (plus Vitest toolchain as dev deps) (**recommended**) | Minimum footprint; chart libraries come in Phase 7/8 | ✓ |
| Also pre-install `lightweight-charts` and `recharts` | Pollutes dep tree before they're needed | |

**User's choice:** `zustand` + Vitest toolchain only.
**Notes:** Auto-selected recommended. Delivers D-24.

---

## Claude's Discretion

Captured in CONTEXT.md `<decisions>` under "Claude's Discretion". Summary:
- Exact Tailwind token names (rename for readability as panels land).
- Zustand boilerplate style (plain `create()` unless state grows).
- `PriceStreamProvider` placement (outermost so `/debug` sees it).
- `MockEventSource` implementation (handwritten preferred).
- Debug page polish (unstyled table is fine).
- Exact neutral-scale CSS variable values (pick coherent ramp).
- `package.json` scripts (`dev`, `build`, `start`, `lint`, `test`, `test:ci`).

---

## Deferred Ideas

Captured in CONTEXT.md `<deferred>`. Summary:
- Backend-emitted `session_start_price` in SSE.
- SSE heartbeat / keepalive from backend.
- Phase 7 header connection-status dot UI.
- Lightweight Charts, Recharts, sparklines, heatmap, P&L chart (Phase 7/8).
- Prettier config.
- Playwright E2E for SSE reconnect (Phase 10).
- Multi-tab `EventSource` deduplication.
- Service-worker offline fallback.
- Automated type-sharing between backend Pydantic and frontend TypeScript.
