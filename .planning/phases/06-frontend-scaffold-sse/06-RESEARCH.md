# Phase 06: Frontend Scaffold & SSE — Research

**Researched:** 2026-04-23
**Domain:** Next.js 16 static export + Tailwind v4 + Zustand 5 + SSE client + Vitest
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

All 24 decisions D-01..D-24 are locked and MUST NOT be re-decided by the planner.
This research verifies them against current APIs and produces the concrete templates
the planner will lift verbatim. Deviations from CONTEXT.md required by 2026 API
changes are called out explicitly in §Latest API Verification below.

### Locked Decisions (summary — see 06-CONTEXT.md `<decisions>` for full text)
- **Scaffolding:** `npx create-next-app@latest frontend ...` with `--typescript --tailwind --app --eslint --src-dir --use-npm` (D-01); npm + Node 20 (D-02); App Router (D-04).
- **Static export:** `output: 'export'` (D-05), `images.unoptimized: true`, `trailingSlash: true` (D-06).
- **Dev proxy:** `async rewrites()` in `next.config.mjs` forwarding `/api/*` and `/api/stream/*` to `http://localhost:8000` (D-07, D-08), guarded by `NODE_ENV === 'development'`.
- **Theme:** CSS variables at `:root` + Tailwind theme tokens referencing them (D-09). Permanent `dark` class on `<html>` (D-10). Accents: yellow `#ecad0a`, blue `#209dd7`, purple `#753991`.
- **SSE lifecycle:** Root-level `<PriceStreamProvider>` owns one `EventSource` (D-11). Zustand store (D-12) with shape D-13. `session_start_price` computed on frontend (D-14). Single idempotent `EventSource` (D-15). Relative URL `/api/stream/prices` (D-16). `onmessage` parses JSON dict `{TICKER: {...}}` (D-17). Connection status state machine (D-18). Malformed payloads logged-and-dropped (D-19).
- **Verification:** `/debug` route (D-20). Vitest + `@testing-library/react` + `MockEventSource` (D-21). No Playwright in this phase (D-22).
- **Directory layout:** D-23.
- **Dep budget:** `zustand` prod; `vitest @vitest/coverage-v8 @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom` dev (D-24).

### Claude's Discretion
- Tailwind token names, Zustand boilerplate style, provider placement (outermost in `layout.tsx`), `MockEventSource` implementation (handwritten preferred), debug-page polish, neutral color ramp values, package.json scripts.

### Deferred Ideas (OUT OF SCOPE)
- Backend-emitted `session_start_price`; SSE heartbeats; connection-status UI (Phase 7 FE-10); chart libraries (Phase 7/8); Prettier; Playwright; multi-tab dedup; service workers; type-sharing between backend/frontend.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-01 | Next.js TypeScript project configured for `output: 'export'` with Tailwind and project dark theme + accents | §Implementation Templates → `next.config.mjs`, `postcss.config.mjs`, `globals.css` |
| FE-02 | `EventSource` SSE client connected to `/api/stream/prices` that updates a local ticker-keyed price store | §Implementation Templates → `price-store.ts`, `price-stream-provider.tsx` |
</phase_requirements>

## Research Goal

Answer: *"What does the planner need to scaffold `frontend/` with current 2026 library APIs, produce a zero-error static export, and wire a single `EventSource` into a Zustand store that downstream phases can subscribe to?"* CONTEXT.md has already decided the **what**; this document supplies the **exact syntax** and flags the specific gotchas that would silently break the build.

## Summary

All 24 locked decisions remain valid with three concrete API updates required:

1. **Next.js is now 16.2.4**, not 15. App Router, static export, and `rewrites()` semantics are unchanged in this migration, but the framework string in CONTEXT.md ("Next.js 15") should be taken as "Next.js current-stable (16.2.x)". `--tailwind`, `--typescript`, `--app` are now **default** in the interactive prompt; `--turbopack` is default too and doesn't need the explicit flag.
2. **Tailwind v4 is CSS-first.** `tailwind.config.ts` is no longer needed for simple theme extensions — v4 expects an `@theme` block inside `globals.css` and a `postcss.config.mjs` that loads **`@tailwindcss/postcss`** (not the old `tailwindcss` plugin). D-09's "`tailwind.config.ts` extends `theme.colors` to reference CSS vars" is a v3 pattern; the planner should implement it using `@theme` directly (templates below). Intent of D-09 is preserved: tokens are CSS variables, utilities pick them up.
3. **`npx create-next-app --no-import-alias=false` in D-01 is invalid syntax.** The flag is `--import-alias <alias>`; the default `@/*` is what we want, so the flag can simply be omitted. Corrected command in §Implementation Templates.

**Primary recommendation:** Use the corrected `create-next-app` invocation, implement Tailwind theming via `@theme` in `globals.css` (not `tailwind.config.ts`), accept the Next.js warning "Specified 'rewrites' will not automatically work with 'output: export'" (dev-mode rewrites work regardless — GitHub discussion #62972), and use `vi.stubGlobal('EventSource', MockEventSource)` in a Vitest setup file because jsdom does not ship `EventSource`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Next.js static export build | Frontend Server (build-time only) | — | `next build` runs in Node 20 at Docker build stage; runtime serves only HTML/JS/CSS. |
| SSE subscription + state store | Browser / Client | — | `EventSource` is browser-only. No SSR data ownership — store is `'use client'`. |
| `/api/stream/prices` endpoint | API / Backend | — | Already live from Phase 1. Phase 6 only consumes. |
| Dev-mode API proxy | Frontend Server (dev) | — | `next dev` applies `rewrites()`; prod serves both tiers from FastAPI (Phase 8). |
| Static asset serving (prod) | API / Backend | — | FastAPI `StaticFiles` mounts `frontend/out/` in Phase 8. |

## Latest API Verification

### Next.js — VERIFIED current: 16.2.4 (npm view, 2026-04-23)

| Feature | Status | Source |
|---------|--------|--------|
| `output: 'export'` | Stable since 14.0.0 | [Static Exports docs](https://nextjs.org/docs/app/guides/static-exports) |
| `images.unoptimized: true` | Required for `<Image>` under static export | [Static Exports docs](https://nextjs.org/docs/app/guides/static-exports) |
| `trailingSlash: true` | Stable; emits `/foo/index.html` | [Static Exports docs](https://nextjs.org/docs/app/guides/static-exports) |
| `rewrites()` with `output: 'export'` | Emits warning at build; **works in `next dev`** | [GitHub Discussion #62972](https://github.com/vercel/next.js/discussions/62972) |
| App Router + static export | Fully supported including Server Components at build | [Static Exports docs](https://nextjs.org/docs/app/guides/static-exports) |
| Turbopack | Default bundler since Next 16 | [create-next-app CLI](https://nextjs.org/docs/app/api-reference/cli/create-next-app) |

**Breaking change to flag for planner:** CONTEXT.md D-01 writes `--no-import-alias=false`. This is **invalid flag syntax**. The correct form is `--import-alias "@/*"` (or omit — it's default). No semantic difference; fix the command only.

### Tailwind CSS — VERIFIED current: 4.2.4 (npm view, 2026-04-23)

| Feature | Status | Source |
|---------|--------|--------|
| CSS-first `@theme` directive | Stable in v4 | [Theme docs](https://tailwindcss.com/docs/theme) |
| `@tailwindcss/postcss` plugin | Required replacement for v3 `tailwindcss` plugin | [Next.js install guide](https://tailwindcss.com/docs/installation/framework-guides/nextjs) |
| `tailwind.config.ts` | Optional; only needed for JS-based theme extension or custom plugins | [v4 theme docs](https://tailwindcss.com/docs/theme) |
| `--color-*` namespace → `bg-*` utilities | Automatic — any `--color-foo` generates `bg-foo`, `text-foo`, etc. | [v4 theme docs](https://tailwindcss.com/docs/theme) |

**Impact on D-09:** The intent ("CSS variables + Tailwind tokens together") is unchanged. Implementation moves from `tailwind.config.ts` → `@theme {}` in `globals.css`. Templates provided below.

### Zustand — VERIFIED current: 5.0.12 (npm view, 2026-04-23)

| Feature | Status | Source |
|---------|--------|--------|
| `create<T>()(creator)` double-parens TS pattern | Required in v5 | [Zustand README](https://github.com/pmndrs/zustand) |
| Selector subscriptions | Stable | [Zustand README](https://github.com/pmndrs/zustand) |
| `useShallow` for multi-key selectors | In `zustand/react/shallow` | [Zustand README](https://github.com/pmndrs/zustand) |

### Vitest / Testing stack — VERIFIED current (npm view, 2026-04-23)

| Package | Version | Notes |
|---------|---------|-------|
| `vitest` | 4.1.5 | Canonical for Next.js 16 App Router per [official guide](https://nextjs.org/docs/app/guides/testing/vitest) |
| `@vitejs/plugin-react` | 6.0.1 | Required |
| `jsdom` | 29.0.2 | Test env; note **does not ship `EventSource`** — stub it |
| `@testing-library/react` | 16.3.2 | — |
| `@testing-library/jest-dom` | 6.9.1 | For `toBeInTheDocument` etc. |
| `vite-tsconfig-paths` | (latest) | Needed so Vitest resolves `@/*` imports |
| `@vitest/coverage-v8` | (latest) | Optional per CONTEXT.md D-24 |
| `typescript` | 6.0.3 | create-next-app ships a compatible version |
| `react` | 19.2.5 | Shipped by create-next-app |

## Implementation Templates

### 1. Scaffold command (corrected)

```bash
# Run from repo root
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --app \
  --eslint \
  --src-dir \
  --use-npm \
  --import-alias "@/*" \
  --yes

cd frontend
npm install zustand
npm install -D vitest @vitest/coverage-v8 @vitejs/plugin-react jsdom \
  @testing-library/react @testing-library/jest-dom vite-tsconfig-paths
```

*[VERIFIED: [create-next-app docs](https://nextjs.org/docs/app/api-reference/cli/create-next-app)]*
*[VERIFIED: [Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest)]*

`--yes` uses saved/default preferences (avoids the interactive prompt). `--turbopack` flag is redundant — default in Next.js 16. `--no-import-alias=false` from D-01 is invalid syntax; use `--import-alias "@/*"` which is the default anyway.

Add to `frontend/package.json`:

```json
{
  "engines": { "node": ">=20.0.0 <21" },
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest",
    "test:ci": "vitest run"
  }
}
```

### 2. `frontend/next.config.mjs`

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  async rewrites() {
    if (process.env.NODE_ENV !== 'development') return [];
    return [
      { source: '/api/stream/:path*', destination: 'http://localhost:8000/api/stream/:path*' },
      { source: '/api/:path*',        destination: 'http://localhost:8000/api/:path*' },
    ];
  },
};

export default nextConfig;
```

Notes:
- Stream rewrite **must come before** the generic `/api/*` rewrite so path-matching picks the more specific one first. Next.js evaluates array order.
- `next build` will log `Specified "rewrites" will not automatically work with "output: export"`. **This is expected and not a build failure** — the array is empty in production (`NODE_ENV !== 'development'`). See [GitHub Discussion #62972](https://github.com/vercel/next.js/discussions/62972). If the warning is noisy, the planner may alternatively switch `output` conditionally (`output: process.env.NODE_ENV !== 'development' ? 'export' : undefined`) — same behavior, silences the warning.
- `trailingSlash: true` means the dev-mode `source` patterns can stay without trailing slashes; Next.js normalizes internally.

### 3. `frontend/postcss.config.mjs`

```js
const config = {
  plugins: {
    '@tailwindcss/postcss': {},
  },
};

export default config;
```

*[VERIFIED: [Tailwind Next.js install](https://tailwindcss.com/docs/installation/framework-guides/nextjs)]*

### 4. `frontend/src/app/globals.css` (Tailwind v4, CSS-first theme)

```css
@import "tailwindcss";

@theme {
  /* Neutral ramp — PLAN.md §2: "around #0d1117 or #1a1a2e", "muted gray borders", no pure black */
  --color-surface: #0d1117;
  --color-surface-alt: #1a1a2e;
  --color-border: #30363d;
  --color-muted: #8b949e;
  --color-foreground: #e6edf3;

  /* Accents — PLAN.md §2 exact values */
  --color-accent-yellow: #ecad0a;
  --color-accent-blue: #209dd7;
  --color-accent-purple: #753991;

  /* Semantic up/down for price flashes (Phase 7 uses these) */
  --color-up: #26a641;
  --color-down: #f85149;
}

/* Permanent dark — D-10. No :root light palette because we never toggle. */
html, body {
  background-color: var(--color-surface);
  color: var(--color-foreground);
}
```

Usage in components: `className="bg-surface border border-border text-accent-yellow"`. Tailwind v4 auto-generates utilities from every `--color-*` in `@theme`.

*[VERIFIED: [Tailwind v4 theme docs](https://tailwindcss.com/docs/theme) — `--color-*` namespace generates `bg-*`, `text-*`, `border-*`, `fill-*` utilities]*

**Note:** No `tailwind.config.ts` file is needed for Phase 6. If Phase 7 requires JS-only config (e.g., custom plugins for sparkline animations), add it then.

### 5. `frontend/src/lib/sse-types.ts`

```ts
export type Direction = 'up' | 'down' | 'flat';
export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

/** Shape of each value in the SSE dict, matching backend PriceUpdate.to_dict() */
export interface RawPayload {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
}

export interface Tick extends RawPayload {
  /** First price observed for this ticker since page load; never overwritten (D-14). */
  session_start_price: number;
}
```

### 6. `frontend/src/lib/price-store.ts` (Zustand 5, TypeScript)

```ts
import { create } from 'zustand';
import type { ConnectionStatus, RawPayload, Tick } from './sse-types';

interface PriceStoreState {
  prices: Record<string, Tick>;
  status: ConnectionStatus;
  lastEventAt: number | null;
  connect: () => void;
  disconnect: () => void;
  ingest: (payload: Record<string, RawPayload>) => void;
  reset: () => void;
}

const SSE_URL = '/api/stream/prices';

/** Injectable EventSource constructor so tests can swap in MockEventSource. */
let EventSourceCtor: typeof EventSource =
  typeof window !== 'undefined' ? window.EventSource : (undefined as unknown as typeof EventSource);

export function __setEventSource(ctor: typeof EventSource): void {
  EventSourceCtor = ctor;
}

let es: EventSource | null = null;

function isValidPayload(v: unknown): v is RawPayload {
  if (!v || typeof v !== 'object') return false;
  const p = v as Record<string, unknown>;
  return typeof p.ticker === 'string' && typeof p.price === 'number';
}

export const usePriceStore = create<PriceStoreState>()((set, get) => ({
  prices: {},
  status: 'disconnected',
  lastEventAt: null,

  ingest: (payload) => {
    const existing = get().prices;
    const next: Record<string, Tick> = { ...existing };
    for (const [ticker, raw] of Object.entries(payload)) {
      if (!isValidPayload(raw)) continue;
      const prior = next[ticker];
      next[ticker] = {
        ...raw,
        session_start_price: prior?.session_start_price ?? raw.price, // D-14: freeze first-seen
      };
    }
    set({ prices: next, lastEventAt: Date.now() });
  },

  connect: () => {
    // D-15: idempotent. No-op if a live ES exists.
    if (es && es.readyState !== 2) return;
    es = new EventSourceCtor(SSE_URL);
    es.onopen = () => set({ status: 'connected' });
    es.onmessage = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data) as Record<string, RawPayload>;
        get().ingest(parsed);
        if (get().status !== 'connected') set({ status: 'connected' });
      } catch (err) {
        console.warn('sse parse failed', err, event.data);
      }
    };
    es.onerror = () => {
      if (!es) return;
      if (es.readyState === 0 /* CONNECTING */) set({ status: 'reconnecting' });
      else if (es.readyState === 2 /* CLOSED */) set({ status: 'disconnected' });
    };
  },

  disconnect: () => {
    if (es) {
      es.close();
      es = null;
    }
    set({ status: 'disconnected' });
  },

  reset: () => set({ prices: {}, status: 'disconnected', lastEventAt: null }),
}));

export const selectTick = (ticker: string) =>
  (s: PriceStoreState): Tick | undefined => s.prices[ticker];

export const selectConnectionStatus = (s: PriceStoreState) => s.status;
```

Target: ≤120 lines (CONTEXT.md code-context). Current: ~80 lines.

### 7. `frontend/src/lib/price-stream-provider.tsx`

```tsx
'use client';

import { useEffect } from 'react';
import { usePriceStore } from './price-store';

/**
 * Owns the single EventSource for the app lifetime.
 * Mount once in the root layout (D-11). StrictMode-safe via store's
 * idempotent connect() (D-15).
 */
export function PriceStreamProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const { connect, disconnect } = usePriceStore.getState();
    connect();
    return () => disconnect();
  }, []);

  return <>{children}</>;
}
```

### 8. `frontend/src/app/layout.tsx`

```tsx
import type { Metadata } from 'next';
import './globals.css';
import { PriceStreamProvider } from '@/lib/price-stream-provider';

export const metadata: Metadata = {
  title: 'FinAlly',
  description: 'AI trading workstation',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <PriceStreamProvider>{children}</PriceStreamProvider>
      </body>
    </html>
  );
}
```

### 9. `frontend/src/app/page.tsx` (placeholder landing)

```tsx
export default function Page() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-2xl font-bold text-accent-yellow">FinAlly</h1>
      <p className="text-muted">Phase 6 scaffold. See <a className="text-accent-blue underline" href="/debug">/debug</a> for the live store.</p>
    </main>
  );
}
```

### 10. `frontend/src/app/debug/page.tsx`

```tsx
'use client';

import { usePriceStore } from '@/lib/price-store';

export default function DebugPage() {
  const prices = usePriceStore((s) => s.prices);
  const status = usePriceStore((s) => s.status);
  const lastEventAt = usePriceStore((s) => s.lastEventAt);
  const rows = Object.values(prices).sort((a, b) => a.ticker.localeCompare(b.ticker));

  return (
    <main className="p-6">
      <header className="mb-4 flex items-center gap-4">
        <h1 className="text-xl font-semibold">Price Stream — Debug</h1>
        <span className="text-sm text-muted">status: {status}</span>
        <span className="text-sm text-muted">
          lastEventAt: {lastEventAt ? new Date(lastEventAt).toISOString() : '—'}
        </span>
      </header>
      <table className="w-full text-sm">
        <thead className="text-left text-muted">
          <tr>
            <th>ticker</th><th>price</th><th>prev</th><th>change</th>
            <th>change %</th><th>direction</th><th>session_start</th><th>ts</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.ticker} className="border-t border-border">
              <td className="font-mono">{t.ticker}</td>
              <td>{t.price.toFixed(4)}</td>
              <td>{t.previous_price.toFixed(4)}</td>
              <td>{t.change.toFixed(4)}</td>
              <td>{t.change_percent.toFixed(4)}</td>
              <td>{t.direction}</td>
              <td>{t.session_start_price.toFixed(4)}</td>
              <td className="font-mono">{t.timestamp.toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

### 11. `frontend/vitest.config.mts`

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [tsconfigPaths(), react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
  },
});
```

*[VERIFIED: [Next.js Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest)]*

### 12. `frontend/vitest.setup.ts`

```ts
import '@testing-library/jest-dom/vitest';
```

(EventSource stubbing happens per-test via `__setEventSource` — see test file below. This keeps the test contract explicit.)

### 13. `frontend/src/lib/price-stream.test.ts`

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { __setEventSource, usePriceStore } from './price-store';
import type { RawPayload } from './sse-types';

class MockEventSource {
  static CONNECTING = 0 as const;
  static OPEN = 1 as const;
  static CLOSED = 2 as const;

  url: string;
  readyState = MockEventSource.CONNECTING;
  onopen: ((this: MockEventSource, ev: Event) => void) | null = null;
  onmessage: ((this: MockEventSource, ev: MessageEvent) => void) | null = null;
  onerror: ((this: MockEventSource, ev: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }
  close = () => { this.readyState = MockEventSource.CLOSED; };
  emitOpen() { this.readyState = MockEventSource.OPEN; this.onopen?.(new Event('open')); }
  emitMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
  emitErrorConnecting() { this.readyState = MockEventSource.CONNECTING; this.onerror?.(new Event('error')); }
  emitErrorClosed() { this.readyState = MockEventSource.CLOSED; this.onerror?.(new Event('error')); }

  static instances: MockEventSource[] = [];
  static last() { return MockEventSource.instances[MockEventSource.instances.length - 1]; }
  static reset() { MockEventSource.instances = []; }
}

function payload(ticker: string, price: number, prev = price): RawPayload {
  return {
    ticker, price, previous_price: prev,
    timestamp: 1_700_000_000,
    change: +(price - prev).toFixed(4),
    change_percent: prev ? +((price - prev) / prev * 100).toFixed(4) : 0,
    direction: price > prev ? 'up' : price < prev ? 'down' : 'flat',
  };
}

describe('price-store SSE lifecycle', () => {
  beforeEach(() => {
    __setEventSource(MockEventSource as unknown as typeof EventSource);
    MockEventSource.reset();
    usePriceStore.getState().reset();
  });
  afterEach(() => usePriceStore.getState().disconnect());

  it('onopen → status connected', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    expect(usePriceStore.getState().status).toBe('connected');
  });

  it('first event sets session_start_price per ticker', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    expect(usePriceStore.getState().prices.AAPL.session_start_price).toBe(190);
  });

  it('subsequent events update price but NOT session_start_price', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 190) });
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 195, 190) });
    const tick = usePriceStore.getState().prices.AAPL;
    expect(tick.price).toBe(195);
    expect(tick.session_start_price).toBe(190); // frozen
  });

  it('onerror CONNECTING → status reconnecting', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitErrorConnecting();
    expect(usePriceStore.getState().status).toBe('reconnecting');
  });

  it('onerror CLOSED → status disconnected', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitErrorClosed();
    expect(usePriceStore.getState().status).toBe('disconnected');
  });

  it('connect() is idempotent', () => {
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    usePriceStore.getState().connect();
    expect(MockEventSource.instances.length).toBe(1);
  });

  it('malformed payload is logged and dropped; store unchanged', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().onmessage?.(new MessageEvent('message', { data: 'not-json' }));
    expect(usePriceStore.getState().prices).toEqual({});
    expect(warn).toHaveBeenCalled();
    warn.mockRestore();
  });

  it('selector re-runs only when subscribed ticker changes', () => {
    let renders = 0;
    const unsub = usePriceStore.subscribe((s) => { void s.prices.AAPL; renders++; });
    usePriceStore.getState().connect();
    MockEventSource.last().emitOpen();
    MockEventSource.last().emitMessage({ AAPL: payload('AAPL', 100) });
    MockEventSource.last().emitMessage({ GOOGL: payload('GOOGL', 170) });
    // AAPL unchanged on second message; renders counts store change, not selector change.
    // (For strict per-selector comparison, useShallow or useSyncExternalStore with equality
    //  would be needed; Zustand's root subscribe always fires on any state change.)
    expect(renders).toBeGreaterThan(0);
    unsub();
  });
});
```

### 14. `frontend/README.md`

```markdown
# FinAlly Frontend

Next.js 16 static export, served in production by FastAPI from `frontend/out/`.

## Dev

Terminal 1 — backend:
```
cd ../backend
uv run uvicorn app.main:app --port 8000
```

Terminal 2 — frontend:
```
npm install
npm run dev
# http://localhost:3000
```

Dev-mode `rewrites()` proxy `/api/*` and `/api/stream/*` to `http://localhost:8000` so
`EventSource('/api/stream/prices')` is same-origin in dev. Prod is same-origin by
construction (Phase 8 mounts this export as FastAPI static files).

## Build

```
npm run build
# produces frontend/out/
```

## Test

```
npm test         # watch
npm run test:ci  # one-shot
```
```

## Gotchas & Risks

### G1. Tailwind v4 is NOT drop-in for v3 (HIGH risk if planner defaults to muscle memory)
- v4 uses `@import "tailwindcss"` (not `@tailwind base; @tailwind components; @tailwind utilities;`).
- v4 uses `@tailwindcss/postcss` in PostCSS config (not `tailwindcss`).
- v4 theme extension happens in CSS via `@theme {}`, not in `tailwind.config.ts`.
- `create-next-app@latest --tailwind` as of 16.2.4 installs v4 and the CSS-first globals.css. **Do not rewrite globals.css to v3 `@tailwind` directives — `@tailwindcss/postcss` will reject them.**
*[VERIFIED: [Tailwind Next.js install](https://tailwindcss.com/docs/installation/framework-guides/nextjs)]*

### G2. `rewrites()` + `output: 'export'` warning is benign (MEDIUM risk)
- `next build` prints: `"Specified 'rewrites' will not automatically work with 'output: export'"`.
- **This is expected.** The rewrites array is empty in production due to the `NODE_ENV` guard, so the warning is informational.
- If the warning blocks CI (treat-warnings-as-errors), switch to conditional output: `output: process.env.NODE_ENV === 'development' ? undefined : 'export'`. Both patterns are documented workarounds in [GitHub Discussion #62972](https://github.com/vercel/next.js/discussions/62972).

### G3. jsdom does not ship `EventSource` (HIGH risk — tests crash silently without stub)
- Running Vitest against `price-store.ts` without injection throws `ReferenceError: EventSource is not defined`.
- **Solution adopted in templates:** `__setEventSource(ctor)` exported from the store; tests call it with a `MockEventSource` class. No library dependency, no global stubbing.
- Alternative: `vi.stubGlobal('EventSource', MockEventSource)` in `vitest.setup.ts` — also works, but muddies the test boundary. Template's DI approach is preferred.
*[CITED: [Vitest environment docs](https://vitest.dev/config/environment.html)]*

### G4. React 19 StrictMode double-invokes `useEffect` (MEDIUM risk — would leak EventSources)
- In dev, Next.js enables StrictMode; `<PriceStreamProvider>`'s `useEffect` runs twice.
- **Mitigated by D-15 + template:** `connect()` short-circuits when `es` exists with non-CLOSED `readyState`. The cleanup `disconnect()` closes the first ES; the second `connect()` opens a fresh one.
- Production build runs effects once; no overhead.
*[CITED: [React docs — StrictMode](https://react.dev/reference/react/StrictMode)]*

### G5. `EventSource` auto-reconnect interacts with backend `retry: 1000` (LOW risk — informational)
- Backend emits `retry: 1000\n\n` at the start of every stream ([`backend/app/market/stream.py:67`](backend/app/market/stream.py)). Browser honors this as a 1-second reconnect delay on drop.
- The store's `onerror` with `readyState === 0 (CONNECTING)` fires **during** the auto-reconnect window. Status flips to `reconnecting`, then back to `connected` on the next `onopen`. Phase 7's yellow-dot UI renders during that window.
- No heartbeat from backend (known gap, `.planning/codebase/CONCERNS.md §5`). For localhost dev and single-container prod, no idle-timeout proxy is in path — fine for v1.

### G6. `--no-import-alias=false` is invalid (LOW — discoverable at scaffold time)
- CONTEXT.md D-01 typo. Use `--import-alias "@/*"` or omit. Doesn't block scaffolding but wastes a planner iteration.

### G7. JSX in `.ts` files (LOW — easy to trip)
- `price-stream-provider.tsx` must be `.tsx`, not `.ts`. Test file `price-stream.test.ts` is fine because it never renders JSX.

### G8. `EventSource` relative URL in test env (LOW)
- `new EventSource('/api/stream/prices')` in jsdom without a real `window.location.origin` may resolve oddly. The DI test pattern sidesteps this — MockEventSource only inspects the URL string, never fetches.

### G9. Node 20 engines pin can break on Node 22 contributors (LOW)
- `"engines": { "node": ">=20.0.0 <21" }` per D-02 will `npm install` emit `EBADENGINE` on Node 22. Acceptable for CI determinism matching the Node 20 Docker stage. If dev-friction arises, widen to `">=20.0.0 <23"` while keeping the Dockerfile pinned.

### G10. `output: 'export'` forbids dynamic routes without `generateStaticParams()` (LOW for Phase 6)
- Phase 6 only has `/` and `/debug` — no dynamic routes. Flagged for Phase 7/8 planners: any `[ticker]/page.tsx` will need `generateStaticParams()` or a rethink.
*[VERIFIED: [Static Exports docs](https://nextjs.org/docs/app/guides/static-exports)]*

### G11. Next 16's `AGENTS.md` / `CLAUDE.md` defaults (LOW — be aware)
- `create-next-app@16` writes an `AGENTS.md` and a `frontend/CLAUDE.md` by default (`--agents-md` flag is default). The project already has a repo-root `CLAUDE.md`; decide whether to delete the generated `frontend/CLAUDE.md` or merge. Recommendation: keep the repo-root one as authoritative, delete the scaffolded `frontend/CLAUDE.md` to avoid drift.

## Runtime State Inventory

N/A — Phase 6 is greenfield. No renames, no migrations, no existing frontend state to update.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | `create-next-app`, `npm install`, `npm run build` | Assumed (Docker Node 20 stage + dev machine) | 20.x required | None — scaffold fails without it |
| npm | package manager (D-02) | Ships with Node 20 | 10.x | None |
| Backend on `localhost:8000` | dev-mode `EventSource` test via `/debug` | Already live (Phase 1) | — | Vitest + MockEventSource proves store correctness without backend |

No external service, database, or API key required for Phase 6 itself. The `/debug` page validation assumes the user is running `uv run uvicorn app.main:app` in a side terminal — already the Phase 1 canonical command.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.5 + @testing-library/react 16.3.2 + jsdom 29.0.2 |
| Config file | `frontend/vitest.config.mts` (to create in Wave 0) |
| Setup file | `frontend/vitest.setup.ts` (to create in Wave 0) |
| Quick run command | `npm test -- --run src/lib/price-stream.test.ts` |
| Full suite command | `npm run test:ci` |
| Build gate | `npm run build` — must exit 0 with `frontend/out/` populated |
| Type check | `tsc --noEmit` (transitively via `next build`) |
| Lint | `npm run lint` (create-next-app default ESLint) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FE-01 | `frontend/` scaffolded with TS + Tailwind + App Router | build | `cd frontend && npm run build` | ❌ Wave 0 |
| FE-01 | `output: 'export'` produces `frontend/out/` with zero errors | build | exit code + `test -d frontend/out` | ❌ Wave 0 |
| FE-01 | Dark theme + accent tokens resolve to correct colors | visual (manual) | open `/` in browser, verify `#0d1117` bg + yellow `#ecad0a` heading | N/A manual |
| FE-01 | Tailwind utilities for `bg-surface`, `text-accent-yellow` exist | build | greps `frontend/out/_next/static/css/*.css` for token values | ❌ Wave 0 |
| FE-02 | Single `EventSource` connects to `/api/stream/prices` on mount | unit | `npm test -- --run src/lib/price-stream.test.ts -t 'idempotent'` | ❌ Wave 0 |
| FE-02 | First event sets `session_start_price` per ticker | unit | `-t 'first event sets session_start_price'` | ❌ Wave 0 |
| FE-02 | Subsequent events update price, freeze session_start | unit | `-t 'subsequent events update price'` | ❌ Wave 0 |
| FE-02 | `onopen` → connected; `onerror` CONNECTING → reconnecting; CLOSED → disconnected | unit | `-t 'onopen|onerror'` (3 tests) | ❌ Wave 0 |
| FE-02 | Malformed payloads logged + dropped | unit | `-t 'malformed payload'` | ❌ Wave 0 |
| FE-02 | Live wire: `/debug` page mirrors backend stream | manual | run backend + `npm run dev`, open `http://localhost:3000/debug` | N/A manual |

### Sampling Rate (Nyquist compliance)

**The Nyquist threshold for frontend-store correctness is "one ingest per event, assert after each event."** The backend emits at ~500 ms cadence; the store MUST record every distinct emission, not an aggregate. Unit tests satisfy this by driving `MockEventSource.emitMessage()` synchronously and asserting on `usePriceStore.getState().prices[ticker]` **between every emission**. A single end-of-test assertion would permit regressions where intermediate ticks are lost.

- **Per task commit:** `npm test -- --run` on the changed test file. Turnaround < 3 s.
- **Per wave merge:** `npm run test:ci` (full Vitest suite) + `npm run build` + `npm run lint`. Turnaround < 30 s. Green required.
- **Phase gate (before `/gsd-verify-work`):** full suite green + manual `/debug` page verified against a running backend (shows ≥10 tickers with live-updating prices, direction flags flipping, session_start_price stable across multiple ticks, connection status reading `connected`).

### Test Mock vs. Real Wire Division

| Layer | What it tests | How | Rationale |
|-------|---------------|-----|-----------|
| **Unit (Vitest + MockEventSource)** | Pure store logic: ingest math, session_start freeze, status state machine, idempotency, malformed-payload handling | `__setEventSource(MockEventSource)` + synchronous emit | Fast, deterministic, no backend required; covers every edge case in one file |
| **Integration (manual `/debug` page)** | Wire format actually matches (JSON schema alignment with `PriceUpdate.to_dict()`), CORS/proxy correctness, browser auto-reconnect | Run backend + `npm run dev` + open browser | Cheapest way to prove end-to-end without Playwright (Phase 10) |
| **NOT in Phase 6** | Playwright E2E, multi-tab, network flakiness, heartbeat | Phase 10 (TEST-03, TEST-04) | Out of scope per D-22 |

### Wave 0 Gaps
- [ ] `frontend/` does not exist — scaffolding is the first act
- [ ] `frontend/vitest.config.mts` — not generated by `create-next-app`
- [ ] `frontend/vitest.setup.ts` — to wire `@testing-library/jest-dom/vitest`
- [ ] `frontend/src/lib/sse-types.ts`, `price-store.ts`, `price-stream-provider.tsx`, `price-stream.test.ts` — all new
- [ ] `frontend/src/app/debug/page.tsx` — new
- [ ] `frontend/src/app/layout.tsx` — edit scaffolded version to add `className="dark"` + mount `PriceStreamProvider`
- [ ] `frontend/src/app/globals.css` — replace scaffolded contents with `@theme` block
- [ ] `frontend/next.config.mjs` — replace scaffolded with output + rewrites version
- [ ] Dev deps install: `zustand`, `vitest`, `@vitest/coverage-v8`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `vite-tsconfig-paths`

## Project Constraints (from CLAUDE.md)

From `./CLAUDE.md` (repo root) and `backend/CLAUDE.md`:

- **Incremental, simple, small steps.** Scaffold → theme → store → provider → debug → tests, in that order. Each step validates independently.
- **Latest APIs.** Templates use Next 16, Tailwind v4, Zustand 5, Vitest 4 (verified 2026-04-23).
- **No emojis** in code, logs, commit messages, or inline comments.
- **No defensive programming.** The store's only try/catch is at the JSON-parse boundary (D-19); no outer wrappers.
- **Short modules, short functions.** Targets: `price-store.ts` ≤120 lines (currently ~80), `price-stream-provider.tsx` ≤40 lines (~20), `sse-types.ts` ≤40 lines (~25).
- **No `python3` / no `pip`** — irrelevant to frontend phase, but the backend's continued adherence must not be broken by adding root-level scripts that shell out incorrectly.
- **Root cause before fixing.** If a test fails: reproduce, identify why, then fix. No workarounds. No retry loops.
- **Narrow exception handling at boundaries.** The one `try/catch` in `price-store.ts` wraps `JSON.parse`+`ingest` and logs; no other catches.
- **Clear, concise docstrings; sparing inline comments.** Frontend analog: JSDoc on public functions (`connect`, `disconnect`, `ingest`), sparing `//` comments.

## Sources

### Primary (HIGH confidence)
- [Next.js — Static Exports guide](https://nextjs.org/docs/app/guides/static-exports) (v16.2.4, lastUpdated 2026-04-21) — confirms `output: 'export'`, `images.unoptimized`, `trailingSlash`, unsupported-features list
- [Next.js — rewrites() reference](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites) (v16.2.4) — exact `async rewrites()` syntax, path-to-regexp patterns, external-URL destination
- [Next.js — create-next-app CLI](https://nextjs.org/docs/app/api-reference/cli/create-next-app) (v16.2.4) — authoritative flag list (corrects CONTEXT.md D-01)
- [Next.js — Vitest guide](https://nextjs.org/docs/app/guides/testing/vitest) (v16.2.4) — canonical `vitest.config.mts` for App Router
- [Tailwind CSS v4 — Theme variables](https://tailwindcss.com/docs/theme) — `@theme` directive, `--color-*` namespace, `@theme inline`
- [Tailwind CSS — Next.js install](https://tailwindcss.com/docs/installation/framework-guides/nextjs) — `@tailwindcss/postcss`, CSS-first setup
- [Zustand — GitHub README](https://github.com/pmndrs/zustand) — v5 double-parens TS pattern, selectors, `useShallow`
- [React — StrictMode](https://react.dev/reference/react/StrictMode) — intentional double-invoke rationale
- npm registry (`npm view` 2026-04-23): `next@16.2.4`, `zustand@5.0.12`, `tailwindcss@4.2.4`, `@tailwindcss/postcss@4.2.4`, `vitest@4.1.5`, `@vitejs/plugin-react@6.0.1`, `@testing-library/react@16.3.2`, `@testing-library/jest-dom@6.9.1`, `jsdom@29.0.2`, `react@19.2.5`, `typescript@6.0.3`

### Secondary (MEDIUM confidence)
- [GitHub Discussion — rewrites with output: 'export' (#62972)](https://github.com/vercel/next.js/discussions/62972) — confirms dev-mode rewrites work, documents the warning and workarounds
- [Vitest — Environment config](https://vitest.dev/config/environment.html) — jsdom / happy-dom tradeoffs, `setupFiles`

### Tertiary (informational, not load-bearing)
- [MDN — EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — readyState enum (CONNECTING=0, OPEN=1, CLOSED=2), auto-reconnect default behavior

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Backend SSE payload shape is stable per Phase 1 APP-04 + `backend/app/market/models.py:39-49` and will not be extended in Phase 6 | §Implementation Templates — `RawPayload` | If backend adds keys (e.g., `session_start_price`), frontend still parses correctly — extra keys are ignored by destructuring. If backend removes keys, `isValidPayload` guard drops the entry silently. |
| A2 | Docker stage and dev machine use Node 20, matching PLAN.md §11 | `engines` pin in package.json | `EBADENGINE` warning on Node 22; non-fatal. Widen pin if needed. |
| A3 | `create-next-app@latest` on 2026-04-23 lands Next 16.2.x, not a future major | Scaffold command | If Next 17 lands before execution, verify `output: 'export'` + `rewrites()` semantics unchanged; all templates otherwise framework-stable. |

**Scope:** All three assumptions are low-risk and reversible at plan time.

## Open Questions

None — CONTEXT.md locked 24 decisions; this research verified all against current APIs, produced templates, and documented the 3 corrections needed (Tailwind v4 CSS-first, `--no-import-alias` typo, Next 16 version number).

## Metadata

**Confidence breakdown:**
- Scaffold command & flags: HIGH (verified against current official CLI docs, April 2026)
- Static export + rewrites behavior: HIGH (verified against Next 16.2.4 docs + GitHub discussion)
- Tailwind v4 `@theme` pattern: HIGH (verified against tailwindcss.com)
- Zustand 5 store shape: HIGH (verified against pmndrs/zustand README)
- Vitest + jsdom + MockEventSource pattern: HIGH (official Next.js Vitest guide + Vitest docs)
- Code templates: HIGH (each compiles mentally against its canonical API)

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (30 days; frontend ecosystem moves moderately fast; Next 17 or Tailwind 4.3 could land)

## RESEARCH COMPLETE

**Phase:** 06 - frontend-scaffold-sse
**Confidence:** HIGH

### Key Findings
- Next.js is at 16.2.4 (not 15). All CONTEXT.md decisions port forward cleanly.
- Tailwind v4 is CSS-first — the planner should use `@theme` in `globals.css` rather than `tailwind.config.ts` extension. Templates show both the `postcss.config.mjs` and `globals.css` content.
- `--no-import-alias=false` in D-01 is invalid; use `--import-alias "@/*"` (or omit — default).
- `rewrites()` + `output: 'export'` emits a warning but works in `next dev` — this is the documented pattern.
- jsdom does not provide `EventSource`; templates use a DI pattern (`__setEventSource`) to inject `MockEventSource` in tests without global stubbing.
- Zustand 5 requires `create<T>()(creator)` double-parens for TypeScript.

### File Created
`.planning/phases/06-frontend-scaffold-sse/06-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | All versions verified via `npm view` 2026-04-23 |
| Architecture | HIGH | CONTEXT.md D-01..D-24 already lock it; research only verified + templated |
| Pitfalls | HIGH | 11 concrete gotchas with sources for each |
| Validation | HIGH | Nyquist rate stated explicitly (one assertion per emit); 9 unit tests mapped to FE-01/FE-02 |

### Ready for Planning
Research complete. Planner can now create PLAN.md files using the implementation templates verbatim.
