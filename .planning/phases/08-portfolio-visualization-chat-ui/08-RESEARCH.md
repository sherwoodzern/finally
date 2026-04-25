# Phase 8: Portfolio Visualization & Chat UI - Research

**Researched:** 2026-04-25
**Domain:** React 19 + Recharts 3 charting, Tailwind v4 push-layout drawer, TanStack Query mutations, FastAPI StaticFiles same-origin mount, Vitest + RTL component tests for SVG-based charts.
**Confidence:** HIGH

## Summary

Phase 8 ships the three "wow" surfaces (heatmap, P&L chart, AI chat drawer), the
demo polish layer (skeletons + agentic-trade animations), the same-origin
APP-02 static mount, and ~22 Vitest component tests. All visual decisions, copy,
spacing, color tokens, and component splits are already locked in CONTEXT.md
(D-01..D-17) and 08-UI-SPEC.md (§1..§14). Research scope is the remaining
plannable technical surface: library APIs, integration patterns, jsdom test
quirks, and concrete file modifications.

**Three findings that materially affect planning:**

1. **Recharts is on 3.x, not 2.x as written in CONTEXT.md D-17 and UI-SPEC §1.**
   `npm view recharts version` returns `3.8.1` (latest, published 2026-03-25).
   The 3.x line is React-19-compatible (peer `^19.0.0`) and the children-based
   composition pattern from 2.x is unchanged. Treemap, LineChart,
   ReferenceLine, Tooltip, ResponsiveContainer all keep the same API shape;
   only `TooltipProps` was renamed to `TooltipContentProps` for typed custom
   tooltips, and `ResponsiveContainer.ref.current.current` was flattened. The
   planner should write `recharts@^3` (or `^3.8.0`) in `package.json`, NOT
   `^2.x`. This is a correction to UI-SPEC §1, NOT a new design decision.
2. **`skipTrailingSlashRedirect` is a valid Next.js 16.2.4 config flag** —
   verified in the Next.js 16 proxy.js docs (advanced proxy flags section).
   It is NOT in the `next.config.js` options index page, but IS officially
   supported and has been since v13.1. D-15 is sound.
3. **Recharts in jsdom needs ResizeObserver mocked** OR `<ResponsiveContainer>`
   replaced with fixed `width`/`height` in tests. Without one of these, the
   container collapses to 0×0 and chart children never render, breaking every
   Heatmap/PnLChart assertion.

**Primary recommendation:** Plan in the order spelled out by UI-SPEC §15
(APP-02 + dev-redirect fix first, then deps + API clients + store extensions,
then TabBar+layout, then Heatmap, P&L, skeletons, chat shell, chat thread,
action cards, chat input + ThinkingBubble, reduced-motion CSS, tests). Each
step is small, has a single clear gate, and isolates risk.

## Architectural Responsibility Map

This phase is purely frontend (Next.js client components + Tailwind + Zustand +
TanStack Query + Recharts) plus one tiny backend edit (`StaticFiles` mount in
the existing lifespan). All API contracts are stable.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Portfolio heatmap rendering (FE-05) | Browser/Client | — | Recharts SVG; reads `usePriceStore` selectors + `useQuery(['portfolio'])` |
| P&L chart rendering (FE-06) | Browser/Client | — | Recharts SVG; reads `useQuery(['portfolio','history'])` only |
| Chat panel UI (FE-09) | Browser/Client | — | Pure React + Tailwind; consumes `/api/chat` + `/api/chat/history` |
| Agentic-trade animation orchestration (FE-11 D-12) | Browser/Client | — | Zustand transient slice (`tradeFlash`) + setTimeout; mirrors Phase 7 price-flash primitive |
| Per-panel skeleton loaders (FE-11 D-13) | Browser/Client | — | Pure CSS (`animate-pulse` Tailwind built-in); gated on TanStack `isPending` |
| Same-origin static serving (APP-02) | API/Backend (FastAPI) | — | One-line mount of `StaticFiles(directory="frontend/out", html=True)` AFTER all routers |
| Dev-mode SSE redirect fix (G1 carry-over) | Browser/Client (Next dev server) | — | `skipTrailingSlashRedirect: true` in `next.config.mjs` |
| Component tests (TEST-02) | Browser/Client (Vitest jsdom) | — | RTL + MockEventSource + (NEW) ResizeObserver stub for Recharts |

**Why this matters:** Plans must NOT push price-data subscription into the
chat panel (no second EventSource), must NOT introduce a toast system
(inline cards own that surface), and must NOT modify any Phase 1–5 backend
contract. The single backend edit is the StaticFiles mount; everything else
is frontend.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Heatmap (FE-05):**

- **D-01:** Recharts `<Treemap>` (single new chart dep). Rejected hand-rolled
  CSS-grid and `react-d3-treemap`.
- **D-02:** Binary up/down coloring — `--color-up` when `unrealized_pnl >= 0`
  else `--color-down`. Phase 7 D-02 palette inherited.
- **D-03:** Label = ticker (bold, top) + signed P&L % (mono, below). Click
  reuses `selectedTicker` to drive the main chart. Cash excluded from heatmap.

**P&L Chart (FE-06):**

- **D-04:** Recharts `<LineChart>` over ALL snapshots from
  `GET /api/portfolio/history`. No time-window selector.
- **D-05:** Dotted $10k starting reference line via `<ReferenceLine y={10000}>`,
  dashed, low-opacity.
- **D-06:** Stroke flips at break-even — `--color-up` solid when last
  `total_value >= 10000` else `--color-down`.

**Chat Panel (FE-09):**

- **D-07:** Right-edge drawer, **default open**, push layout (~380px).
  `transition-[width] duration-300`. Header toggle collapses to a 48px icon
  strip.
- **D-08:** Loading indicator = animated 3-dot "thinking" bubble, pure CSS
  keyframes, sits as the last assistant message in the thread while
  `POST /api/chat` is in flight.
- **D-09:** History on mount via `GET /api/chat/history` (Phase 5 D-19 — ASC
  tail, `limit=50` default).

**Action Confirmations:**

- **D-10:** Inline action cards under the assistant message. Order matches
  Phase 5 D-09 — watchlist first, then trades.
- **D-11:** Status styling — color-coded by Phase 5 D-07 status
  (`executed`/`added`/`removed` → green; `exists`/`not_present` → muted;
  `failed` → red with error code mapped to human strings).

**Agentic "Wow" Moment:**

- **D-12:** Action-card pulse + position-row flash on auto-trade (~800ms
  coordinated, longer than Phase 7's 500ms price flash). Header total + cash
  re-render via TanStack Query invalidation.
- **D-13:** First-load = skeleton blocks per panel. Pure CSS, no library.
  Skeleton until first SSE tick / first `/api/portfolio` resolve / first
  snapshot.

**Static Mount (APP-02):**

- **D-14:** FastAPI `StaticFiles` mount of `frontend/out/` at `/` AFTER API
  routers. `html=True` so visiting `/` serves `out/index.html`.
- **D-15:** `skipTrailingSlashRedirect: true` in `next.config.mjs` — fixes
  Phase 7 G1 dev-redirect chain so `npm run dev` SSE works, and prod static
  mount sidesteps the chain entirely.

**Frontend Tests (TEST-02):**

- **D-16:** Vitest + RTL + MockEventSource pattern (Phase 6 D-test). Coverage:
  price-flash trigger (regression), watchlist CRUD UI (via chat-driven
  add/remove cards + existing watchlist panel), portfolio display calculations
  (heatmap weight, P&L %, reference-line condition), chat rendering + loading
  state. No Playwright in this phase.

**Dependencies:**

- **D-17:** Add `recharts` as a frontend prod dep. (Note version correction
  below — see "Version Verification" in §Standard Stack.)

### Claude's Discretion

The planner may pick conventional defaults without re-asking on:

- Heatmap empty state copy and cold-cache fallback.
- P&L chart with 0/1 snapshots — show skeleton + empty state until ≥2 points.
- P&L chart tooltip detail — date + total formatted as `$X,XXX.XX`, optional
  delta vs $10k.
- Layout placement of heatmap and P&L chart (UI-SPEC §5.1 already locked
  this as a tabbed center column).
- Action-card layout details (icon, padding, monospace numerics).
- Failed-action error message strings (UI-SPEC §8.5 already locked these).
- Chat input UX — Enter to send, Shift+Enter for newline, Cmd/Ctrl+Enter
  also submits (UI-SPEC §5.8).
- Empty chat state — single welcome line; no suggested-prompt buttons.
- Manual-trade flash — UI-SPEC §4.2 locked YES.
- Drawer toggle keyboard shortcut (Cmd+K) — explicitly DEFERRED.

### Deferred Ideas (OUT OF SCOPE)

- P&L chart time-window selector (1h / 1d / All toggles).
- Heatmap with cash slice.
- Sector coloring on heatmap.
- Suggested-prompt buttons in empty chat.
- Token-by-token chat streaming (CHAT-07, v2).
- Toast / global notification system.
- Trade-history dedicated view (HIST-01, v2).
- Mobile/tablet responsive stacking + a11y polish (POLISH-01, v2).
- Chat keyboard shortcut to focus input (Cmd+K).
- Heatmap drilling/zooming.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-05 | Portfolio heatmap — treemap, sized by weight, colored by P&L | §Standard Stack (Recharts Treemap), §Pattern 1 (Treemap content render), §Common Pitfall 1 (cell size threshold), §Code Examples |
| FE-06 | P&L line chart driven by `/api/portfolio/history` (Recharts SVG) | §Standard Stack (Recharts LineChart + ReferenceLine + Tooltip), §Pattern 2 (LineChart composition), §Code Examples |
| FE-09 | AI chat panel — docked/collapsible sidebar, history, send box, loading indicator, inline confirmations | §Pattern 3 (Tailwind push drawer), §Pattern 4 (TanStack Query mutation + auto-scroll), §Code Examples |
| FE-11 | Demo-grade polish — transitions, skeletons, chat micro-interactions, trade-execution moments | §Pattern 5 (Zustand `tradeFlash` slice), §Pattern 6 (CSS `@keyframes` + `prefers-reduced-motion`), §Pattern 7 (skeleton-block primitive) |
| APP-02 | FastAPI serves Next.js static export from `/` on same port as API | §Pattern 8 (StaticFiles mount AFTER routers), §Common Pitfall 4 (route precedence), §Code Examples |
| TEST-02 | Frontend component tests — price flash, watchlist CRUD UI, portfolio display calc, chat rendering + loading state | §Pattern 9 (Vitest + RTL + MockEventSource + ResizeObserver stub), §Common Pitfall 5 (jsdom + Recharts size collapse) |

## Project Constraints (from CLAUDE.md)

The following directives MUST be honored by every plan and task in this phase.
They are project-wide rules, not phase-specific decisions.

| Rule | Where it bites in Phase 8 |
|------|---------------------------|
| **Latest library APIs** | `recharts@^3` (NOT `^2`); `lightweight-charts@^5` (already installed); React 19; Tailwind v4 CSS-first `@theme`. |
| **No emojis in code, logs, or output** | UI-SPEC §5.5 uses Unicode single guillemets (`›` / `‹`) for the drawer toggle — these are sans-serif glyphs, not emoji. No emoji in test names, console.warn args, or aria-labels. |
| **No defensive programming, no over-engineering** | Trust TanStack Query's error/pending states; don't wrap fetches in try/except for "what if". Narrow try/catch only at wire boundaries (matches Phase 6 D-19, Phase 7 inheritance). |
| **Identify root cause before fixing** | Apply when wiring G1: D-15 + D-14 in the SAME plan land both paths (dev rewrite + prod static mount). Don't apply just one and "see if it helps". |
| **Short modules, short functions, clear names** | UI-SPEC §12 budget: ≤120 lines per `.tsx`/`.ts`. The chat sub-tree is intentionally split into 8 small components for this reason. ActionCard is the most at risk — split trade vs watchlist sub-renderers if it grows. |
| **Use `uv` for any backend Python work** | Only one backend edit in this phase (lifespan.py); no new Python deps. |
| **GSD workflow gating** | `/gsd-execute-phase` is the canonical entry point. Direct edits outside the workflow are forbidden unless the user explicitly bypasses. |

## Standard Stack

### Core (NEW for Phase 8)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `recharts` | `^3.8.1` (latest at 2026-04-25) `[VERIFIED: npm view recharts version]` | Treemap (FE-05) + LineChart (FE-06) + ReferenceLine + Tooltip + ResponsiveContainer | SVG-based, React-19-compatible peer, declared by PLAN.md §10 ("Recharts SVG for the P&L chart"), MIT, ~70k weekly downloads, audited and widely deployed. CONTEXT.md D-17 says `^2.x` but the latest stable is 3.x — see "Version Verification" below. |

### Already Installed (consumed by Phase 8)

| Library | Installed Version | Purpose | Phase 8 use |
|---------|------------------|---------|-------------|
| `next` | `16.2.4` `[VERIFIED: package.json]` | App Router, dev server with `rewrites()` proxy, `output: 'export'` | `next.config.mjs` patch (D-15) |
| `react` / `react-dom` | `19.2.4` `[VERIFIED: package.json]` | UI rendering | `'use client'` components, hooks |
| `@tanstack/react-query` | `^5.100.1` `[VERIFIED: package.json]` | REST data fetching with cache invalidation | `useQuery(['portfolio','history'])`, `useQuery(['chat','history'])`, `useMutation(postChat)` |
| `zustand` | `^5.0.12` `[VERIFIED: package.json]` | Live ticker state | extend with `selectedTab` slice + `tradeFlash` slice + `setSelectedTab`/`flashTrade` actions |
| `tailwindcss` (v4) | `^4` `[VERIFIED: package.json]` | Styling tokens via `@theme` | `bg-up`, `bg-down`, `border-l-up`, `border-l-down`, `bg-up/20`, `bg-down/20` (Tailwind v4 derives these from existing CSS-var-backed tokens), `animate-pulse` built-in |
| `lightweight-charts` | `^5.2.0` `[VERIFIED: package.json]` | Phase 7 main chart + sparklines | unchanged in Phase 8; left as-is |

### Test stack (already installed; ResizeObserver stub is NEW)

| Library | Installed | Purpose | Phase 8 use |
|---------|-----------|---------|-------------|
| `vitest` | `^4.1.5` `[VERIFIED: package.json]` | Test runner | All `*.test.tsx` files |
| `@vitejs/plugin-react` | `^6.0.1` `[VERIFIED]` | JSX transform | Already wired in `vitest.config.mts` |
| `@testing-library/react` | `^16.3.2` `[VERIFIED]` | RTL `render` / `screen` / `fireEvent` | Component DOM assertions |
| `@testing-library/jest-dom/vitest` | `^6.9.1` `[VERIFIED]` | `toBeInTheDocument`, `toHaveClass` | Already imported in `vitest.setup.ts` |
| `jsdom` | `^29.0.2` `[VERIFIED]` | Browser-like env | `vitest.config.mts` has `environment: 'jsdom'` |
| **`ResizeObserver` stub** | NEW (4-line pattern) | Stubbing `window.ResizeObserver` so Recharts `<ResponsiveContainer>` doesn't crash in jsdom | Add to `vitest.setup.ts`. See Common Pitfall 5. |

### Alternatives Considered (and rejected by CONTEXT.md)

| Instead of | Could Use | Tradeoff (and why rejected) |
|------------|-----------|------------------------------|
| Recharts `<Treemap>` (D-01) | `react-d3-treemap`, hand-rolled CSS-grid | Extra dep with no payoff for ~10–20 positions, OR reinvents layout math. |
| Recharts `<LineChart>` (D-04) | Lightweight Charts (already installed) | Phase 7 chose Lightweight for canvas-perf on 500ms ticks; P&L chart updates only on 60s/post-trade snapshots, so SVG/Recharts is the right fit AND PLAN.md §10 specifies it. |
| Right-edge push drawer (D-07) | Bottom drawer / overlay drawer | Bottom drawer eats viz space; overlay loses first-impression "AI is here". |
| Default-open drawer (D-07) | Default-collapsed | Loses first-5-second "wow"; demo lands without the AI visible. |
| 3-dot bubble (D-08) | Skeleton placeholder, send-button spinner | Skeleton reads "loading content"; spinner moves the eye to the wrong place. |
| Inline action cards (D-10) | Toast / global notification system | Phase 7 already rejected toasts; carry-forward. Toast for chat would be inconsistent with trade-bar inline-error doctrine. |
| Per-panel skeletons (D-13) | Generic spinner | Spinners read as "broken/slow"; matching-shape skeletons read as "intentional". |

### Installation

```bash
cd frontend
npm install recharts@^3
```

`[VERIFIED: npm view recharts]` Latest is `3.8.1` (published 2026-03-25), peer
`react@^19.0.0` is supported. The lockfile delta is small (Recharts pulls in
clsx, decimal.js-light, es-toolkit, eventemitter3, immer, react-redux,
reselect, tiny-invariant, victory-vendor — most are tiny utility libs).

### Version Verification (D-17 correction)

| Source | Reported version |
|--------|------------------|
| `npm view recharts version` | `3.8.1` `[VERIFIED]` |
| `npm view recharts dist-tags` | `latest: 3.8.1`, `alpha: 3.0.0-alpha.9`, `beta: 3.0.0-beta.2` `[VERIFIED]` |
| `npm view recharts time` (3.8.1) | published 2026-03-25 `[VERIFIED]` |
| `npm view recharts peerDependencies` | `react: '^16.8.0 \|\| ^17 \|\| ^18 \|\| ^19'` `[VERIFIED]` |

**CONTEXT.md D-17 and UI-SPEC §1 say `recharts@^2.x`.** The latest stable line
is 3.x. CLAUDE.md mandates "latest library APIs". The planner should specify
`^3.8.0` (or `^3`) in `package.json`. This is a version bump for currency,
NOT a design change — the Treemap, LineChart, ReferenceLine, Tooltip, and
ResponsiveContainer APIs all work with the same children-composition pattern
in 3.x as in 2.x.

**Recharts 3.x breaking changes that touch Phase 8 surfaces** (per the
[3.0 migration guide][rc3-migrate]):

- `TooltipProps<TValue, TName>` is now `TooltipContentProps<TValue, TName>`
  for typed custom tooltip components (used by `<PnLTooltip>`).
- `ResponsiveContainer.ref.current.current` flattened to `.current` (Phase 8
  doesn't ref the container, so this doesn't bite).
- `CategoricalChartState` removed; `Customized` no longer receives state
  (Phase 8 uses neither).
- `react-smooth` and `recharts-scale` are now internalized (no peer deps to
  worry about).
- Accessibility is on by default in 3.x (good for Phase 8 — `<Heatmap>` and
  `<PnLChart>` get a11y for free).

None of the breaking changes touch the planned implementation. The minor
import update is `TooltipContentProps` if the planner wants strict typing on
the custom P&L tooltip.

[rc3-migrate]: https://github.com/recharts/recharts/wiki/3.0-migration-guide

## Architecture Patterns

### System Architecture Diagram

Data flow from browser entry through the new Phase 8 surfaces:

```
                                                      ┌────────────────────┐
  Browser load ─────────────────────────────────────▶│ Same-origin /:8000 │
                                                      │ (FastAPI process)  │
                                                      └─────────┬──────────┘
                                                                │
                                          ┌─────────────────────┴──────────┐
                                          │ Route precedence (D-14)        │
                                          │   /api/health   ─▶ inline      │
                                          │   /api/stream/* ─▶ SSE router  │
                                          │   /api/portfolio/* ─▶ router   │
                                          │   /api/watchlist/*  ─▶ router  │
                                          │   /api/chat/*       ─▶ router  │
                                          │   /              ─▶ StaticFiles│
                                          │                       (catch-  │
                                          │                       all,     │
                                          │                       LAST)    │
                                          └────────────────────────────────┘
                                                                │
                                                                ▼
                          ┌──────────────────────────────────────────────────────────┐
                          │  frontend/out/index.html  (Next.js static export)        │
                          │   ├─ <Providers> (TanStack Query + PriceStreamProvider)  │
                          │   └─ <Terminal>                                          │
                          │       ├─ flex row outer                                  │
                          │       ├─ left: 3-col grid (Phase 7)                      │
                          │       │   ├─ <Watchlist /> (Phase 7)                     │
                          │       │   ├─ center: Header + <TabBar /> + tabbed surface│
                          │       │   │   ├─ <MainChart />  (Phase 7)                │
                          │       │   │   ├─ <Heatmap />    (NEW — FE-05)            │
                          │       │   │   └─ <PnLChart />   (NEW — FE-06)            │
                          │       │   └─ right: <PositionsTable /> + <TradeBar />    │
                          │       └─ right-edge: <ChatDrawer />     (NEW — FE-09)    │
                          │                       └─ <ChatHeader />                  │
                          │                       └─ <ChatThread />                  │
                          │                            ├─ <ChatMessage /> (loop)     │
                          │                            │    └─ <ActionCardList />    │
                          │                            │         └─ <ActionCard />   │
                          │                            └─ <ThinkingBubble /> (cond.) │
                          │                       └─ <ChatInput />                   │
                          └──────────────────────────────────────────────────────────┘
                                                                │
            ┌───────────────────────────────────────────────────┴──────────────────────────┐
            │                                                                              │
            ▼                                                                              ▼
  Live price ticks (SSE)                                                  REST queries (TanStack Query)
  EventSource → usePriceStore                                             ├─ ['portfolio']    /api/portfolio
  selectors:                                                              ├─ ['portfolio','history'] /api/portfolio/history (NEW)
   - selectTick(t)                                                        ├─ ['watchlist']    /api/watchlist (Phase 7)
   - selectFlash(t)        — 500ms price flash                            └─ ['chat','history']     /api/chat/history (NEW)
   - selectTradeFlash(t)   — 800ms trade flash (NEW)                      mutations:
   - selectSelectedTicker  — main chart driver                            └─ postChat → /api/chat (NEW)
   - selectSelectedTab     — tabbed center column (NEW)                       └─ on resolve:
   - selectSparkline(t)                                                            ├─ append assistant msg locally
                                                                                   ├─ flashTrade(ticker, 'up') for each `executed`
                                                                                   └─ queryClient.invalidateQueries(['portfolio'])
```

### Recommended Project Structure (additions only)

```
frontend/src/
├── app/
│   └── globals.css                  (EXTEND: @keyframes + reduced-motion block)
├── components/
│   ├── chat/                        (NEW)
│   │   ├── ChatDrawer.tsx
│   │   ├── ChatHeader.tsx
│   │   ├── ChatThread.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ActionCardList.tsx
│   │   ├── ActionCard.tsx
│   │   ├── ChatInput.tsx
│   │   ├── ThinkingBubble.tsx
│   │   └── *.test.tsx
│   ├── portfolio/                   (NEW)
│   │   ├── Heatmap.tsx
│   │   ├── HeatmapCell.tsx
│   │   ├── PnLChart.tsx
│   │   ├── PnLTooltip.tsx
│   │   └── *.test.tsx
│   ├── skeleton/                    (NEW)
│   │   └── SkeletonBlock.tsx
│   └── terminal/
│       ├── Terminal.tsx             (UPDATE: wrap grid in flex row + drawer; insert TabBar + tabbed surface)
│       └── TabBar.tsx               (NEW)
├── lib/
│   ├── api/
│   │   ├── portfolio.ts             (EXTEND: getPortfolioHistory)
│   │   └── chat.ts                  (NEW: getChatHistory + postChat)
│   ├── price-store.ts               (EXTEND: selectedTab slice, tradeFlash slice, flashTrade action, selectTradeFlash selector)
│   └── fixtures/                    (NEW — for tests)
│       ├── portfolio.ts
│       ├── history.ts
│       └── chat.ts
├── test-utils.tsx                   (existing — renderWithQuery)
└── vitest.setup.ts                  (EXTEND: vi.stubGlobal('ResizeObserver', ...))

frontend/
└── next.config.mjs                  (UPDATE: skipTrailingSlashRedirect: true)

backend/
└── app/
    └── lifespan.py                  (UPDATE: app.mount("/", StaticFiles(...), html=True) AFTER all routers)
```

### Pattern 1: Recharts `<Treemap>` with Custom `content` Prop

**What:** Render rectangles via a custom function component so the cell can
include the binary up/down fill, the ticker label, and the signed P&L %.

**When to use:** FE-05 heatmap. Default Recharts cell rendering would only
render a fill — we need ticker + signed P&L % labels with the threshold-hide
behavior from D-03.

**Key prop signature** (from Recharts 3.x source, `[CITED:
github.com/recharts/recharts/blob/main/src/chart/Treemap.tsx]`):

```typescript
export interface TreemapNode {
  children: ReadonlyArray<TreemapNode> | null;
  value: number;
  depth: number;
  index: number;
  x: number;
  y: number;
  width: number;
  height: number;
  name: string;
  tooltipIndex: TooltipIndex;
  root?: TreemapNode;
  [k: string]: unknown;   // ← custom data fields are merged in here
}

type TreemapContentType =
  | ReactNode
  | ((props: TreemapNode) => React.ReactElement);
```

**Custom data fields are accessible directly on the node** (they're spread
into the same object as `x`, `y`, `width`, `height`). For Phase 8:

```typescript
// data shape passed to <Treemap data={treeData} dataKey="weight">
type HeatmapDatum = {
  ticker: string;
  weight: number;        // dataKey — drives sizing
  pnlPct: number;        // bound to label
  isUp: boolean;         // drives fill choice
  isCold: boolean;       // cold-cache fallback path
};

// HeatmapCell receives these fields directly because Recharts merges the
// datum into the TreemapNode it passes to the content function.
function HeatmapCell({
  x, y, width, height,
  ticker, pnlPct, isUp, isCold,
}: TreemapNode & HeatmapDatum) { /* ... */ }
```

**Example:**

```tsx
// Source: UI-SPEC §5.3 + Recharts 3.x docs
<ResponsiveContainer width="100%" height="100%">
  <Treemap
    data={treeData}                     // HeatmapDatum[]
    dataKey="weight"                    // size driver
    stroke="#30363d"
    strokeWidth={1}
    content={<HeatmapCell />}           // Recharts clones with TreemapNode props
    onClick={(node) => {                // node is TreemapNode + datum
      usePriceStore.getState().setSelectedTicker((node as any).ticker);
      usePriceStore.getState().setSelectedTab('chart');
    }}
    isAnimationActive
    animationDuration={300}
  />
</ResponsiveContainer>
```

**Threshold-hide labels:**

```tsx
function HeatmapCell({ x, y, width, height, ticker, pnlPct, isUp, isCold }) {
  const fill = isCold
    ? 'var(--color-surface-alt)'
    : isUp ? 'var(--color-up)' : 'var(--color-down)';
  const showLabel = width >= 60 && height >= 32;
  return (
    <g cursor="pointer">
      <rect x={x} y={y} width={width} height={height}
            fill={fill} stroke="#30363d" />
      {showLabel && (
        <>
          <text x={x + 8} y={y + 18} fill="#ffffff" fontWeight={600} fontSize={14}>
            {ticker}
          </text>
          <text x={x + 8} y={y + 36} fill="#ffffff"
                fontFamily="ui-monospace" fontSize={12}>
            {formatSignedPercent(pnlPct)}
          </text>
        </>
      )}
      <title>{ticker}: {formatSignedPercent(pnlPct)}</title>{/* a11y */}
    </g>
  );
}
```

### Pattern 2: Recharts `<LineChart>` + `<ReferenceLine>` + Custom `<Tooltip>`

**What:** Compose LineChart with one Line, X/Y axes, CartesianGrid, a horizontal
ReferenceLine at y=10000, and a custom Tooltip via the `content` prop.

**When to use:** FE-06 P&L chart.

**Key APIs** `[CITED: recharts.github.io/en-US/api/LineChart,
recharts.github.io/en-US/api/ReferenceLine]`:

| Component | Critical props |
|-----------|---------------|
| `<LineChart>` | `data: ReadonlyArray<DataPoint>`, `margin` |
| `<Line>` | `dataKey`, `type='monotone'`, `stroke`, `strokeWidth`, `dot={false}`, `isAnimationActive={false}` |
| `<XAxis>` | `dataKey`, `stroke`, `tickFormatter` |
| `<YAxis>` | `stroke`, `tickFormatter`, `domain={['auto','auto']}` |
| `<CartesianGrid>` | `stroke`, `strokeDasharray="2 2"` |
| `<ReferenceLine>` | `y={number}`, `stroke`, `strokeDasharray="4 4"`, `strokeOpacity={0.4}`, `ifOverflow="extendDomain"` |
| `<Tooltip>` | `content={<PnLTooltip />}` |
| `<ResponsiveContainer>` | `width="100%"`, `height="100%"` (parent must have explicit height) |

**Custom Tooltip TypeScript signature (Recharts 3.x)** — `[CITED:
github.com/recharts/recharts source]`:

```typescript
import type { TooltipContentProps } from 'recharts';   // 3.x: was TooltipProps in 2.x

function PnLTooltip(
  { active, payload, label }: TooltipContentProps<number, string>
) {
  if (!active || !payload?.length) return null;
  // payload[0].payload is the original data point object
  const { recorded_at, total_value } = payload[0].payload as {
    recorded_at: string;
    total_value: number;
  };
  const delta = total_value - 10000;
  return (
    <div className="bg-surface-alt border border-border-muted rounded p-2 text-sm">
      <div className="text-foreground-muted">{formatTimestamp(recorded_at)}</div>
      <div className="font-mono tabular-nums text-foreground">
        {formatPrice(total_value)}
      </div>
      <div className={`font-mono tabular-nums ${delta >= 0 ? 'text-up' : 'text-down'}`}>
        {formatSignedMoney(delta)} vs $10k
      </div>
    </div>
  );
}
```

**Stroke flip via state (D-06):**

```tsx
const lastTotal = snapshots.length ? snapshots[snapshots.length - 1].total_value : 10000;
const stroke = lastTotal >= 10000 ? 'var(--color-up)' : 'var(--color-down)';
// ...
<Line
  type="monotone"
  dataKey="total_value"
  stroke={stroke}
  strokeWidth={2}
  dot={false}
  isAnimationActive={false}   // chart updates feel instant on snapshot insert
/>
```

### Pattern 3: Tailwind v4 Push-Layout Drawer (Width Transition, NOT Overlay)

**What:** Right-edge drawer that pushes the workspace left when open and
collapses to an icon strip on toggle. UI-SPEC §5.1 locks it as a `flex flex-row`
with the drawer as a sibling `<aside>` whose `width` transitions.

**Why width-transition over `grid-template-columns` transition:** A `width`
transition on a single flex child is universally supported and animates
smoothly in every browser. `grid-template-columns` transitions are CSS
spec-allowed but inconsistently animated (Safari has historically not
interpolated keyword-vs-fr values cleanly). The flex sibling pattern Just
Works.

**Skeleton:**

```tsx
// Outer Terminal layout (UPDATE — wraps existing 3-col grid)
<main className="flex flex-row min-h-screen min-w-[1024px] bg-surface text-foreground">
  <div className="flex-1 min-w-0 p-6">
    {/* existing 3-col grid stays here, with TabBar+tabbed surface in center */}
    <div className="grid grid-cols-[320px_1fr_360px] gap-6">
      {/* ... */}
    </div>
  </div>
  <ChatDrawer />
</main>

// ChatDrawer
<aside
  className={`
    bg-surface-alt border-l border-border-muted flex flex-col
    transition-[width] duration-300 ease-out
    ${isOpen ? 'w-[380px]' : 'w-12'}
  `}
  aria-label="AI assistant"
>
  <ChatHeader isOpen={isOpen} onToggle={() => setOpen(!isOpen)} />
  {isOpen && (
    <>
      <ChatThread />
      <ChatInput />
    </>
  )}
</aside>
```

**Why mount the inner content conditionally on `isOpen`:** Avoids rendering
the chat thread (and its scroll container, mutation hooks, history fetch)
when collapsed. Simpler than overflow-hidden + opacity tricks.

**Trade-off:** mounting/unmounting the thread on toggle re-runs the
`useQuery(['chat','history'])` cache hit, but TanStack Query holds the data
in memory after first resolve so this is essentially free. The `<ThinkingBubble>`
state is local to the drawer-open lifetime, which is fine — toggling closed
while a request is in flight cancels nothing visually but the request
continues; on re-open, the assistant reply is in the history fetch when it
refetches.

### Pattern 4: TanStack Query Mutation with Optimistic Local Append + Cache Invalidation

**What:** `postChat` mutation that:

1. Optimistically appends the user message to a local array (so the bubble
   shows immediately).
2. Renders `<ThinkingBubble>` while `mutation.isPending`.
3. On success: appends the assistant message + actions, marks each `executed`
   action `_fresh: true` for the pulse, fires `flashTrade()` for each `executed`
   trade, calls `queryClient.invalidateQueries(['portfolio'])` to re-fetch
   positions/cash for the header + positions table.
4. On error: shows inline error below the input; user message stays.

**Why local-append instead of optimistic cache update via TanStack:** Chat
history is append-only and the order matters. Mixing optimistic `setQueryData`
with the eventual server response (which may include slightly different
created_at timestamps) creates jitter. A simple `useState<ChatMessageOut[]>`
local list overlaid on the `useQuery` result is straightforward.

**Skeleton:**

```tsx
const queryClient = useQueryClient();
const [pending, setPending] = useState<ChatMessageOut[]>([]);  // optimistic user msgs
const [fresh, setFresh] = useState<ChatMessageOut[]>([]);      // server-resolved tail

const historyQuery = useQuery({
  queryKey: ['chat', 'history'],
  queryFn: getChatHistory,
});

const mutation = useMutation({
  mutationFn: (content: string) => postChat({ message: content }),
  onMutate: (content) => {
    const optimistic: ChatMessageOut = {
      id: `pending-${Date.now()}`,
      role: 'user',
      content,
      actions: null,
      created_at: new Date().toISOString(),
    };
    setPending((p) => [...p, optimistic]);
    return { optimistic };
  },
  onSuccess: (response) => {
    const assistant: ChatMessageOut = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: response.message,
      actions: { trades: response.trades, watchlist_changes: response.watchlist_changes },
      created_at: new Date().toISOString(),
    };
    setFresh((f) => [...f, assistant]);
    // Trade-flash for each executed trade (D-12)
    for (const trade of response.trades) {
      if (trade.status === 'executed') {
        usePriceStore.getState().flashTrade(trade.ticker, 'up');
      }
    }
    // Invalidate portfolio so positions table + header re-render with new cash/qty
    queryClient.invalidateQueries({ queryKey: ['portfolio'] });
  },
  onError: () => {
    // Inline error rendered below ChatInput; pending user msg STAYS so the
    // user can see what they sent.
  },
});

// merged thread
const messages = [
  ...(historyQuery.data?.messages ?? []),
  ...pending,
  ...fresh,
];
```

**Auto-scroll on new message (UI-SPEC §5.5):**

```tsx
const threadRef = useRef<HTMLDivElement>(null);
useLayoutEffect(() => {
  const el = threadRef.current;
  if (!el) return;
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
  if (distanceFromBottom <= 120) {
    el.scrollTop = el.scrollHeight;
  }
}, [messages.length, mutation.isPending]);
```

`useLayoutEffect` (NOT `useEffect`) so the scroll lands before paint and the
user never sees the "old" position briefly.

### Pattern 5: Zustand `tradeFlash` Slice (Separate from `flashDirection`)

**What:** Add a NEW transient slice `tradeFlash: Record<string, 'up' | 'down'>`
to `usePriceStore`, with a `flashTrade(ticker, dir)` action and
`selectTradeFlash(ticker)` selector. Mirrors Phase 7's `flashDirection` /
`selectFlash` pattern with **distinct duration (800ms vs 500ms) and distinct
opacity (`/20` vs `/10`)** so the two flashes never visually collide on the
same row.

**Why a SEPARATE slice (not reuse `flashDirection`):**

- Phase 7 D-01 has 500ms timeout machinery wired specifically for price ticks
  (`flashTimers` map, FLASH_MS constant). Reusing it for trade-flash would
  require a per-ticker "kind" tag, OR overriding price-flash duration when a
  trade fires — both expand the price-store API surface and create coupling
  between unrelated triggers.
- Distinct slices let the position row apply both classes simultaneously when
  a price tick lands during an in-flight trade flash (rare but possible — the
  CSS rules `.bg-up/10` and `.bg-up/20` are independent and the eye sees
  whichever has the higher alpha at that instant).
- `setTimeout` map keyed by ticker mirrors Phase 7 `flashTimers` exactly.

**Skeleton (extends `frontend/src/lib/price-store.ts`):**

```typescript
const tradeFlashTimers = new Map<string, ReturnType<typeof setTimeout>>();
const TRADE_FLASH_MS = 800;

interface PriceStoreState {
  // ... existing slices unchanged
  selectedTab: 'chart' | 'heatmap' | 'pnl';
  tradeFlash: Record<string, 'up' | 'down'>;
  setSelectedTab: (t: 'chart' | 'heatmap' | 'pnl') => void;
  flashTrade: (ticker: string, dir: 'up' | 'down') => void;
}

flashTrade: (ticker, dir) => {
  set((s) => ({ tradeFlash: { ...s.tradeFlash, [ticker]: dir } }));
  const prev = tradeFlashTimers.get(ticker);
  if (prev) clearTimeout(prev);
  const handle = setTimeout(() => {
    set((s) => {
      const cleared = { ...s.tradeFlash };
      delete cleared[ticker];
      return { tradeFlash: cleared };
    });
    tradeFlashTimers.delete(ticker);
  }, TRADE_FLASH_MS);
  tradeFlashTimers.set(ticker, handle);
},

selectedTab: 'chart',
setSelectedTab: (t) => set({ selectedTab: t }),
```

**Don't forget:** the `disconnect()` and `reset()` methods MUST clear
`tradeFlashTimers` AND empty the `tradeFlash` slice, mirroring Phase 7's
`flashTimers` cleanup. Otherwise Vitest tests that call `reset()` between
cases will leak timers.

### Pattern 6: CSS `@keyframes` Pulse Animations + `prefers-reduced-motion`

**What:** Pure CSS `@keyframes` for the action-card pulse and the 3-dot
thinking bubble. Live in `globals.css`. No animation library.

**Action-card pulse (UI-SPEC §5.7):**

```css
@keyframes action-pulse-up {
  0%   { background-color: rgb(38 166 154 / 0.30); }
  100% { background-color: rgb(38 166 154 / 0.00); }
}
@keyframes action-pulse-down {
  0%   { background-color: rgb(239 83 80 / 0.30); }
  100% { background-color: rgb(239 83 80 / 0.00); }
}
.action-pulse-up   { animation: action-pulse-up   800ms ease-out 1; }
.action-pulse-down { animation: action-pulse-down 800ms ease-out 1; }
```

**Thinking-bubble dots (UI-SPEC §5.9):**

```css
.thinking-dot {
  width: 6px; height: 6px; border-radius: 9999px;
  background-color: var(--color-foreground-muted);
  animation: thinking-pulse 1200ms infinite ease-in-out;
}
.thinking-dot:nth-child(2) { animation-delay: 200ms; }
.thinking-dot:nth-child(3) { animation-delay: 400ms; }

@keyframes thinking-pulse {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30%           { opacity: 1.0; transform: translateY(-2px); }
}
```

**Reduced-motion fallback (UI-SPEC §7):**

```css
@media (prefers-reduced-motion: reduce) {
  .action-pulse-up,
  .action-pulse-down,
  .thinking-dot,
  .animate-pulse,
  .transition-colors,
  .transition-\[width\] {
    animation: none !important;
    transition: none !important;
  }
}
```

The `transition-\[width\]` selector escapes the bracket — Tailwind v4 emits
`transition-property: width` under that exact selector.

### Pattern 7: Skeleton-Block Primitive (Pure CSS, No Library)

**What:** A shared `<SkeletonBlock>` component using Tailwind v4 built-in
`animate-pulse`. UI-SPEC §6 + §12 spell out the per-panel shapes.

```tsx
// src/components/skeleton/SkeletonBlock.tsx
export function SkeletonBlock({ className }: { className?: string }) {
  return (
    <div className={`bg-border-muted/50 rounded animate-pulse ${className ?? ''}`} />
  );
}
```

**Per-panel skeleton trigger (UI-SPEC §6):** gated on TanStack Query's
`isPending`. For the heatmap and P&L chart, this works directly; for the chat
thread, gate on `historyQuery.isPending`.

```tsx
// in <Heatmap>
const { data, isPending } = useQuery({ queryKey: ['portfolio'], queryFn: fetchPortfolio });
if (isPending) return <SkeletonBlock className="flex-1 w-full" />;
if (!data || data.positions.length === 0) return <EmptyState ... />;
return <Treemap ... />;
```

### Pattern 8: FastAPI `StaticFiles` Mount AFTER All API Routers

**What:** `app.mount("/", StaticFiles(directory="frontend/out", html=True))`
appended to the lifespan AFTER every `app.include_router(...)` call.

**Why mount-AFTER matters:** FastAPI/Starlette match routes in registration
order. A mount at `/` is a catch-all — every path that isn't an existing
route falls through to it. If you mount BEFORE the API routers, every
`/api/health`, `/api/portfolio`, `/api/stream/prices` request would be
shadowed by the static-file fallback (and probably 404 because no file
matches that path).

**Why `html=True` matters:** Without it, hitting `/` returns 404 because no
file at `directory/` matches the empty path. With `html=True`, Starlette's
StaticFiles middleware serves `directory/index.html` for `/` and tries
`directory/<path>/index.html` for sub-paths. This is exactly the behavior we
want for a Next.js static export with `trailingSlash: true`.

**Concrete diff to `backend/app/lifespan.py`:**

```python
# at the top
from fastapi.staticfiles import StaticFiles

# inside lifespan, after the LAST app.include_router(...) call:
app.include_router(create_chat_router(conn, cache, source, chat_client))   # line 78 (existing)

# NEW (D-14): mount static after all routers are registered
app.mount(
    "/",
    StaticFiles(directory="frontend/out", html=True),
    name="frontend",
)
```

**Path resolution caveat:** the relative path `frontend/out` is resolved from
the **current working directory at uvicorn startup**, NOT from the package
root. The canonical run command is `cd backend && uv run uvicorn
app.main:app`, so `cwd = repo/backend/`. From there, `frontend/out` resolves
to `repo/backend/frontend/out` — which DOESN'T EXIST. The actual export is
at `repo/frontend/out`.

**Two options the planner should pick:**

1. **Compute the path from the package** (preferred): use
   `pathlib.Path(__file__).resolve().parents[2] / "frontend" / "out"` to
   resolve the static directory regardless of cwd.
2. **Document the cwd contract:** require running uvicorn from the repo root
   (`uv run --project backend uvicorn app.main:app`) and use the relative
   path. This is more brittle.

Phase 9 (OPS-01) ships the Dockerfile that copies `frontend/out/` into
`backend/static/` — at that point the path becomes static-relative-to-package
and the cwd brittleness goes away. For Phase 8 the planner should choose
option 1 (path from `__file__`) so dev-mode `uv run uvicorn app.main:app`
works without cwd discipline.

`[CITED: starlette.dev/staticfiles/]` — `html=True` automatically loads
`index.html` for directories if such file exists; in HTML mode, `404.html` is
shown for missing files. Our Next.js export contains both `index.html` and
`404.html` (verified — `ls frontend/out/`).

### Pattern 9: Vitest + RTL + MockEventSource + ResizeObserver Stub

**What:** Inherit Phase 6 D-test patterns. ADD a global `ResizeObserver` stub
to `vitest.setup.ts` so Recharts `<ResponsiveContainer>` doesn't crash in
jsdom.

**Existing Phase 6 / Phase 7 harness** (verified in
`frontend/vitest.config.mts`, `frontend/vitest.setup.ts`,
`frontend/src/components/terminal/PositionsTable.test.tsx`):

- jsdom env, globals, plugin-react, tsconfig-paths.
- `@testing-library/jest-dom/vitest` imported in `vitest.setup.ts`.
- Test pattern: `vi.stubGlobal('fetch', vi.fn().mockResolvedValue(...))` for
  REST stubs.
- `usePriceStore.getState().reset()` in `beforeEach` to clear store between
  tests.
- `vi.unstubAllGlobals()` in `afterEach`.
- `renderWithQuery(...)` from `src/test-utils.tsx` wraps components in a
  fresh `QueryClientProvider`.

**ResizeObserver stub** — `[CITED: greenonsoftware.com,
jsdom-testing-mocks]`:

```typescript
// vitest.setup.ts (extend existing file)
import '@testing-library/jest-dom/vitest';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);
```

This allows Recharts `<ResponsiveContainer>` to mount without throwing.
However, the container will still report `width=0 height=0` in jsdom because
there's no real layout engine. **Two complementary mitigations:**

1. **Mock `ResponsiveContainer` to a fixed size**, OR
2. **Render the chart with explicit `width` and `height`** in the test, OR
3. **Assert against the data-driven props** (e.g., `data` prop on
   `<Treemap>`) rather than against rendered SVG geometry.

Option 3 is the cleanest for Phase 8's tests because the requirements are
"renders one rect per position with binary coloring" — that can be asserted
by inspecting the data fed to the Treemap, not by inspecting actual rect
geometry. UI-SPEC §13 row 1 ("Heatmap renders one rect per position with
binary coloring") + row 5/6 ("PnLChart line stroke is up/down...") all map
to props-on-the-rendered-component assertions, not pixel positions.

For the click-test (UI-SPEC §13 row 2 — "Heatmap click on rect dispatches
setSelectedTicker"), an alternative is to test the click handler in
isolation: extract `handleHeatmapClick(node)` as a pure function and unit-test
it with a synthetic `TreemapNode` argument. This is the planner's call;
either approach is acceptable.

**Concrete: mock Recharts ResponsiveContainer for tests** if option 3 isn't
enough:

```typescript
// In a specific test file or vitest.setup.ts
vi.mock('recharts', async () => {
  const original = await vi.importActual<typeof import('recharts')>('recharts');
  return {
    ...original,
    ResponsiveContainer: ({ children }: { children: React.ReactElement }) =>
      React.cloneElement(children, { width: 800, height: 600 }),
  };
});
```

`[VERIFIED: jsdom-testing-mocks docs]` This mock pattern is the standard
escape hatch for Recharts in jsdom and matches the Mantine and Chakra UI
testing guides.

### Anti-Patterns to Avoid

- **Re-opening an EventSource from any new component.** The chat panel,
  heatmap, and P&L chart all subscribe to existing store selectors only.
  Confirmed in CONTEXT.md `<code_context>` and UI-SPEC §15 "executor".
- **Toast / global notification system.** Inline action cards (D-10, D-11)
  are the entire user-feedback surface. Trade-bar inline-error from Phase 7
  D-07 stays. UI-SPEC §15 explicitly forbids.
- **Modifying any Phase 1–5 backend contract.** The chat, portfolio,
  watchlist, and SSE contracts are stable from prior phases. Only one
  backend edit in Phase 8: the StaticFiles mount.
- **Adding chart libraries beyond `lightweight-charts` + `recharts`.** No
  d3, no chart.js. CONTEXT.md `<code_context>` anti-patterns.
- **Mounting `StaticFiles` at `/` BEFORE API routers.** Would shadow every
  `/api/*` route. See Pattern 8.
- **Skipping the `html=True` flag.** Without it, hitting `/` returns 404.
  See Pattern 8.
- **Reusing `flashDirection` for trade flash.** Distinct slice required so
  500ms price flash and 800ms trade flash never collide. See Pattern 5.
- **Using `useEffect` (not `useLayoutEffect`) for chat thread auto-scroll.**
  Causes a single-frame flicker where the user sees the "old" scroll
  position. See Pattern 4.
- **Hand-rolling `recharts@^2` when `^3` is current.** UI-SPEC §1 and
  CONTEXT.md D-17 say `^2.x`; the latest is `3.8.1`. CLAUDE.md mandates
  latest APIs. See "Version Verification".
- **Forgetting the `prefers-reduced-motion` block in globals.css.** UI-SPEC
  §7 lists this as mandatory.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Treemap layout (squarified rectangles) | Custom CSS-grid heatmap | Recharts `<Treemap>` | Layout math (squarified algorithm), tooltip, click events all free |
| Time-series line chart with reference line | SVG `<polyline>` + `<line>` by hand | Recharts `<LineChart>` + `<ReferenceLine>` | Axis ticks, scaling, padding domain, tooltip all built-in |
| Custom tooltip positioning + portal | DIY `<div>` with absolute positioning | Recharts `<Tooltip content={...}>` | Recharts handles cursor follow, axis snap, edge clipping |
| Drawer slide animation | DIY transform + state machine | `transition-[width] duration-300` (Tailwind) | One CSS line; no JS animation framework needed |
| Skeleton pulse | DIY CSS `@keyframes opacity` | Tailwind `animate-pulse` (built-in) | Already in v4; consistent with the rest of the design system |
| 3-dot thinking bubble | A library like `react-loading` | Pure CSS `@keyframes` (3 dots, staggered) | < 20 lines of CSS, no dep |
| Auto-scroll-to-bottom in chat thread | A library like `react-scroll-to-bottom` | `useLayoutEffect` + `el.scrollTop = el.scrollHeight` (with 120px-from-bottom guard) | < 10 lines, exactly what UI-SPEC §5.5 specifies |
| Reactive cache invalidation across panels | Manual `setState` calls everywhere on trade success | `queryClient.invalidateQueries(['portfolio'])` | Header, positions table, trade bar all re-render naturally |
| Mock `EventSource` for tests | A library like `eventsourcemock` | The handwritten `MockEventSource` from Phase 6 | Already wired via `__setEventSource` DI in `price-store.ts` |
| Mock `ResizeObserver` for tests | A library like `resize-observer-polyfill` (in tests) | 4-line `class ResizeObserverStub { observe() {} ... }` + `vi.stubGlobal` | Lightest-weight mock; matches the Mantine/Chakra testing pattern |

**Key insight:** every "wow" element in Phase 8 has a stock library or a 10-
line idiomatic pattern. The agentic-AI animation choreography (D-12) is the
ONLY piece that needed a custom design — and that's already specified down
to the millisecond in UI-SPEC §7. Don't write a state machine for it; use
two `setTimeout` calls and a CSS class.

## Runtime State Inventory

Phase 8 is a greenfield-feature phase, not a rename or migration. No runtime
state needs auditing. The "Runtime State Inventory" section is therefore
omitted intentionally — there's nothing to inventory.

(For the record: the only data-shape changes are additions — `selectedTab`
and `tradeFlash` slices in `usePriceStore`. Both are in-memory, transient,
non-persisted, browser-tab-local. Nothing in SQLite, no n8n workflows, no
Windows scheduled tasks, no SOPS keys, no installed packages, no build
artifacts touched.)

## Common Pitfalls

### Pitfall 1: Recharts Treemap labels disappear silently on small cells

**What goes wrong:** Cells smaller than ~60×32 px render the rect but no
visible text, even when your `content` function tries to draw `<text>`. The
text IS rendered but is too small for screen readers or hover.

**Why it happens:** Recharts default behavior on small treemap rectangles is
to ALWAYS pass the data to your `content` function — Recharts itself doesn't
hide labels. If you don't add a threshold check, your `<text>` elements are
clipped or visually unreadable.

**How to avoid:** UI-SPEC §5.3 already locks the threshold at `width >= 60
&& height >= 32`. Use this guard in `<HeatmapCell>` (Pattern 1 above).

**Warning signs:** All-positions tests pass with 3 large positions, then a
20-position fixture has labels that "look weird". Always test with a fixture
that mixes large and small weights.

### Pitfall 2: `<ResponsiveContainer>` collapses to 0×0 in jsdom

**What goes wrong:** Chart children are present in the React tree but
nothing renders inside `<ResponsiveContainer>` because jsdom doesn't run
`ResizeObserver` callbacks. Every Recharts test fails to find any visible
SVG content.

**Why it happens:** `<ResponsiveContainer>` reads element dimensions via
`ResizeObserver`. In jsdom, `ResizeObserver` is undefined OR (with a polyfill)
returns 0×0 because there's no layout.

**How to avoid:** Stub `ResizeObserver` globally in `vitest.setup.ts`
(Pattern 9). Where geometry-level assertions are needed, additionally mock
`ResponsiveContainer` to inject fixed `width`/`height`. Where data-driven
assertions are enough, just stub `ResizeObserver` and assert against `data`
props on the Treemap/LineChart.

**Warning signs:** `screen.getByText('AAPL')` fails inside a Heatmap test
even though `data` clearly contains an AAPL entry. The test is hitting
collapsed-container, not a real bug.

### Pitfall 3: `skipTrailingSlashRedirect` known issue with NextURL stripping

**What goes wrong:** Documented Next.js issue
[#54984][gh-54984] / [#66738][gh-66738] — `NextURL` ignores
`config.skipTrailingSlashRedirect` and only checks `info.trailingSlash`,
which can cause trailing-slash stripping in middleware/proxy code paths
even when the flag is set.

[gh-54984]: https://github.com/vercel/next.js/issues/54984
[gh-66738]: https://github.com/vercel/next.js/issues/66738

**Why it happens:** The flag was implemented in v13.1 for the page-routing
layer but not consistently propagated through all Next internals.

**How to avoid:** This issue affects **middleware/proxy code paths
specifically**. Phase 8 has no middleware/proxy file (the existing
`next.config.mjs` only uses `rewrites()`, not `proxy.ts`). The
`skipTrailingSlashRedirect: true` setting works correctly for D-15's stated
purpose: stopping the dev server from issuing a 308 redirect that the
FastAPI rewrite chain trips over.

**Warning signs:** If a future phase adds a `proxy.ts` (e.g., for auth in
v2), the trailing-slash-stripping bug may resurface. For Phase 8 (no proxy
file), D-15 is sound.

### Pitfall 4: StaticFiles mount route precedence

**What goes wrong:** Mounting `StaticFiles(directory="frontend/out", html=True)`
at `/` BEFORE the API routers means every `/api/health`, `/api/portfolio`,
`/api/stream/prices` request is intercepted by the static-file middleware,
which 404s because no matching file exists. The API "stops working" silently
in production.

**Why it happens:** FastAPI/Starlette match registered routes in
registration order. A `mount("/")` is a catch-all — first match wins, and
with `html=True` the catch-all consumes everything, returning the index for
unknown paths or 404 from `404.html`.

**How to avoid:** Mount StaticFiles **AFTER** every `app.include_router(...)`
call. Phase 8's `lifespan.py` edit goes at the very end of the lifespan
startup block, after `create_chat_router` is mounted. UI-SPEC §15 calls this
"non-negotiable".

**Warning signs:** `curl http://localhost:8000/api/health` returns HTML
(the index page) instead of `{"status": "ok"}`. Confirms route shadowing.

### Pitfall 5: jsdom `useLayoutEffect` warning + auto-scroll

**What goes wrong:** Test renders the chat thread component, console warns
"useLayoutEffect does nothing on the server"; or the auto-scroll assertion
flakes because RTL's microtask doesn't run the layout effect synchronously.

**Why it happens:** `useLayoutEffect` is intended for browser layout. In
jsdom, it runs after paint via the requestAnimationFrame polyfill, which
RTL's `act()` may not auto-flush.

**How to avoid:** UI-SPEC §13 doesn't mandate testing the auto-scroll
mechanic; the chat thread tests cover "renders messages on mount" and "shows
ThinkingBubble while in flight". Skip the auto-scroll geometry assertion in
tests; the `useLayoutEffect` runs in real browsers as intended.

If a smoke test of auto-scroll behavior is desired, use
`await waitFor(() => expect(threadEl.scrollTop).toBeGreaterThan(0))` and
accept that the test is best-effort, not deterministic.

**Warning signs:** Flaky tests that pass locally but fail in CI; or the
`scrollTop` assertion returns 0 when the test expects a positive number.

### Pitfall 6: Recharts 3.x `TooltipContentProps` type breakage

**What goes wrong:** Custom tooltip component types `TooltipProps<number,
string>` from `recharts`, TypeScript error: "Module '"recharts"' has no
exported member 'TooltipProps'."

**Why it happens:** Recharts 3.x renamed `TooltipProps` to
`TooltipContentProps` for typed custom tooltips.
`[CITED: github.com/recharts/recharts/wiki/3.0-migration-guide]`

**How to avoid:** Import `TooltipContentProps` instead. See Pattern 2 code
sample.

**Warning signs:** TypeScript build error referencing `TooltipProps` after
upgrading to `recharts@^3`.

## Code Examples

Verified patterns from official sources and in-repo prior art:

### Heatmap weight + P&L % computation

```typescript
// Source: UI-SPEC §5.3 + Phase 7 PositionRow client-side P&L pattern
function buildHeatmapData(
  positions: PositionOut[],
  getTick: (ticker: string) => Tick | undefined,
): HeatmapDatum[] {
  const enriched = positions.map((p) => {
    const tick = getTick(p.ticker);
    const isCold = !tick;
    const currentPrice = tick?.price ?? p.avg_cost;
    const weight = p.quantity * currentPrice;
    const pnlPct = isCold ? 0 : ((tick.price - p.avg_cost) / p.avg_cost) * 100;
    const isUp = pnlPct >= 0;
    return { ticker: p.ticker, weight, pnlPct, isUp, isCold };
  });
  // Optional: sort by weight desc for the squarified algo to put big tiles first
  return enriched.sort((a, b) => b.weight - a.weight);
}
```

### `getPortfolioHistory` API client (extends `lib/api/portfolio.ts`)

```typescript
// Source: backend/app/portfolio/routes.py + 03-CONTEXT.md PORT-04
export interface SnapshotOut {
  recorded_at: string;
  total_value: number;
}
export interface HistoryResponse {
  snapshots: SnapshotOut[];
}

export async function getPortfolioHistory(): Promise<HistoryResponse> {
  const res = await fetch('/api/portfolio/history');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as HistoryResponse;
}
```

(Verify final response key — backend returns `HistoryResponse` with a list
of snapshots; the planner should grep `backend/app/portfolio/models.py` for
the exact field name. `[ASSUMED]` it is `snapshots`; if the backend uses
`items` or another key, adjust accordingly. This is a 1-line adjustment.)

### `lib/api/chat.ts` (NEW)

```typescript
// Source: backend/app/chat/models.py (verified) + 05-CONTEXT.md D-07/D-19
export type TradeStatus = 'executed' | 'failed';
export type WatchlistStatus = 'added' | 'exists' | 'removed' | 'not_present' | 'failed';

export interface TradeActionResult {
  ticker: string;
  side: 'buy' | 'sell';
  quantity: number;
  status: TradeStatus;
  price: number | null;
  cash_balance: number | null;
  executed_at: string | null;
  error: string | null;
  message: string | null;
}

export interface WatchlistActionResult {
  ticker: string;
  action: 'add' | 'remove';
  status: WatchlistStatus;
  error: string | null;
  message: string | null;
}

export interface ChatResponse {
  message: string;
  trades: TradeActionResult[];
  watchlist_changes: WatchlistActionResult[];
}

export interface ChatMessageOut {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  actions: { trades: TradeActionResult[]; watchlist_changes: WatchlistActionResult[] } | null;
  created_at: string;
}

export interface HistoryResponse {
  messages: ChatMessageOut[];
}

export async function getChatHistory(): Promise<HistoryResponse> {
  const res = await fetch('/api/chat/history?limit=50');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as HistoryResponse;
}

export async function postChat(body: { message: string }): Promise<ChatResponse> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const j = (await res.json().catch(() => ({}))) as {
      detail?: { error?: string; message?: string };
    };
    throw new Error(j?.detail?.message ?? `HTTP ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
```

### Action card status → CSS class map

```typescript
// Source: UI-SPEC §5.7 status table (verbatim)
type Status = TradeStatus | WatchlistStatus;

const STATUS_STYLE: Record<Status, { borderClass: string; textClass: string; label: string }> = {
  executed:    { borderClass: 'border-l-up border-l-4 border-up/30',                 textClass: 'text-up',                 label: 'executed' },
  added:       { borderClass: 'border-l-up border-l-4 border-up/30',                 textClass: 'text-up',                 label: 'added' },
  removed:     { borderClass: 'border-l-up border-l-4 border-up/30',                 textClass: 'text-up',                 label: 'removed' },
  exists:      { borderClass: 'border-l-foreground-muted border-l-4 border-border-muted', textClass: 'text-foreground-muted', label: 'already there' },
  not_present: { borderClass: 'border-l-foreground-muted border-l-4 border-border-muted', textClass: 'text-foreground-muted', label: "wasn't there" },
  failed:      { borderClass: 'border-l-down border-l-4 border-down/40',             textClass: 'text-down',               label: 'failed' },
};

const ERROR_COPY: Record<string, string> = {
  insufficient_cash:   'Not enough cash for that order.',
  insufficient_shares: "You don't have that many shares to sell.",
  unknown_ticker:      'No such ticker.',
  price_unavailable:   'Price unavailable right now — try again.',
  invalid_ticker:      "That ticker symbol isn't valid.",
  internal_error:      'Something went wrong on our side. Try again.',
};
const FALLBACK_ERROR_COPY = 'Something went wrong. Try again.';
```

### `next.config.mjs` patch (D-15)

```javascript
// Source: UI-SPEC §9 (locked)
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  skipTrailingSlashRedirect: true,   // NEW — Phase 8 D-15
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

### `backend/app/lifespan.py` patch (D-14)

```python
# Source: UI-SPEC §9 + Pattern 8
# Add at the top of imports:
from pathlib import Path
from fastapi.staticfiles import StaticFiles

# At the END of the lifespan startup block, AFTER the chat router mount:
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"
app.mount(
    "/",
    StaticFiles(directory=str(static_dir), html=True),
    name="frontend",
)
```

(`Path(__file__).resolve().parents[2]` from `backend/app/lifespan.py` →
`backend/app/` → `backend/` → repo root. Then `/frontend/out/`. Verified
against the actual filesystem layout.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Recharts 2.x with `TooltipProps<TValue, TName>` for custom tooltips | Recharts 3.x with `TooltipContentProps<TValue, TName>` | Recharts 3.0 (mid-2025) | One import rename in `<PnLTooltip>` |
| `react-smooth` and `recharts-scale` as separate deps | Internalized in Recharts 3.x | Recharts 3.0 | Smaller dep tree, no peer dep issues |
| `Customized` component receiving recharts state via cloned props | Custom React components render natively in the recharts tree | Recharts 3.0 | Phase 8 doesn't use this; informational only |
| Manual `ResponsiveContainer.ref.current.current` ref unwrapping | Single `.current` (flattened) | Recharts 3.0 | Phase 8 doesn't ref the container; informational only |
| Tailwind v3 JS config (`tailwind.config.ts`) | Tailwind v4 CSS-first `@theme` | Phase 6 already adopted | Inherited; no change in Phase 8 |

**Deprecated/outdated:**

- Pre-Recharts-3.x training data examples that import `TooltipProps` —
  use `TooltipContentProps` for typed custom tooltips.
- Anything that suggests overlay-style chat drawers with `position:fixed` —
  push layout (D-07) is the locked design.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `getPortfolioHistory` response is keyed `snapshots: SnapshotOut[]`. Backend `HistoryResponse` model field name not directly verified — inferred from Phase 3 patterns. | §Code Examples | LOW — 1-line key rename in `lib/api/portfolio.ts` if wrong; planner can grep `backend/app/portfolio/models.py:HistoryResponse` to confirm before the API-client task. |
| A2 | The `selectedTab` state belongs in `usePriceStore` (alongside `selectedTicker`) per UI-SPEC §5.2 stated rationale. | §Pattern 5 | LOW — alternative is a separate Zustand store or local React state in `<TabBar>`. UI-SPEC §5.2 says "lives in `price-store.ts` alongside `selectedTicker`", so this is locked. |
| A3 | Treemap custom `content` function receives custom data fields directly merged into `TreemapNode`. | §Pattern 1 | LOW — verified in [Recharts 3.x source `Treemap.tsx`][rc3-tm-src]. If the planner needs to be cautious, destructure via `({ x, y, width, height, ...datum })` and access `datum.ticker` etc. |

[rc3-tm-src]: https://github.com/recharts/recharts/blob/main/src/chart/Treemap.tsx

**Net assumption volume: 3, all LOW risk. No user confirmation needed.**

## Open Questions (RESOLVED)

1. **Should the planner use the Path-from-`__file__` pattern or document
   the cwd contract for the StaticFiles mount?**
   - What we know: dev mode `uv run uvicorn app.main:app` runs from `cd
     backend/`; relative path `frontend/out` doesn't resolve.
   - What's unclear: nothing — the answer is "compute from `__file__`" so
     it works regardless of cwd. Phase 9's Dockerfile will copy
     `frontend/out/` into `backend/static/` and the path becomes static-
     relative.
   - RESOLVED: planner uses
     `Path(__file__).resolve().parents[2] / "frontend" / "out"`. See §Code
     Examples.

2. **Recharts test mocking strategy: stub-only vs `vi.mock('recharts')`?**
   - What we know: `vi.stubGlobal('ResizeObserver', ...)` lets
     `<ResponsiveContainer>` mount but reports 0×0 size in jsdom.
   - What's unclear: how strict the geometry-based assertions in UI-SPEC §13
     need to be. Most Phase 8 tests can assert against props (data shape,
     stroke color), not pixel positions.
   - RESOLVED: start with the `ResizeObserver` stub only. If a
     specific test (e.g., row 1 "renders one rect per position") needs
     visible SVG, add `vi.mock('recharts', () => ({ ...original,
     ResponsiveContainer: <fixed-size-wrapper> }))` in JUST that test file.
     Don't blanket-mock at the setup level.

3. **Should `recharts@^2.x` (CONTEXT.md / UI-SPEC) or `recharts@^3` (latest,
   per CLAUDE.md "latest APIs") be installed?**
   - What we know: Recharts 3.8.1 is the latest stable; the children-based
     composition pattern is unchanged; React 19 is supported.
   - What's unclear: nothing — CLAUDE.md mandates latest APIs; the only
     breaking change touching Phase 8 is `TooltipProps` →
     `TooltipContentProps`, which is a 1-line import update.
   - RESOLVED: install `recharts@^3` (or `^3.8.0`). CONTEXT.md D-17
     and UI-SPEC §1 should be treated as a target version that needs minor
     correction during planning. The decision (use Recharts) is unchanged;
     only the version pin is corrected.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js (≥20) | `npm install recharts`, `npm run build` | ✓ | (engines pin in package.json) `[VERIFIED: package.json engines]` | — |
| `npm` | dependency install | ✓ | (default with Node) | — |
| Python 3.12 | `uv run uvicorn app.main:app` | ✓ | per `backend/pyproject.toml` | — |
| `uv` | backend toolchain | ✓ | per CLAUDE.md mandate | — |
| `frontend/out/` directory | StaticFiles mount target | ✓ | already produced by Phase 6 build `[VERIFIED: ls frontend/out/]` | If missing, run `cd frontend && npm run build`; planner's APP-02 plan should include a `npm run build` gate before testing the mount. |
| `fastapi.staticfiles` (StaticFiles class) | APP-02 mount | ✓ | ships with FastAPI core; no new dep | — |
| `Recharts 3.x` (NEW) | FE-05, FE-06 | not yet installed | will install `^3.8.1` | — |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** none.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`. Section
included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.5 + React Testing Library 16.3.2 + jsdom 29.0.2 (`[VERIFIED: package.json]`) |
| Config file | `frontend/vitest.config.mts` (`[VERIFIED]`) |
| Setup file | `frontend/vitest.setup.ts` (currently 1 line; will extend with ResizeObserver stub) |
| Quick run command | `cd frontend && npm test -- <pattern>` (vitest watch mode) |
| Full suite command | `cd frontend && npm run test:ci` |
| Backend test command | `cd backend && uv run --extra dev pytest -v` (only relevant for the StaticFiles mount integration test, if written) |

### Phase Requirements → Test Map

(Mirrors UI-SPEC §13 Test Map — 22 tests + Phase 7 regression coverage.)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FE-05 | Heatmap renders one rect per position with binary coloring | unit (RTL props assert) | `npm test Heatmap.test.tsx` | ❌ Wave 0 |
| FE-05 | Heatmap click on rect dispatches `setSelectedTicker` | unit | `npm test Heatmap.test.tsx` | ❌ Wave 0 |
| FE-05 | Heatmap empty state copy renders when `positions.length === 0` | unit | `npm test Heatmap.test.tsx` | ❌ Wave 0 |
| FE-05 | Heatmap cell renders cold-cache gray when `current_price` is null | unit | `npm test Heatmap.test.tsx` | ❌ Wave 0 |
| FE-05 | Heatmap weight calc: `weight = quantity * current_price` | unit (pure-fn) | `npm test Heatmap.test.tsx` | ❌ Wave 0 |
| FE-05 | Heatmap P&L %: `(current - avg) / avg * 100`, signed, 2 decimals | unit | `npm test HeatmapCell.test.tsx` | ❌ Wave 0 |
| FE-06 | PnLChart line stroke is up when `latest >= 10000` | unit (props assert) | `npm test PnLChart.test.tsx` | ❌ Wave 0 |
| FE-06 | PnLChart line stroke is down when `latest < 10000` | unit | `npm test PnLChart.test.tsx` | ❌ Wave 0 |
| FE-06 | PnLChart renders 1-snapshot empty state copy | unit | `npm test PnLChart.test.tsx` | ❌ Wave 0 |
| FE-06 | PnLChart includes ReferenceLine at `y=10000` | unit | `npm test PnLChart.test.tsx` | ❌ Wave 0 |
| FE-09 | ChatDrawer is open by default and toggles to 48px on click | unit | `npm test ChatDrawer.test.tsx` | ❌ Wave 0 |
| FE-09 | ChatThread renders messages from `/api/chat/history` on mount | unit (RTL + fetch stub) | `npm test ChatThread.test.tsx` | ❌ Wave 0 |
| FE-09 | ChatThread shows ThinkingBubble while `postChat` in flight | unit | `npm test ChatThread.test.tsx` | ❌ Wave 0 |
| FE-09 | ChatInput Enter submits, Shift+Enter inserts newline | unit (keyboard) | `npm test ChatInput.test.tsx` | ❌ Wave 0 |
| FE-09 | ActionCard renders executed status with up styling | unit | `npm test ActionCard.test.tsx` | ❌ Wave 0 |
| FE-09 | ActionCard renders failed status with down styling and error message | unit | `npm test ActionCard.test.tsx` | ❌ Wave 0 |
| FE-09 | ActionCard renders exists/not_present with muted styling | unit | `npm test ActionCard.test.tsx` | ❌ Wave 0 |
| FE-09 | ActionCardList renders watchlist_changes BEFORE trades | unit | `npm test ActionCardList.test.tsx` | ❌ Wave 0 |
| FE-11 | Position row trade-flash applies `bg-up/20` for ~800ms after executed trade | unit (timer + class) | `npm test PositionRow.test.tsx` | ⚠️ extend Phase 7 file |
| FE-11 | Position row 500ms price-flash and 800ms trade-flash do not interfere | unit | `npm test PositionRow.test.tsx` | ⚠️ extend Phase 7 file |
| FE-11 | SkeletonBlock pulses while query `isPending`; hides after resolve | unit | `npm test Heatmap.test.tsx` | ❌ Wave 0 |
| TEST-02 | Existing Phase 7 price-flash test stays green (regression guard) | unit | `npm run test:ci` | ✅ existing |
| APP-02 | (manual smoke) `curl http://localhost:8000/` returns the index, `curl /api/health` returns the JSON | smoke | `bash test/smoke-app02.sh` (planner may add) OR human verify | ❌ optional |

### Sampling Rate

- **Per task commit:** `npm test -- <relevant pattern>` (vitest watch on the
  changed test file or component).
- **Per wave merge:** `npm run test:ci && npm run build` (full suite + build
  gate).
- **Phase gate:** Full Vitest suite green AND backend `uv run pytest` green
  AND manual smoke (open `/`, see terminal, default chat is open, switch
  tabs, ask the assistant to "buy 1 AAPL", see card pulse + position row
  flash + cash decrease).

### Wave 0 Gaps

Component test files don't exist yet — they're created during Phase 8
plans alongside their components. Plan ordering in UI-SPEC §15 already
spaces these correctly (component plan → test plan, in pairs).

- [ ] `src/components/portfolio/Heatmap.test.tsx` — covers FE-05 (5 tests)
- [ ] `src/components/portfolio/HeatmapCell.test.tsx` — covers FE-05 cell-rendering
- [ ] `src/components/portfolio/PnLChart.test.tsx` — covers FE-06 (4 tests)
- [ ] `src/components/chat/ChatDrawer.test.tsx` — covers FE-09 drawer
- [ ] `src/components/chat/ChatThread.test.tsx` — covers FE-09 thread + history + thinking-bubble
- [ ] `src/components/chat/ChatInput.test.tsx` — covers FE-09 keyboard
- [ ] `src/components/chat/ActionCard.test.tsx` — covers FE-09 styling
- [ ] `src/components/chat/ActionCardList.test.tsx` — covers FE-09 ordering
- [ ] `src/components/terminal/PositionRow.test.tsx` — extend with trade-flash + interference tests
- [ ] `src/lib/fixtures/portfolio.ts` — sample `PortfolioResponse` (3 positions: 1 positive, 1 negative, 1 cold-cache)
- [ ] `src/lib/fixtures/history.ts` — sample 5-snapshot history bridging $10k
- [ ] `src/lib/fixtures/chat.ts` — sample `/api/chat/history` response with 4 messages covering all 6 statuses
- [ ] `vitest.setup.ts` — add `vi.stubGlobal('ResizeObserver', ResizeObserverStub)`

## Sources

### Primary (HIGH confidence)

- `[VERIFIED: npm view recharts version]` — `3.8.1` is current; published
  2026-03-25.
- `[VERIFIED: npm view recharts peerDependencies]` — supports React 19.
- `[CITED: github.com/recharts/recharts/wiki/3.0-migration-guide]` —
  Recharts 3.0 migration: `TooltipProps` → `TooltipContentProps`,
  `ResponsiveContainer.ref` flattened, `Customized` no longer receives
  state, `react-smooth` and `recharts-scale` internalized.
- `[CITED: github.com/recharts/recharts/blob/main/src/chart/Treemap.tsx]` —
  `TreemapNode` interface includes `[k: string]: unknown` for custom data
  fields; `TreemapContentType = ReactNode | ((props: TreemapNode) =>
  ReactElement)`.
- `[CITED: recharts.github.io/en-US/api/Treemap]` — Treemap props (data,
  dataKey, nameKey, content, stroke, animationDuration, isAnimationActive,
  aspectRatio, onClick).
- `[CITED: recharts.github.io/en-US/api/LineChart]` — LineChart and child
  composition (Line, XAxis, YAxis, CartesianGrid, ReferenceLine, Tooltip).
- `[CITED: recharts.github.io/en-US/api/ReferenceLine]` — ReferenceLine
  with `y={number}`, stroke, strokeDasharray, strokeOpacity, ifOverflow.
- `[CITED: nextjs.org/docs/app/api-reference/file-conventions/proxy]` —
  Next.js 16.2.4 proxy.js doc, advanced proxy flags section confirms
  `skipTrailingSlashRedirect` is valid in v13.1+ including v16.
- `[CITED: nextjs.org/docs/app/api-reference/config/next-config-js/trailingSlash]`
  — current Next.js 16.2.4 trailingSlash docs.
- `[CITED: starlette.dev/staticfiles/]` — `html=True` auto-loads
  `index.html` for directories; serves `404.html` in HTML mode.
- `[VERIFIED: package.json + ls frontend/]` — Frontend stack: Next 16.2.4,
  React 19.2.4, TanStack Query 5.100.1, Zustand 5.0.12, Tailwind 4,
  Lightweight Charts 5.2.0, Vitest 4.1.5, jsdom 29.0.2.
- `[VERIFIED: frontend/src/lib/price-store.ts + frontend/src/components/terminal/PositionRow.tsx]`
  — Phase 7 `flashDirection` slice and `flashTimers` map machinery — Phase 8
  `tradeFlash` mirrors this pattern.

### Secondary (MEDIUM confidence)

- `[CITED: github.com/recharts/recharts/discussions/5984]` — v3.0.0
  release announcement.
- `[CITED: github.com/recharts/recharts/discussions/6055]` — Custom Tooltip
  in v3.0+ with `TooltipContentProps`.
- WebSearch — Recharts 3.x breaking changes overview (cross-referenced with
  the migration wiki).
- WebSearch — `vi.stubGlobal('ResizeObserver', ...)` pattern; Mantine and
  Chakra UI testing guides recommend the same approach.
- `[CITED: nextjs.org/docs/app/api-reference/file-conventions/proxy]`
  v16.0.0 changelog row "Middleware is deprecated and renamed to Proxy" —
  informational; does not affect Phase 8 because we use no middleware/proxy
  file.

### Tertiary (LOW confidence — flagged for validation)

- `[CITED: github.com/vercel/next.js/issues/54984, /issues/66738]` — known
  bugs with `skipTrailingSlashRedirect` in middleware/proxy code paths.
  LOW because Phase 8 doesn't use a proxy file; the bug is irrelevant for
  D-15's stated purpose. Validation: a manual smoke test of `npm run dev`
  hitting `/api/stream/prices` after the patch should confirm the redirect
  chain is broken.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — versions verified against npm registry; React 19
  compat confirmed; jsdom test pattern verified against in-repo Phase 7
  prior art.
- Architecture: HIGH — UI-SPEC §5 is exhaustive; CONTEXT.md decisions all
  cite prior phases; the only research-derived correction is the Recharts
  version pin.
- Pitfalls: HIGH — every pitfall is sourced from official docs, GitHub
  issues, or in-repo prior art. The Recharts ResizeObserver pitfall is the
  most novel for this team but is documented across the testing-library
  community.
- Validation Architecture: HIGH — UI-SPEC §13 already provides the test
  map; this section restates it in the Nyquist format and adds the
  ResizeObserver setup gap.

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (30 days; Recharts and Next.js are stable
mainstream libraries; revisit if `recharts@4` ships).
