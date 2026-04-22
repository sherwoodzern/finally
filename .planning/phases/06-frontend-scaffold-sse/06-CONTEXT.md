# Phase 6: Frontend Scaffold & SSE - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up a self-contained Next.js TypeScript project under `frontend/`,
configured for `output: 'export'`, wired with Tailwind CSS and the project's
dark theme + accent colors, and wire a single long-lived `EventSource`
client to `/api/stream/prices` that feeds a ticker-keyed in-memory price
store downstream components can subscribe to. `npm run build` must
produce a zero-error static export under `frontend/out/`. A real browser
loading the app against a running backend must see its store populated
by the live SSE stream, and that store must be verifiable both by a
simple debug page (real wire) and by a component/hook test against a
mock `EventSource` (pure-logic).

**In scope (FE-01, FE-02):**
- `frontend/` as an `npm`-managed Next.js 15 TypeScript project using the
  App Router, configured with `output: 'export'` and Tailwind CSS.
- Tailwind config extended with the dark-theme palette + accent tokens
  (yellow `#ecad0a`, blue `#209dd7`, purple `#753991`) and CSS variables
  for runtime theming (background, foreground, border, muted, accents).
- `next.config.mjs` dev-only `rewrites()` proxying `/api/*` and
  `/api/stream/*` to `http://localhost:8000` so dev is same-origin
  against the dev browser (prod is already same-origin via Phase 8's
  `StaticFiles` mount).
- SSE price-store module (e.g. `src/lib/price-store.ts`) owning one
  `EventSource` at application load, parsing `data:` frames from
  `backend/app/market/stream.py` (the all-tickers-per-event shape), and
  updating a ticker-keyed state surface.
- Connection-status surface (`connected | reconnecting | disconnected`)
  exposed from the same store for Phase 7's header dot to consume later.
- Root-level client provider component that mounts the `EventSource`
  lifecycle exactly once for the app lifetime.
- `/debug` route rendering the live store contents in a minimal table so
  Phase 6 can be validated in a real browser against a live backend.
- Hook/component test (Vitest + Testing Library + a mock
  `EventSource` double) exercising the store against synthetic events
  — no live network call, no backend required.
- Minimal `frontend/README.md` covering `npm install`, `npm run dev`
  (against `uvicorn` on 8000), `npm run build`, and the one-line proxy
  rewrite in dev.

**Out of scope (belongs to later phases):**
- Watchlist panel, sparklines, main chart, positions table, trade bar,
  header live totals, connection-status dot UI → Phase 7
  (FE-03, FE-04, FE-07, FE-08, FE-10).
- Portfolio heatmap, P&L line chart, AI chat panel, demo polish,
  frontend component tests for trading UI → Phase 8 (FE-05, FE-06,
  FE-09, FE-11, TEST-02).
- FastAPI `StaticFiles` mount of the built export at `/` → Phase 8
  (APP-02).
- Dockerfile's Node 20 build stage that copies `frontend/out/` into the
  Python image → Phase 9 (OPS-01).
- Playwright E2E against the built image → Phase 10 (TEST-04).
- Real data fetching from `/api/portfolio`, `/api/watchlist`,
  `/api/chat` — Phase 6 only wires SSE; REST calls arrive with the
  panels that consume them in Phases 7–8.
- Backend changes. The SSE event shape emitted today by
  `backend/app/market/stream.py` (`data: {TICKER: {ticker, price,
  previous_price, timestamp, change, change_percent, direction}}`) is
  treated as the stable contract for Phase 6 — no backend extension to
  emit `session_start_price`.

</domain>

<decisions>
## Implementation Decisions

### Project Scaffolding & Tooling

- **D-01:** `frontend/` is created by `npx create-next-app@latest frontend
  --typescript --tailwind --app --eslint --src-dir --no-import-alias=false
  --use-npm`. This matches the PLAN.md §11 "Node 20 slim" Docker stage,
  delivers the current Next.js + Tailwind + TypeScript + App Router
  defaults in one command, and uses `src/` which keeps `app/`, `lib/`,
  and `components/` cleanly separated from config files at the
  `frontend/` root. Post-scaffold edits are additive: `next.config.mjs`,
  `tailwind.config.ts`, `src/app/globals.css`, and the price-store +
  debug-page + test files.

- **D-02:** Package manager is `npm` (with the committed
  `frontend/package-lock.json`), Node version pin is `>=20.0.0 <21`
  declared under `engines` in `frontend/package.json`. Rationale: PLAN.md
  §11 specifies `Node 20 slim` for the builder image; pinning `engines`
  fails fast if a contributor is on an older Node, and aligning with
  `npm` avoids mixing lockfiles with Phase 9's Dockerfile.

- **D-03:** ESLint uses the `create-next-app` default config (no custom
  rules added in Phase 6). Prettier is **not** added in Phase 6 —
  `create-next-app` does not include it, and adding it now is scope
  creep for the scaffold phase. If Phase 7 or 8 wants it, add then.

- **D-04:** Next.js App Router (not Pages Router). App Router is the
  current default and what `--app` lands; Pages is legacy and would
  complicate `output: 'export'` + layouts + the root client provider
  pattern (D-11) that the rest of the frontend builds on.

### Static Export & Dev Proxy

- **D-05:** `next.config.mjs` sets `output: 'export'` at the top level.
  `npm run build` must produce `frontend/out/` with zero type errors and
  zero build errors — this is success criterion #2 and the gate Phase 9
  consumes when it copies `frontend/out/` into `static/` inside the
  Python image.

- **D-06:** `next.config.mjs` also declares `images: { unoptimized: true }`
  (required for `output: 'export'` when any `<Image>` is ever used) and
  `trailingSlash: true` (standard for static exports; FastAPI's
  `StaticFiles` serves `about/index.html` for `/about/` predictably).

- **D-07:** **Dev-only proxy via `async rewrites()`** in
  `next.config.mjs`, guarded by `if (process.env.NODE_ENV === 'development')`,
  forwarding `/api/:path*` and `/api/stream/:path*` to
  `http://localhost:8000`. Rationale: static exports have no server-side
  proxy, but the dev server does — this keeps `EventSource('/api/stream/prices')`
  a same-origin relative URL in every environment (dev proxies it, prod
  serves it from the same FastAPI process via Phase 8 APP-02). No
  `NEXT_PUBLIC_API_URL`, no `CORS`, no cross-origin `EventSource`.
  Rejected: hardcoded `http://localhost:8000` in fetch calls (breaks
  prod), enabling CORS on the backend (PLAN.md §3 "no CORS
  configuration").

- **D-08:** `rewrites()` returns an array with two entries — one for
  `/api/:path*` (REST endpoints used from Phase 7 onward) and one for
  `/api/stream/:path*` (SSE). Next.js rewrites preserve `text/event-stream`
  content-type and streaming — no buffering — which is the piece that
  makes `EventSource` work at all in dev.

### Theme & Styling

- **D-09:** **Tailwind v4 theme tokens AND CSS variables together.**
  `src/app/globals.css` defines CSS custom properties (`--bg`,
  `--foreground`, `--border`, `--muted`, `--accent-yellow`,
  `--accent-blue`, `--accent-purple`) at `:root`. `tailwind.config.ts`
  extends `theme.colors` to reference those variables
  (e.g. `bg: 'rgb(var(--bg) / <alpha-value>)'`) so Tailwind utilities
  pick them up. Exact values match PLAN.md §2:
  - Background: `#0d1117` (PLAN's primary option) with `#1a1a2e` kept as
    an opt-in variant via a `bg-surface-alt` token. No pure black.
  - Muted gray borders: a mid-gray like `#30363d` (PLAN's "muted gray
    borders") — not Tailwind's `neutral-800`.
  - Accent yellow: `#ecad0a`; accent blue: `#209dd7`; accent purple:
    `#753991` (submit buttons, per PLAN.md §2).
  Rationale: variables mean Phase 7's sparkline/flash animations and
  Phase 8's heatmap colors can reference one palette; Tailwind classes
  stay ergonomic.

- **D-10:** `dark` class on `<html>` is **permanently set in the root
  layout** (`src/app/layout.tsx`) — no light/dark toggle in v1.
  PROJECT.md says "Dark theme"; PLAN.md §2 says "Dark, data-rich trading
  terminal aesthetic". Mirror that by hardcoding `className="dark"` on
  `<html>` and styling against `dark:` variants (or just base styles
  given the permanent dark class — planner's choice).

### SSE Client & Price Store

- **D-11:** **Root-level client provider** owns the SSE lifecycle.
  `src/lib/price-stream-provider.tsx` is a `'use client'` component
  rendered inside `src/app/layout.tsx` wrapping `{children}`. It calls
  the store's `connect()` on mount and `disconnect()` on unmount.
  Rationale: one connection per app lifetime; hooks called in arbitrary
  components never create duplicate connections; Phase 7/8 consumers
  are pure subscribers.
  Rejected: module-level singleton that auto-connects on import (breaks
  SSR + makes testing hard), per-hook-instance connections (duplicates
  the stream when multiple components subscribe).

- **D-12:** **State store is Zustand** (`zustand` npm dep). Rationale:
  - Tiny runtime (~1 KB gzipped), selector-based subscriptions so a
    component reading `AAPL` doesn't re-render when `GOOGL` ticks.
  - No React context ceremony, works fine under App Router's
    `'use client'` boundary.
  - Battle-tested for this exact pattern (external data stream →
    ticker-keyed state → selector-based components).
  Alternative considered: `useSyncExternalStore` with a custom external
  store. Workable but hand-rolls the selector/shallow-compare layer
  Zustand already provides. Phase 6's "stable contract for panels" goal
  is better served by the library.
  Alternative rejected: React Context + `useReducer` — re-renders every
  subscriber on every tick, unacceptable at ~500 ms cadence × N tickers.
  Alternative rejected: TanStack Query — optimized for request/response,
  not streaming push.

- **D-13:** **Store shape** (canonical for Phase 6; Phase 7 extends
  it for selected-ticker, watchlist panel, etc.):
  ```ts
  type Direction = 'up' | 'down' | 'flat';

  interface Tick {
    ticker: string;
    price: number;
    previous_price: number;
    timestamp: number;          // unix seconds (from SSE)
    change: number;
    change_percent: number;     // between-ticks %
    direction: Direction;
    session_start_price: number; // set once per ticker, client-side
  }

  type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

  interface PriceStoreState {
    prices: Record<string, Tick>;
    status: ConnectionStatus;
    lastEventAt: number | null;  // epoch ms
    connect: () => void;
    disconnect: () => void;
    ingest: (payload: Record<string, RawPayload>) => void;  // exposed for tests
    reset: () => void;           // exposed for tests
  }
  ```
  `RawPayload` is the backend's emitted dict per ticker (from
  `PriceUpdate.to_dict()` in `backend/app/market/models.py:39-49`).

- **D-14:** **`session_start_price` is computed on the frontend** —
  the first time a ticker appears in the stream since page load, the
  frontend captures `payload.price` into `session_start_price` and
  never overwrites it for the duration of the page view. Rationale:
  the backend's `PriceUpdate` dataclass (`backend/app/market/models.py`)
  does not expose a `session_start_price`; extending the SSE shape is
  a backend change that belongs outside Phase 6 (Phase 7 will also
  not touch the backend — the session-start value only drives display).
  PLAN.md §6 explicitly says "since the backend process started
  tracking this ticker" — frontend-since-page-load is a strictly
  conservative reading (page load ≥ process start). Phase 7's
  watchlist panel will read `session_start_price` from this store to
  compute its daily-change % (FE-03).
  Accepted tradeoff: a hard browser reload resets `session_start_price`
  without resetting the backend process, so daily-change % restarts
  at 0 on refresh. For a demo session this is acceptable.

- **D-15:** **Single `EventSource` instance**, stored as a module-level
  variable captured by `connect()`. Closing happens in `disconnect()`.
  `connect()` is idempotent: if an `EventSource` already exists with
  `readyState !== 2`, it is a no-op. This protects against strict-mode
  double-invocation in dev.

- **D-16:** **SSE endpoint URL is the relative path `/api/stream/prices`**
  (same-origin). Dev routes via the D-07 rewrite; prod routes via the
  Phase 8 `StaticFiles` mount. No `NEXT_PUBLIC_*` env var, no
  absolute URL.

- **D-17:** **Event parsing** — `EventSource.onmessage` receives a
  message whose `data` is a JSON string matching
  `backend/app/market/stream.py` line 88 (`f"data: {payload}\n\n"`
  where `payload = json.dumps(data)` and `data` is
  `{ticker: update.to_dict() for ticker, update in prices.items()}`).
  Parse with `JSON.parse(event.data)`, iterate entries, merge each into
  `prices[ticker]`. When a ticker appears for the first time, set
  `session_start_price = payload.price` (D-14). Set
  `status = 'connected'` on the first successful parse. Update
  `lastEventAt` on every parse.

- **D-18:** **Connection-status state machine** driven by
  `EventSource` lifecycle:
  - `onopen` → `status = 'connected'`.
  - `onerror` with `readyState === EventSource.CONNECTING` (the browser
    is auto-reconnecting per `retry: 1000` in
    `backend/app/market/stream.py:67`) → `status = 'reconnecting'`.
  - `onerror` with `readyState === EventSource.CLOSED` → `status =
    'disconnected'` (browser gave up).
  - `disconnect()` (explicit unmount) → `status = 'disconnected'`,
    skip dispatch if unmount was expected.
  - Initial state before `connect()` → `status = 'disconnected'`.
  Rationale: matches the native `EventSource` state machine; Phase 7
  FE-10 (the connection dot) reads this verbatim.

- **D-19:** **Malformed payloads are logged and dropped** — wrap the
  `JSON.parse` + `ingest` step in a single `try/catch`, `console.warn`
  the error with the raw `event.data`, but do NOT rethrow (would crash
  the `EventSource`). Per-ticker entries that fail shape validation
  (missing `ticker`, missing `price`) are skipped; the rest of the
  batch still ingests. Matches backend's "narrow, log-and-continue"
  pattern from `CONVENTIONS.md`.

### Verification

- **D-20:** **Debug page at `/debug`** — `src/app/debug/page.tsx` (a
  client component) renders the store contents as a minimal table:
  one row per ticker with price, previous_price, change, change %,
  direction, session_start_price, last tick timestamp, and a header
  showing the connection status. No styling beyond dark-theme
  defaults. Satisfies success criterion #3 (real-browser wire check)
  and can be removed or kept as a hidden developer tool after Phase 7.

- **D-21:** **Unit/component test** — `src/lib/price-stream.test.ts`
  (or `.test.tsx`) using **Vitest + @testing-library/react**. Create
  a `MockEventSource` double that mirrors the minimal interface
  (`onopen`, `onerror`, `onmessage`, `readyState`, `close`) and
  inject it into the store. Cover:
  - First event sets `session_start_price` per ticker.
  - Subsequent events update `price`, `previous_price`, `change`,
    `direction`, but do **not** overwrite `session_start_price`.
  - `onopen` → `status = 'connected'`.
  - `onerror` CONNECTING → `status = 'reconnecting'`.
  - `onerror` CLOSED → `status = 'disconnected'`.
  - Selector-based subscribe only re-renders when the subscribed
    ticker changes.
  Satisfies success criterion #4. Vitest is preferred over Jest
  because it's the current Next.js 15 + Vite-testing default and has
  the smallest config surface — less yak-shaving than Jest with
  `next/jest`.

- **D-22:** **No Playwright in Phase 6.** TEST-03 / TEST-04 are
  Phase 10. Phase 6's browser check is the manual `npm run dev`
  against a running `uvicorn` backend, plus the `/debug` page.

### Directory Layout (final)

- **D-23:** After Phase 6 completes:
  ```
  frontend/
  ├── package.json
  ├── package-lock.json
  ├── tsconfig.json
  ├── next.config.mjs              # output: export, images.unoptimized,
  │                                # trailingSlash, dev rewrites
  ├── next-env.d.ts
  ├── tailwind.config.ts           # extends with project palette
  ├── postcss.config.mjs
  ├── .eslintrc.json               # create-next-app default
  ├── .gitignore                   # create-next-app default (.next, node_modules, out)
  ├── README.md                    # dev/build quick-start
  ├── public/                      # create-next-app default static assets
  └── src/
      ├── app/
      │   ├── layout.tsx           # dark root, mounts PriceStreamProvider
      │   ├── page.tsx             # minimal landing page (placeholder)
      │   ├── globals.css          # CSS vars + Tailwind directives
      │   └── debug/
      │       └── page.tsx         # live store dump (D-20)
      ├── lib/
      │   ├── price-store.ts       # Zustand store + connect/disconnect
      │   ├── price-stream-provider.tsx # mounts EventSource lifecycle
      │   ├── sse-types.ts         # Tick, RawPayload, ConnectionStatus
      │   └── price-stream.test.ts # Vitest + MockEventSource
      └── components/              # (empty in Phase 6; populated in 7/8)
  ```
  This layout matches PLAN.md §4 ("`frontend/` is a self-contained
  Next.js project") and Phase 7/8's expectations without prescribing
  their internal structure.

### Dependency Budget

- **D-24:** Phase 6 adds exactly these production deps beyond
  `create-next-app` defaults:
  - `zustand` (store, D-12).
  Dev deps beyond `create-next-app` defaults:
  - `vitest`, `@vitest/coverage-v8`, `@vitejs/plugin-react`,
    `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`.
  Lightweight Charts, Recharts, and any chart library come in Phase 7
  and Phase 8 — NOT in Phase 6.

### Claude's Discretion

Planner may pick the conventional answer without re-asking.

- **Exact Tailwind token names.** `bg-surface`, `bg-surface-alt`,
  `border-muted`, `text-foreground`, `accent-yellow`, `accent-blue`,
  `accent-purple` is a reasonable starting set; rename as it reads
  better against the Phase 7 panel components.
- **Zustand boilerplate style.** `create()` with a plain state object
  vs `create()(devtools(immer(...)))` vs a slice-per-concern pattern
  — the store is small enough that plain `create()` is the default;
  split if Phase 7/8 needs more state.
- **`PriceStreamProvider` placement.** Either directly in
  `layout.tsx` body or wrapping `{children}`. Either works; place it
  outermost so `/debug` sees it.
- **`MockEventSource` implementation.** Either a tiny handwritten
  class or the `eventsourcemock` npm package. Handwritten is simpler
  and avoids a dep; PLAN.md constraint "no over-engineering" backs
  that.
- **Debug page polish.** Minimal unstyled table is fine; the goal is
  to prove the wire, not a product.
- **Exact CSS variable color values for muted/border.** PLAN.md §2
  gives exact accent values but only gestures at the neutral palette
  ("muted gray borders", "around `#0d1117` or `#1a1a2e`"). Pick one
  coherent ramp (e.g. a 50–900 neutral scale in CSS variables); keep
  it consistent with Phase 7's watchlist rows and Phase 8's heatmap.
- **`package.json` scripts.** Keep `dev`, `build`, `start`, `lint`
  from `create-next-app`; add `test` and `test:ci` (Vitest). No
  others.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification (the source of truth)
- `planning/PLAN.md` §2 — Visual design (dark theme, `#0d1117` /
  `#1a1a2e`, muted gray borders, no pure black), color scheme (accent
  yellow `#ecad0a`, blue `#209dd7`, purple `#753991`). Backs D-09.
- `planning/PLAN.md` §3 — Architecture (single container, static
  Next.js export served by FastAPI, single origin, no CORS). Backs
  D-05, D-07, D-16.
- `planning/PLAN.md` §4 — Directory structure: `frontend/` as a
  self-contained Next.js project. Backs D-23.
- `planning/PLAN.md` §6 — SSE contract (endpoint path, ~500 ms
  cadence, event shape, "daily change %" computed from
  session-start price). Backs D-13, D-14, D-17.
- `planning/PLAN.md` §10 — Frontend design notes (EventSource, chart
  library selection for later phases). Confirms Phase 6 delivers only
  the SSE wiring + store, not charts. Backs "out of scope" list.
- `planning/PLAN.md` §11 — Multi-stage Dockerfile (Node 20 → Python
  3.12 slim). Backs D-01, D-02.

### Project planning
- `.planning/REQUIREMENTS.md` — FE-01, FE-02 (the two requirements
  this phase delivers).
- `.planning/ROADMAP.md` — Phase 6 "Success Criteria" (all four must
  evaluate TRUE: static export with dark theme + accents, zero-error
  `npm run build`, single `EventSource` updating ticker-keyed store,
  store contents match backend emissions).
- `.planning/PROJECT.md` — Constraints (frontend tech stack: Next.js
  TS `output: 'export'`, Tailwind, Lightweight Charts, Recharts —
  but only Next.js + Tailwind land in this phase). Backs D-04, D-05,
  D-24.
- `.planning/phases/01-app-shell-config/01-CONTEXT.md` — factory
  closure for `create_stream_router(cache)` mounted in lifespan, and
  the stable `/api/stream/prices` endpoint path. Backs D-15, D-16.
- `.planning/phases/05-ai-chat-integration/05-CONTEXT.md` — project
  pattern for sub-package mirroring, factory closures, "latest APIs"
  directive. Applies by analogy to the frontend structure.

### Codebase intel
- `.planning/codebase/ARCHITECTURE.md` — "Missing architectural
  pieces" table still shows `frontend/` missing; this phase closes
  two of those rows (Frontend scaffold + SSE client).
- `.planning/codebase/STRUCTURE.md` — confirms `frontend/` is not
  present today and where it is expected to live. Backs D-23.
- `.planning/codebase/CONCERNS.md` §"Architectural risks" #4 (SSE
  reconnection semantics), #5 (no heartbeat / version-gated
  silence), #6 (session-start baseline). Backs D-14, D-18, D-19.
- `.planning/codebase/CONVENTIONS.md` — narrow error handling at
  boundaries with logging, short modules, no emojis, latest APIs.
  The frontend inherits the "narrow try/catch at the wire boundary"
  rule (D-19).
- `.planning/codebase/INTEGRATIONS.md` — backend API surface the
  frontend will consume in later phases (Phase 6 only touches the
  SSE slice).

### Reusable code touched by Phase 6
- `backend/app/market/stream.py` (read-only — do NOT modify) — the
  SSE endpoint this phase consumes. Key facts: prefix `/api/stream`,
  route `/prices`, ~500 ms emission interval, version-gated
  (silent when `cache.version` unchanged), `retry: 1000\n\n`
  directive on connect so browsers auto-reconnect, event `data:`
  payload is `{TICKER: PriceUpdate.to_dict()}` (not one event per
  ticker).
- `backend/app/market/models.py:39-49` — `PriceUpdate.to_dict()` is
  the shape of each value in the SSE JSON dict. Phase 6 parses
  exactly these keys: `ticker`, `price`, `previous_price`,
  `timestamp`, `change`, `change_percent`, `direction`. Backs D-13,
  D-17.
- `backend/app/main.py` / `backend/app/lifespan.py` — mounts
  `create_stream_router(cache)`; Phase 6 does not touch these.

### External docs (to read during research/planning)
- Next.js App Router static exports:
  https://nextjs.org/docs/app/building-your-application/deploying/static-exports
- Next.js `rewrites()` for dev proxy:
  https://nextjs.org/docs/app/api-reference/next-config-js/rewrites
- Tailwind CSS v4 theme + CSS variables pattern:
  https://tailwindcss.com/docs/theme
- Zustand + external stream pattern:
  https://github.com/pmndrs/zustand
- MDN `EventSource` + auto-reconnect behavior:
  https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- Vitest + Next.js (App Router) setup:
  https://nextjs.org/docs/app/building-your-application/testing/vitest

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Backend SSE endpoint** is already live at `/api/stream/prices`
  (Phase 1 APP-04). No backend changes needed for Phase 6.
- **`PriceUpdate.to_dict()`** (`backend/app/market/models.py:39-49`)
  is the canonical SSE payload shape per ticker — frontend parses
  these keys verbatim.
- **`.planning/phases/*/` precedent** for module layout discipline
  (sub-package mirroring, explicit `__all__`, factory closures).
  Frontend adapts this to `src/lib/*` modules with explicit named
  exports (TypeScript `export`).

### Established Patterns
- **Factory closures over global state** (from the backend). Frontend
  follows the same spirit: a root `<PriceStreamProvider>` owns the
  `EventSource` lifecycle, components read via Zustand selectors —
  no module-level globals that auto-run on import.
- **Narrow exception handling at boundaries** — `JSON.parse` +
  ingest wrapped in a single `try/catch` with `console.warn`; no
  outer wrappers.
- **`%`-style logging in backend → `console.warn` + structured args
  in frontend.** No emojis, no f-strings' frontend analog
  (template-literal abuse in log calls).
- **Short modules, short functions.** Target: `price-store.ts` ≤120
  lines, `price-stream-provider.tsx` ≤40 lines, `sse-types.ts`
  ≤40 lines.
- **Latest APIs** — Next.js 15 + App Router, Tailwind v4, React 19
  (whatever `create-next-app@latest` lands on 2026-04-22). No legacy
  Pages Router, no CRA, no Webpack custom config.

### Integration Points
- `frontend/next.config.mjs` → dev rewrites forward `/api/*` and
  `/api/stream/*` to `localhost:8000` (uvicorn's default port from
  Phase 1 D-03).
- `frontend/src/app/layout.tsx` → wraps children in
  `<PriceStreamProvider>` (owns the one `EventSource`).
- `frontend/src/lib/price-store.ts` → the public import surface for
  all subsequent frontend work (`usePriceStore`, `selectTick`,
  `selectConnectionStatus`). Phase 7/8 consume this without
  modification.
- `frontend/out/` → the static-export artifact Phase 8 (APP-02)
  mounts via `StaticFiles` and Phase 9 (OPS-01) copies into
  `static/` inside the Docker image.

### Anti-Patterns to Avoid
- Cross-origin `EventSource` with CORS on the backend. PLAN.md §3
  forbids CORS; the rewrite (D-07) is the answer.
- Module-level `new EventSource(...)` at import time — breaks SSR
  and double-runs under React StrictMode in dev. The
  provider-owned lifecycle (D-11) is the answer.
- Re-render-the-world state shape — a single Redux/Context state
  object rebuilt on every tick will re-render every subscriber at
  ~500 ms cadence. Zustand selectors are the answer (D-12).
- Extending the backend `PriceUpdate` dataclass to include
  `session_start_price`. Out of scope for this phase; the frontend
  derives it client-side (D-14).

</code_context>

<specifics>
## Specific Ideas

- The store is the **stable contract between Phase 6 and all
  subsequent frontend phases**. Phase 7's watchlist, main chart,
  positions table, trade bar, and header all read from
  `usePriceStore(selector)` and none of them reopen an
  `EventSource`. Phase 8's heatmap, P&L chart, and chat panel do
  the same. Getting the store shape right in Phase 6 saves rework
  later.

- `session_start_price` (D-14) is computed frontend-side in Phase 6
  specifically so Phase 7 FE-03 can compute daily-change % without
  needing a backend change. The page-load-reset behavior is an
  accepted demo tradeoff — a hard refresh without restarting the
  backend resets the "daily" baseline, but during a single demo
  session it's stable.

- The debug page (D-20) isn't cosmetic — it's the manual-test
  artifact that proves Phase 6 success criterion #3 against a live
  backend, and it's cheap to delete or hide behind a dev-only route
  later.

- Zustand (D-12) is picked over `useSyncExternalStore` specifically
  for the selector ergonomics. With 10 default tickers ticking
  every 500 ms, a naive context-based store would trigger hundreds
  of needless component re-renders per second once Phase 7 lands.

- The dev `rewrites()` (D-07) is a quiet piece of infrastructure
  that makes every subsequent phase simpler: `fetch('/api/...')`
  and `new EventSource('/api/stream/prices')` Just Work in both
  dev and the packaged Docker image, with no conditional URL
  logic anywhere.

</specifics>

<deferred>
## Deferred Ideas

- **Backend-emitted `session_start_price` in the SSE event.** D-14
  chooses the frontend-computed path. If it ever shows up as a
  demo issue (e.g., after a backend restart the frontend thinks
  the price is unchanged but the "since-process-started" baseline
  should have reset), revisit by extending
  `backend/app/market/cache.py` + `backend/app/market/models.py`
  to expose `session_start_price` on each `PriceUpdate`, and
  bump the SSE payload shape. Keep it in mind but don't do it in
  Phase 6.

- **SSE heartbeat / keepalive frames** from the backend to keep
  proxies from timing out idle connections (known gap flagged in
  `.planning/codebase/CONCERNS.md` §5). Not a Phase 6 concern —
  localhost dev and single-container prod don't have idle-timeout
  proxies in the path. Revisit if cloud deploy ever enters v1.

- **Persistent connection-status UI.** Phase 7 FE-10 renders the
  header dot. Phase 6 exposes `status` on the store; the visual
  is Phase 7's job.

- **Chart libraries, sparklines, heatmap, P&L line chart.**
  Deferred to Phases 7 and 8 with their respective FE requirements.
  Do not `npm install` `lightweight-charts` or `recharts` in
  Phase 6 — pollutes the dep tree for no benefit.

- **Prettier config.** `create-next-app` ships ESLint only; adding
  Prettier now is scope creep. If contributors ask for it in a
  later phase, add `prettier` + `.prettierrc` + a `format` script.

- **Playwright E2E for SSE reconnect.** TEST-03 / TEST-04 in Phase
  10. Phase 6's reconnect proof is the Vitest test exercising
  `onerror` CONNECTING + CLOSED (D-21).

- **Multi-tab `EventSource` deduplication** (BroadcastChannel or a
  shared worker that proxies one connection across tabs). Nice
  for real-world use; unneeded for the single-tab demo. If
  added, it lives in `price-stream-provider.tsx` behind a feature
  flag.

- **Service-worker offline fallback.** Not relevant — the demo
  requires a live backend by definition.

- **Type-sharing between backend Pydantic and frontend TypeScript.**
  E.g., via `datamodel-code-generator` or hand-authored `.d.ts`
  files. Out of scope — Phase 6 manually defines the `Tick` /
  `RawPayload` types matching `PriceUpdate.to_dict()`. If type
  drift becomes a real pain in Phases 7/8, consider generating
  types from a Pydantic schema as a shared build step.

</deferred>

---

*Phase: 06-frontend-scaffold-sse*
*Context gathered: 2026-04-22*
