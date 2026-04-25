---
phase: 08
slug: portfolio-visualization-chat-ui
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-25
---

# Phase 08 — UI Design Contract

> Visual and interaction contract for the three "wow" surfaces of the FinAlly
> trading terminal: portfolio heatmap (FE-05), P&L line chart (FE-06), and the
> right-edge collapsible AI chat panel (FE-09), plus demo polish (FE-11) and the
> APP-02 same-origin static mount. Extends the Phase 07 design system (palette,
> spacing, typography, panel chrome, focus rings) without redefining tokens.
> Locks all CONTEXT.md D-01..D-17 and resolves the ten "Claude's Discretion"
> items with concrete, planner-ready answers.

---

## Scope & Intent

Phase 08 paints three new product surfaces and the two micro-interactions that
make the agentic-AI demo land:

1. **Portfolio heatmap** (FE-05) — Recharts `<Treemap>`, one rectangle per
   position, sized by weight, colored binary up/down by P&L sign.
2. **P&L line chart** (FE-06) — Recharts `<LineChart>` over all snapshots from
   `/api/portfolio/history`, dotted $10k reference line, stroke flips at
   break-even.
3. **AI chat panel** (FE-09) — right-edge ~380px collapsible drawer, default
   open, push layout. Conversation history on mount via
   `GET /api/chat/history`. New turns POST `/api/chat`. 3-dot animated
   "thinking" bubble while in flight. Inline action cards under each assistant
   message render the per-action `status` from Phase 5 D-07.
4. **Demo polish** (FE-11) — per-panel skeleton blocks on cold start, an
   800ms coordinated action-card pulse + position-row flash on agentic auto-
   trade, smooth 300ms drawer slide.
5. **APP-02 static mount** — backend serves `frontend/out/` at `/` after API
   routers; `next.config.mjs` gets `skipTrailingSlashRedirect: true` so dev
   SSE works through the rewrite chain.

Plus: frontend component tests (TEST-02) covering price-flash trigger,
watchlist CRUD UI surfaces (chat-driven add/remove cards), portfolio display
calculations (heatmap weights, P&L %), and chat rendering + loading state.

**Out of scope (later phases):** multi-stage Dockerfile + start/stop scripts +
`.env.example` (Phase 09 OPS-01..04); Playwright E2E (Phase 10 TEST-03,
TEST-04); token-by-token chat streaming (CHAT-07, v2); responsive stacking,
mobile/tablet, full a11y polish (POLISH-01, v2); trade-history dedicated view
(HIST-01, v2); P&L time-window selector; heatmap sector coloring; toast /
global notification system (rejected in Phase 7, rejected again here);
suggested-prompt buttons in empty chat; heatmap drilling/zooming.

---

## 1. Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | none (manual Tailwind v4 CSS-first `@theme`) | Phase 06 UI-SPEC §1 / Phase 07 UI-SPEC §1 (inherited) |
| Preset | not applicable | — |
| Component library | none (hand-authored `components/portfolio/*.tsx` + `components/chat/*.tsx`) | Phase 07 UI-SPEC §1 (inherited pattern) |
| Icon library | none (Phase 08 uses no icon font; emoji are forbidden) | CLAUDE.md / inherited |
| Font stack — sans | `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif` | Phase 06 UI-SPEC §3 (inherited) |
| Font stack — mono | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | Phase 06 UI-SPEC §3 (inherited) |
| Chart library — main + sparklines | `lightweight-charts@^5.x` | Phase 07 (already installed) |
| Chart library — heatmap + P&L | **`recharts@^2.x`** (NEW prod dep) | CONTEXT.md D-01, D-04, D-17 |
| Data-fetching | `@tanstack/react-query@^5.x` for `/api/portfolio`, `/api/portfolio/history`, `/api/chat`, `/api/chat/history` | Phase 07 (already installed) |
| State | `usePriceStore` (Zustand) — Phase 06 store; Phase 08 reads via existing selectors and **may add a `flashTrade(ticker, dir)` slice** for D-12 if not already present from Phase 7 | CONTEXT.md code_context |

**Registry safety gate:** N/A — no shadcn, no third-party registries. Only one
new npm package (`recharts`). It is a first-party, audited, widely deployed
library; no `shadcn view` / no diff vetting required.

---

## 2. Spacing Scale

Inherited verbatim from Phase 06 / Phase 07. Tailwind v4 4px base. Only
multiples of 4. **No arbitrary `px-[Npx]` values anywhere in Phase 08.**

| Token | Value | Usage in Phase 08 |
|-------|-------|-------------------|
| `gap-1` / `p-1` | 4px | Inline action-card icon-to-label gap |
| `gap-2` / `p-2` / `px-2 py-2` | 8px | Action card internal cell padding, message bubble inner padding |
| `gap-3` / `p-3` | 12px | Chat input vertical padding, message-bubble vertical gap inside thread |
| `gap-4` / `p-4` | 16px | Panel internal padding, chat-thread side padding, drawer header padding |
| `gap-6` / `p-6` | 24px | Page outer padding (unchanged from Phase 07) |
| `gap-8` / `p-8` | 32px | Reserved (unused this phase) |

**Exceptions:** none. The drawer width `w-[380px]` (`380` = `4 × 95`) is an
arbitrary `width` — not a spacing utility — and is therefore exempt from the
"multiples-of-4 spacing" rule. (Tailwind v4 still emits `width: 380px` from the
token; it does not generate a spacing utility.)

---

## 3. Typography

Inherited verbatim from Phase 06 / Phase 07. **Phase 08 declares no new sizes
or weights.** Sizes total = 4 (28, 20, 16, 14). Weights total = 2 (400, 600).

| Role | Family | Size | Weight | Line-height | Usage in Phase 08 |
|------|--------|------|--------|-------------|-------------------|
| Body / default | sans | 16px | 400 | 1.5 | Chat message bubbles, action-card labels |
| h2 (panel header) | sans | 20px | 600 | 1.3 | "Heatmap" / "P&L" / "Assistant" panel titles |
| Small / caption | sans | 14px | 400 | 1.4 | Action-card status word, chat timestamps, empty-state copy, tooltip text |
| **Monospace (numeric)** | mono | 14px | 400 | 1.4 | All currency, percentages, quantities, prices on heatmap labels, P&L tooltip values, action-card price + cash fields. `font-mono tabular-nums text-right` for column-aligned digits. |

**Weight 600** is reserved for: panel `<h2>` headings, ticker symbols inside
heatmap rectangles + action cards + position rows, the chat-drawer toggle
label.

**Numeric formatting (verbatim — same as Phase 07):**

| Kind | Format | Example |
|------|--------|---------|
| Currency | `$ X,XXX.XX` (thousands separator, 2 decimals) | `$10,234.56` |
| Signed money (P&L) | `+$X.XX` / `-$X.XX` (sign always present) | `+$12.34` |
| Percent | `+0.00%` / `-0.00%` (sign always present, 2 decimals) | `+2.40%` |
| Quantity (fractional) | up to 4 decimals, trim trailing zeros | `10`, `1.5`, `0.0001` |
| Ticker | uppercase | `AAPL` |
| Timestamp (chat) | `HH:MM` 24h local | `14:32` |
| Timestamp (P&L tooltip) | `MMM D, HH:MM` local | `Apr 25, 14:32` |

---

## 4. Color Contract

### 4.1 Palette — Inherited Unchanged

Phase 08 **adds zero new tokens** and **changes zero existing values**. Every
color comes from the existing `frontend/src/app/globals.css` `@theme` and
`:root` blocks (Phase 07 UI-SPEC §4.1).

| Token | Value | Source |
|-------|-------|--------|
| `--color-surface` | `#0d1117` | Phase 06 / PLAN.md §2 |
| `--color-surface-alt` | `#1a1a2e` | Phase 06 / PLAN.md §2 |
| `--color-border-muted` | `#30363d` | Phase 06 |
| `--color-foreground` | `#e6edf3` | Phase 06 |
| `--color-foreground-muted` | `#8b949e` | Phase 06 |
| `--color-accent-yellow` | `#ecad0a` | PLAN.md §2 |
| `--color-accent-blue` | `#209dd7` | PLAN.md §2 |
| `--color-accent-purple` | `#753991` | PLAN.md §2 |
| `--color-up` | `#26a69a` | Phase 07 D-02 |
| `--color-down` | `#ef5350` | Phase 07 D-02 |

### 4.2 60 / 30 / 10 Split (Phase 08 surfaces)

| Share | Role | Color(s) |
|-------|------|----------|
| 60% | Dominant surface | `--color-surface` (`#0d1117`) — page background, heatmap panel background, P&L chart panel background, chat-thread background |
| 30% | Secondary surface | `--color-surface-alt` (`#1a1a2e`) — chat drawer background, chat input background, action-card background, assistant message bubble background; `--color-border-muted` (`#30363d`) — panel borders, divider between drawer-header and thread, action-card borders |
| 10% | Accent | `--color-accent-purple` (`#753991`) — chat **Send button** (primary CTA, matches PLAN.md §2 "Purple Secondary: submit buttons" + Phase 07 trade-bar precedent); `--color-accent-blue` (`#209dd7`) — focus rings on chat input + Send button + drawer toggle; `--color-accent-yellow` (`#ecad0a`) — **not used in Phase 08** (reserved for connection dot, unchanged from Phase 07) |

**Accent reserved for (Phase 08 surfaces ONLY — full project-wide list adds
to Phase 07's reservations):**

- `--color-accent-purple` (`#753991`) — chat Send button background. Same
  semantic as Phase 07 trade-bar Buy/Sell.
- `--color-accent-blue` (`#209dd7`) — `focus-visible:outline-accent-blue` on:
  chat input, Send button, drawer toggle button, action cards (cards are
  non-interactive in Phase 08 — focus rings only on the cards' "Retry" path,
  which is **not** built in Phase 08).
- `--color-accent-yellow` (`#ecad0a`) — connection-status dot in reconnecting
  state (unchanged from Phase 07; no new yellow surface in Phase 08).

**Semantic up/down — where the tokens render in Phase 08:**

| Surface | Up rule | Down rule |
|---------|---------|-----------|
| Heatmap rectangle background (D-02) | `--color-up` solid when `unrealized_pnl >= 0` | `--color-down` solid when `unrealized_pnl < 0` |
| Heatmap rectangle background — cold-cache fallback | (no tick yet, `current_price == null`) → neutral `--color-surface-alt` (`#1a1a2e`) | same |
| P&L line stroke (D-06) | `--color-up` solid when `last(total_value) >= 10000` | `--color-down` solid when `last(total_value) < 10000` |
| P&L reference line ($10k) (D-05) | dashed `--color-foreground-muted` (`#8b949e`), `strokeDasharray="4 4"`, `strokeOpacity={0.4}` | same |
| Action card status border + accent text (D-11) | `executed`/`added`/`removed` → 4px `border-l-up` + `text-up` status word | `failed` → 4px `border-l-down` + `text-down` status word |
| Action card status border + accent text (D-11) — idempotent | `exists`/`not_present` → 4px `border-l-foreground-muted` + `text-foreground-muted` status word | same |
| Position-row trade-flash (D-12) | `bg-up/20` for ~800ms after a chat-driven `executed` BUY card lands; **also** for any `executed` SELL card lands and total cash increases (the agentic "wow") | `bg-down/20` if the card is `failed`; **note:** failed trades flash on the action card only (no position row to flash; row may not exist) |
| Action-card pulse (D-12) | `bg-up/30 → bg-up/0` over ~800ms via `@keyframes` | `bg-down/30 → bg-down/0` over ~800ms |

**Manual-trade flash (planner discretion → locked here):** The position-row
flash from D-12 also fires on a **manual** `POST /api/portfolio/trade`
success (extending Phase 7 D-08's "implicit confirmation" with a positive
visual cue). This is the inverse of Phase 7 D-08 but Phase 8's polish budget
explicitly supports it. Same 800ms duration, same `bg-up/20` color (manual
trades are always treated as `up` — buy = adding a position, sell = realizing).
This makes the manual-trade and agentic-trade visuals equivalent so users
learn the affordance once.

### 4.3 Accessibility (WCAG AA — no regressions)

Inherited from Phase 07 §4.3. All new combinations pass AA against
`#0d1117`:

| Pair | Ratio | Pass |
|------|-------|------|
| `#26a69a` (up) on `#1a1a2e` (action card bg) | ~5.0:1 | AA |
| `#ef5350` (down) on `#1a1a2e` (action card bg) | ~3.9:1 | **AA Large only** — action-card status word is 14px regular = does NOT clear AA Normal. Mitigation: a 4px `border-l-down` runs the full height of the card so color is never the only signal, and the status word is paired with the verb (`Buy failed`, `Add failed`) so meaning survives without color. |
| `#8b949e` (foreground-muted) on `#1a1a2e` | ~5.4:1 | AA |
| `#e6edf3` (foreground) on `#753991` (Send button) | ~5.2:1 | AA |
| Heatmap label white text on `--color-up` | ~3.9:1 | AA Large only — heatmap labels are bold 16px = clears AA Large |
| Heatmap label white text on `--color-down` | ~4.7:1 | AA |

**Color-as-only-signal mitigations (mandatory):**
- Heatmap labels include the **signed P&L %** (`+2.40%` / `-1.10%`) so the
  meaning carries without color.
- Action cards include the **status word** as text (`executed`, `failed`,
  `added`, `removed`, `exists`, `not_present`) and a **verb prefix**
  (`Buy 10 AAPL`, `Add NVDA`).
- P&L stroke flip is paired with a **dashed $10k reference line**: the line
  position relative to the reference shows up/down without relying on stroke
  color.

### 4.4 Focus Rings

Inherited verbatim from Phase 07 §4.4. New focusable elements:

- Chat input (`<textarea>`)
- Chat Send button
- Chat-drawer toggle button (in the right edge of the header strip, when
  drawer is open and as a thin icon strip when collapsed)

All apply: `focus-visible:outline-2 focus-visible:outline-offset-2
focus-visible:outline-accent-blue`.

Action cards are **not focusable** in Phase 08 (read-only confirmations).

---

## 5. Layout & Component Contracts

### 5.1 Layout Grid — Updated to Host Chat Drawer

Phase 08 wraps the existing Phase 07 `Terminal.tsx` three-column grid in a
**flex row** that places the chat drawer at the right edge with **push
layout** (D-07). When the drawer is open, the existing 3-col grid sits inside
a `min-w-0 flex-1` slot to its left; when collapsed, the drawer becomes a
thin icon strip and the grid expands to fill.

```
┌─ min-w-[1024px+drawer] bg-surface ─────────────────────────────────────────┐
│                                                                            │
│  flex flex-row    (the outermost element of <Terminal>)                    │
│  ┌─ min-w-0 flex-1 ──────────────────────────────────┐  ┌─ chat drawer ─┐ │
│  │  p-6                                              │  │ w-[380px]      │ │
│  │  grid grid-cols-[320px_1fr_360px] gap-6           │  │ bg-surface-alt │ │
│  │  ┌─ Watchlist ─┐ ┌─ Header + center ─┐ ┌─ Right ┐│  │ border-l       │ │
│  │  │             │ │ Header strip      │ │ Pos    │ │  │ flex flex-col  │ │
│  │  │             │ │ TabBar (NEW §5.2) │ │ Tbl    │ │  │ ────────────── │ │
│  │  │             │ │ Tabbed surface:   │ │ Trade  │ │  │ Header (toggle)│ │
│  │  │             │ │ MainChart |       │ │ Bar    │ │  │ ────────────── │ │
│  │  │             │ │ Heatmap   |       │ │        │ │  │ thread (scroll)│ │
│  │  │             │ │ P&L       │       │ │        │ │  │ messages       │ │
│  │  │             │ │                   │ │        │ │  │ action cards   │ │
│  │  │             │ │                   │ │        │ │  │ 3-dot bubble   │ │
│  │  │             │ │                   │ │        │ │  │ ────────────── │ │
│  │  └─────────────┘ └───────────────────┘ └────────┘│  │ input + Send   │ │
│  └───────────────────────────────────────────────────┘  └────────────────┘ │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Layout placement decision (locked from Claude's Discretion):**
**Tabbed center column.** A new `<TabBar />` sits between the header strip
and the main center surface. Tabs: `Chart`, `Heatmap`, `P&L`. Default tab
is `Chart` (Phase 07 surface unchanged on first paint). The Phase 07
positions table + trade bar in the right column **stay in place**. The
existing 3-col grid is preserved; only the center column's content swaps
based on the active tab.

Rationale: a stacked second row would push the trade bar below the fold on
typical 1440×900 desktops and break the "every pixel earns its place"
principle. Tabs keep all five Phase 7 surfaces visible and slot the two new
viz surfaces into the largest area with minimum disruption.

**Concrete grid contract (additions only — Phase 7 contract unchanged):**

| Region | Tailwind classes | Notes |
|--------|------------------|-------|
| Outer flex row | `flex flex-row min-h-screen min-w-[1024px]` | Replaces Phase 7's `<main>` outer-container role |
| Left workspace | `flex-1 min-w-0 bg-surface text-foreground p-6` | Hosts the existing 3-col grid |
| Chat drawer (open) | `w-[380px] bg-surface-alt border-l border-border-muted flex flex-col transition-[width] duration-300` | Pushes the workspace left; total page width ≥ 1024 + 380 ≈ 1404px |
| Chat drawer (collapsed) | `w-12 bg-surface-alt border-l border-border-muted flex flex-col transition-[width] duration-300` | 48px icon strip; toggle remains visible |
| TabBar | `flex gap-2 border-b border-border-muted` | Sits in center column above tabbed surface |
| Tabbed surface — Chart | `flex-1 bg-surface border border-border-muted rounded p-4 min-h-[400px]` | Phase 7 `<MainChart />` unchanged |
| Tabbed surface — Heatmap | `flex-1 bg-surface border border-border-muted rounded p-4 min-h-[400px]` | New `<Heatmap />` |
| Tabbed surface — P&L | `flex-1 bg-surface border border-border-muted rounded p-4 min-h-[400px]` | New `<PnLChart />` |

### 5.2 TabBar (NEW)

**Component:** `<TabBar />` — `'use client'`, named export.
**State:** new Zustand slice `selectedTab: 'chart' | 'heatmap' | 'pnl'`,
default `'chart'`. Action `setSelectedTab(tab)`. Lives in `price-store.ts`
alongside `selectedTicker` (per Phase 7 D-Open Question #3 precedent — same
store for selector symmetry).

```tsx
<nav className="flex gap-2 border-b border-border-muted">
  {tabs.map(t => (
    <button
      key={t.id}
      type="button"
      onClick={() => setSelectedTab(t.id)}
      aria-pressed={selectedTab === t.id}
      className={`
        h-10 px-4 text-sm font-semibold border-b-2 -mb-px
        focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-blue
        ${selectedTab === t.id
          ? 'border-accent-blue text-foreground'
          : 'border-transparent text-foreground-muted hover:text-foreground'}
      `}
    >
      {t.label}
    </button>
  ))}
</nav>
```

| Tab id | Label | Surface |
|--------|-------|---------|
| `chart` | `Chart` | Phase 7 `<MainChart />` (default) |
| `heatmap` | `Heatmap` | new `<Heatmap />` |
| `pnl` | `P&L` | new `<PnLChart />` |

The active tab gets a 2px `border-accent-blue` underline (`-mb-px` so it
overlays the panel divider). Inactive tabs are `text-foreground-muted` with
`hover:text-foreground`.

### 5.3 Portfolio Heatmap (FE-05) — `<Heatmap />`

**Route:** `<Heatmap />` rendered inside the tabbed center surface when
`selectedTab === 'heatmap'`.
**Data source:**
- `useQuery(['portfolio'], fetchPortfolio, { refetchInterval: 15_000 })`
  (already wired by Phase 7) for `positions[]`.
- Per-ticker `selectTick(ticker)` from `usePriceStore` for live
  `current_price` (recomputes weight + P&L on every tick — same convention as
  Phase 7 positions table).

**Markup skeleton:**

```tsx
<section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
  <h2 className="text-xl font-semibold mb-3">Heatmap</h2>
  <div className="flex-1 w-full">
    <ResponsiveContainer width="100%" height="100%">
      <Treemap
        data={treeData}
        dataKey="weight"
        stroke="#30363d"
        strokeWidth={1}
        content={<HeatmapCell />}
        onClick={(node) => setSelectedTicker(node.ticker)}
        animationDuration={300}
        isAnimationActive={true}
      />
    </ResponsiveContainer>
  </div>
</section>
```

**Cell shape (D-03 — ticker + signed P&L %, click selects):**

```tsx
function HeatmapCell({ x, y, width, height, ticker, pnlPct, isUp, isCold }) {
  const fill = isCold ? 'var(--color-surface-alt)'
              : isUp  ? 'var(--color-up)'
              :         'var(--color-down)';
  const showLabel = width >= 60 && height >= 32;  // Recharts hides labels on small cells
  return (
    <g onClick={...} cursor="pointer">
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke="#30363d" />
      {showLabel && (
        <>
          <text x={x + 8} y={y + 18} fill="#ffffff" fontFamily="ui-sans-serif" fontWeight={600} fontSize={14}>
            {ticker}
          </text>
          <text x={x + 8} y={y + 36} fill="#ffffff" fontFamily="ui-monospace" fontSize={12}>
            {formatPercent(pnlPct)}
          </text>
        </>
      )}
    </g>
  );
}
```

| Attribute | Value | Source |
|-----------|-------|--------|
| Library | `recharts@^2.x` `<Treemap>` | CONTEXT.md D-01 |
| Data key | `weight = quantity * current_price` (per position) | CONTEXT.md D-03 + Phase 7 positions sort |
| Total weight | sum over all positions | — |
| Aspect ratio | Recharts default (squarified) | — |
| Cell fill (P&L ≥ 0) | `var(--color-up)` (`#26a69a`) — solid, **not** tinted | D-02 binary up/down |
| Cell fill (P&L < 0) | `var(--color-down)` (`#ef5350`) — solid | D-02 |
| Cell fill (cold cache: `current_price == null`) | `var(--color-surface-alt)` (`#1a1a2e`) — neutral gray (Claude's Discretion locked here) | — |
| Cell border | 1px `#30363d` (`--color-border-muted`) | — |
| Label font (ticker) | sans 16px / 600 / `#ffffff` | — |
| Label font (P&L %) | mono 12px / 400 / `#ffffff` | — |
| Label format | `{ticker}` on top line, `{+0.00%}` on bottom line (signed, 2 decimals) | D-03 |
| Label hide threshold | `width < 60 || height < 32` → render the rectangle without label (same convention as Recharts default) | D-03 ("hides labels automatically on small rectangles") |
| Click | `setSelectedTicker(ticker)` + `setSelectedTab('chart')` (so the user instantly sees the price chart for the clicked rect) | D-03 |
| Animation | Recharts `animationDuration={300}` on layout change (positions reorder when weights shift). Disabled by `prefers-reduced-motion` (see §7). | — |
| Cash inclusion | **excluded** — heatmap is positions-only; cash lives in the header | D-03 |

**P&L % formula (executor reference):**
```
pnl_pct = (current_price - avg_cost) / avg_cost * 100
weight = quantity * current_price
```
Cold-cache fallback: if `current_price == null`, use `avg_cost` for `weight`
and render P&L % as `0.00%` and color as cold-gray.

**Empty state (no positions yet — `positions.length === 0`):**

```tsx
<div className="flex-1 flex items-center justify-center text-center">
  <p className="text-sm text-foreground-muted max-w-xs">
    No positions yet — use the trade bar or ask the AI to buy something.
  </p>
</div>
```

Cold-start (Phase 8 D-13 skeleton): see §6 below — the empty state above
applies only after `useQuery` resolves; before resolve, the skeleton renders.

### 5.4 P&L Line Chart (FE-06) — `<PnLChart />`

**Route:** `<PnLChart />` rendered inside the tabbed center surface when
`selectedTab === 'pnl'`.
**Data source:**
- `useQuery(['portfolio', 'history'], getPortfolioHistory, { refetchInterval: 15_000 })`
  for the snapshot array.
- The `/api/portfolio/history` response is `{recorded_at: ISO, total_value: number}[]`
  ASC-ordered (Phase 3 PORT-04, snapshots from post-trade + 60s cadence).

**Markup skeleton:**

```tsx
<section className="flex-1 bg-surface border border-border-muted rounded p-4 flex flex-col min-h-[400px]">
  <header className="flex items-baseline gap-4 mb-3">
    <h2 className="text-xl font-semibold">P&amp;L</h2>
    <span className="font-mono tabular-nums text-sm text-foreground-muted">
      {formatPrice(latestTotal)} ({formatSignedMoney(latestTotal - 10000)})
    </span>
  </header>
  <div className="flex-1 w-full">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={snapshots}>
        <CartesianGrid stroke="#30363d" strokeDasharray="2 2" />
        <XAxis dataKey="recorded_at" stroke="#8b949e" tickFormatter={tickTime} />
        <YAxis stroke="#8b949e" tickFormatter={tickMoney} domain={['auto', 'auto']} />
        <ReferenceLine y={10000} stroke="#8b949e" strokeDasharray="4 4" strokeOpacity={0.4} />
        <Tooltip content={<PnLTooltip />} />
        <Line
          type="monotone"
          dataKey="total_value"
          stroke={lastTotal >= 10000 ? 'var(--color-up)' : 'var(--color-down)'}
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  </div>
</section>
```

| Attribute | Value | Source |
|-----------|-------|--------|
| Library | `recharts@^2.x` `<LineChart>` + `<ReferenceLine>` + `<Tooltip>` | CONTEXT.md D-04 |
| Data | all rows from `GET /api/portfolio/history` (no time-window filter) | D-04 |
| X-axis | `dataKey="recorded_at"`, formatted `MMM D, HH:MM` local | Discretion (locked) |
| Y-axis | `dataKey="total_value"`, formatted `$X,XXX` (no decimals on axis to keep ticks readable; tooltip shows full 2-decimal precision) | Discretion (locked) |
| Y-axis domain | `['auto', 'auto']` — Recharts decides padding around min/max so the line never touches the panel edges | — |
| Line stroke (≥ $10k last) | `var(--color-up)` (`#26a69a`) | D-06 |
| Line stroke (< $10k last) | `var(--color-down)` (`#ef5350`) | D-06 |
| Line width | 2px | matches main chart in Phase 7 |
| Line type | `monotone` (smooth) | — |
| Dots | `dot={false}` (clean trading aesthetic; tooltip handles point inspection) | — |
| Reference line | horizontal at `y=10000`, stroke `#8b949e` (foreground-muted), `strokeDasharray="4 4"`, `strokeOpacity={0.4}` | D-05 |
| Grid lines | `<CartesianGrid stroke="#30363d" strokeDasharray="2 2" />` (thin dotted) | matches main chart |
| Tooltip | custom `<PnLTooltip />` (see below) | Discretion (locked) |
| Animation | `isAnimationActive={false}` — chart updates feel instant on snapshot insertion; Recharts reflow with animation looks like "redraw" | — |

**Custom tooltip (`<PnLTooltip />`):**

```tsx
function PnLTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { recorded_at, total_value } = payload[0].payload;
  const delta = total_value - 10000;
  return (
    <div className="bg-surface-alt border border-border-muted rounded p-2 text-sm">
      <div className="text-foreground-muted">{formatTimestamp(recorded_at)}</div>
      <div className="font-mono tabular-nums text-foreground">{formatPrice(total_value)}</div>
      <div className={`font-mono tabular-nums ${delta >= 0 ? 'text-up' : 'text-down'}`}>
        {formatSignedMoney(delta)} vs $10k
      </div>
    </div>
  );
}
```

**Header summary line** (right of the panel `<h2>`): shows the latest total +
delta vs $10k. Format: `$10,234.56 (+$234.56)`. Updates on every snapshot
refetch and on every mutation invalidation.

**Empty state (0 or 1 snapshots — locked from Claude's Discretion):**

A line chart needs ≥2 points to be meaningful. With 0 snapshots: render
skeleton (§6). With 1 snapshot: render an explicit empty-state message
inside the panel:

```tsx
<div className="flex-1 flex items-center justify-center text-center">
  <p className="text-sm text-foreground-muted max-w-xs">
    Building P&amp;L history… your first snapshot is in. The next one will
    arrive within 60s or right after your next trade.
  </p>
</div>
```

After the second snapshot lands (auto via 15s `refetchInterval`), the chart
takes over.

**Loading state:** TanStack `isPending` → skeleton (§6).
**Error state:** TanStack `isError` → centered foreground-muted line:
`"Couldn't load P&L history. Retrying in 15s."` (matches Phase 7 positions
error pattern).

### 5.5 AI Chat Panel (FE-09) — `<ChatDrawer />`

**Route:** `<ChatDrawer />` rendered as the right-edge sibling of the
workspace inside `<Terminal>` (see §5.1 layout grid).
**Default state:** **open** (D-07).
**Width:** 380px when open; 48px (icon strip) when collapsed.
**Transition:** `transition-[width] duration-300 ease-out`.
**Toggle:** a `<button>` in the drawer header (top of the drawer) that
flips state. When collapsed, the toggle stays visible inside the 48px strip
as a thin vertical icon-only column.

**Component split:**

| Component | Path | Role |
|-----------|------|------|
| `<ChatDrawer>` | `src/components/chat/ChatDrawer.tsx` | Outer drawer; owns open/closed state; renders header + thread + input |
| `<ChatHeader>` | `src/components/chat/ChatHeader.tsx` | "Assistant" title + toggle button |
| `<ChatThread>` | `src/components/chat/ChatThread.tsx` | Scrollable message list; auto-scrolls to bottom on new message; renders messages from `useQuery(['chat','history'])` + locally-appended turns |
| `<ChatMessage>` | `src/components/chat/ChatMessage.tsx` | One bubble (user or assistant); renders timestamp + content; for assistant, renders `<ActionCardList>` below |
| `<ActionCardList>` | `src/components/chat/ActionCardList.tsx` | Renders the assistant turn's `actions.watchlist_changes` first, then `actions.trades` (matches Phase 5 D-09 execution order) |
| `<ActionCard>` | `src/components/chat/ActionCard.tsx` | Compact card per action; status-driven styling per D-11 |
| `<ChatInput>` | `src/components/chat/ChatInput.tsx` | `<textarea>` + Send button; `useMutation(postChat)` |
| `<ThinkingBubble>` | `src/components/chat/ThinkingBubble.tsx` | 3-dot animated bubble shown as the last assistant message while in flight |

**Drawer markup skeleton:**

```tsx
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

**Drawer header markup:**

```tsx
<header className="h-12 px-4 flex items-center justify-between border-b border-border-muted">
  {isOpen && <h2 className="text-xl font-semibold">Assistant</h2>}
  <button
    type="button"
    onClick={onToggle}
    aria-label={isOpen ? 'Collapse chat' : 'Expand chat'}
    aria-expanded={isOpen}
    className="w-8 h-8 rounded text-foreground-muted hover:text-foreground hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent-blue"
  >
    {isOpen ? '›' : '‹'}
  </button>
</header>
```

(The `›` / `‹` are Unicode single guillemets — not emoji. Sans-serif glyph,
inherits parent color.)

**Thread markup:**

```tsx
<div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
  {messages.map(m => <ChatMessage key={m.id} message={m} />)}
  {isInFlight && <ThinkingBubble />}
</div>
```

**Auto-scroll behavior:** on new message append (history load, post-mutation
resolve, or in-flight bubble appearing), scroll the thread container to
`scrollHeight` via `useLayoutEffect`. Skip the scroll when the user is
already scrolled away from the bottom (>120px from bottom) — this preserves
manual scroll-back behavior. (Implementation guidance for the planner; not
re-asking.)

**Empty state (locked from Claude's Discretion):**

Before the first chat turn (history is empty):

```tsx
<div className="flex-1 flex items-end px-4 py-3">
  <p className="text-sm text-foreground-muted">
    Ask me about your portfolio or tell me to trade.
  </p>
</div>
```

Single line, no suggested-prompt buttons (deferred per CONTEXT.md). Sits at
the bottom of the thread so the input remains the visual focus.

**Loading state (history fetch in flight):**

Cold-load: render the §6 chat-thread skeleton (3 alternating muted bubbles).

### 5.6 Chat Message — `<ChatMessage />`

**Markup (user turn):**

```tsx
<div className="flex flex-col items-end">
  <div className="max-w-[85%] bg-surface border border-border-muted rounded-lg px-3 py-2 text-foreground">
    {content}
  </div>
  <span className="text-xs text-foreground-muted mt-1">{formatTime(created_at)}</span>
</div>
```

**Markup (assistant turn):**

```tsx
<div className="flex flex-col items-start">
  <div className="max-w-[85%] bg-surface-alt border border-border-muted rounded-lg px-3 py-2 text-foreground">
    {content}
  </div>
  {actions && <ActionCardList actions={actions} />}
  <span className="text-xs text-foreground-muted mt-1">{formatTime(created_at)}</span>
</div>
```

| Element | Side | Background | Border | Max width |
|---------|------|------------|--------|-----------|
| User bubble | right | `bg-surface` (slightly different from drawer's `bg-surface-alt` so user vs assistant is visually clear) | `border-border-muted` | 85% of thread width |
| Assistant bubble | left | `bg-surface-alt` (same as drawer) — feels "embedded" in the assistant column | `border-border-muted` | 85% of thread width |
| Timestamp | aligns with bubble side | — | — | — |

Padding `px-3 py-2` (12 / 8). Corner radius `rounded-lg` (8px). Text size
16px / 400 / 1.5 (body). Timestamps `text-xs` (12px) `text-foreground-muted`.

**Multi-line content:** `whitespace-pre-wrap` so newlines from the LLM render
naturally.

### 5.7 Action Cards — `<ActionCardList>` + `<ActionCard>` (D-10, D-11)

**Render order (D-09 — verbatim Phase 5 D-09 watchlist-first execution
order):** `actions.watchlist_changes[]` first, then `actions.trades[]`.

**Action card skeleton:**

```tsx
<div
  className={`
    border-l-4 ${borderClass}
    bg-surface border ${borderClass.replace('border-l-', 'border-')}
    rounded px-3 py-2 mt-2
    flex items-baseline justify-between gap-2
    ${pulseClass}
  `}
>
  <div className="flex items-baseline gap-2 min-w-0">
    <span className="text-sm font-semibold">{verbLabel}</span>
    <span className="font-semibold">{ticker}</span>
    {qtyOrAction && (
      <span className="font-mono tabular-nums text-sm text-foreground-muted">
        {qtyOrAction}
      </span>
    )}
  </div>
  <span className={`text-sm font-semibold ${statusTextClass}`}>{statusLabel}</span>
</div>
```

**Per-status styling table:**

| Status | Source | Border-l + border | Status text class | Status label | Verb label |
|--------|--------|-------------------|-------------------|--------------|------------|
| `executed` (trade) | Phase 5 D-07 | `border-l-up border-up/30` | `text-up` | `executed` | `Buy` / `Sell` (from `side`) |
| `failed` (trade) | Phase 5 D-07 | `border-l-down border-down/40` | `text-down` | `failed` | `Buy` / `Sell` |
| `added` (watchlist) | Phase 4 / D-07 | `border-l-up border-up/30` | `text-up` | `added` | `Add` |
| `removed` (watchlist) | Phase 4 / D-07 | `border-l-up border-up/30` | `text-up` | `removed` | `Remove` |
| `exists` (watchlist) | Phase 4 / D-07 | `border-l-foreground-muted border-border-muted` | `text-foreground-muted` | `already there` | `Add` |
| `not_present` (watchlist) | Phase 4 / D-07 | `border-l-foreground-muted border-border-muted` | `text-foreground-muted` | `wasn't there` | `Remove` |
| `failed` (watchlist) | Phase 5 D-07 | `border-l-down border-down/40` | `text-down` | `failed` | `Add` / `Remove` |

**Card content layout (verb + ticker + detail + status):**

| Action kind | Detail field |
|-------------|--------------|
| Trade `executed` | `quantity @ $price` (e.g., `10 @ $191.23`) — inlined from Phase 5 D-07 trade payload (`price`, `executed_at` available) |
| Trade `failed` | the human-readable error string from §8 copy table, rendered on a second line below the verb row in `text-down text-sm` |
| Watchlist `added` / `removed` / `exists` / `not_present` | no detail (the verb + ticker + status word is enough) |
| Watchlist `failed` | the error string on a second line in `text-down text-sm` |

**Pulse animation (D-12):**

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

The `pulseClass` is applied **only** when the card is freshly rendered as
part of the `postChat` mutation resolve (not for cards rendered from
`/api/chat/history`). Implementation: tag the `actions` array on a freshly-
arrived assistant turn with `_fresh: true` in the local message-list
ingestion step; `<ActionCard>` reads that flag once and applies the class.
Cards from history render without pulse.

**Position-row flash (D-12):** when an `executed` trade card lands, dispatch
`flashTrade(ticker, dir)` on `usePriceStore` where:
- `dir = 'up'` for any `executed` trade (consistent with the §4.2 manual-
  trade rule above — `executed` is unambiguously a positive event).
- A new transient `tradeFlash: Record<string, 'up' | 'down'>` slice on the
  store (parallel to `flashDirection` but **separate**, so the 500ms price
  flash and 800ms trade flash never collide on the same selector).
- `setTimeout(() => clearTradeFlash(ticker), 800)`.
- Position rows subscribe via `selectTradeFlash(ticker)` and apply
  `bg-up/20` (or `bg-down/20`) with `transition-colors duration-800`.

The 500ms price flash and the 800ms trade flash use **different opacity
levels** (`/10` vs `/20`) and **different durations**, so they read as two
distinct events even when both fire on the same row at the same instant
(price tick happens to land during a trade flash).

### 5.8 Chat Input — `<ChatInput />`

**Markup skeleton:**

```tsx
<form
  onSubmit={handleSubmit}
  className="border-t border-border-muted p-3 flex gap-2 items-end"
>
  <textarea
    ref={inputRef}
    value={text}
    onChange={(e) => setText(e.target.value)}
    onKeyDown={handleKeyDown}
    rows={2}
    placeholder="Ask me about your portfolio…"
    disabled={isPending}
    className="flex-1 resize-none px-3 py-2 bg-surface border border-border-muted rounded text-foreground font-sans text-base min-h-[64px] max-h-[160px] focus-visible:outline-2 focus-visible:outline-accent-blue disabled:opacity-50"
  />
  <button
    type="submit"
    disabled={isPending || text.trim().length === 0}
    className="h-10 px-4 bg-accent-purple text-white font-semibold rounded hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent-blue"
  >
    Send
  </button>
</form>
```

**Keyboard contract (locked from Claude's Discretion):**

| Keys | Behavior |
|------|----------|
| `Enter` (no modifier) | Submit the form. Standard chat-app default. |
| `Shift + Enter` | Insert newline. Multi-line composition. |
| `Cmd + Enter` / `Ctrl + Enter` | Also submits. Power-user fallback when Shift+Enter is muscle memory. |

Implemented via `onKeyDown`:

```ts
function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSubmit(e);
  }
}
```

**Disabled rules:**
- Send button disabled when `text.trim() === ''` (no empty submits).
- Both input and Send disabled while `mutation.isPending === true` (single
  in-flight chat at a time — matches Phase 5 D-19 single-shot semantics).

**Placeholder copy:** `Ask me about your portfolio…`

**Submission flow:**
1. User submits (button or Enter).
2. Optimistically append a user message to the local message list (with a
   `_pending: true` flag) — appears immediately in the thread.
3. Render `<ThinkingBubble />` as the last "assistant" position in the thread.
4. `postChat({content: text})` fires.
5. On success: the new assistant turn (with `actions`) is appended; the
   `<ThinkingBubble />` disappears; pulse + position-row flash fire on each
   `executed` action; `queryClient.invalidateQueries(['portfolio'])` refreshes
   the positions table + header totals (manual `executed` already invalidated;
   chat `executed` does the same).
6. On mutation failure (network / 5xx): show a small inline error line below
   the input area in `text-down text-sm`: `"Couldn't reach the assistant.
   Try again."` — auto-dismissed when input changes or next submit succeeds.
7. Clear input. Refocus textarea.

**Drawer keyboard shortcut (Cmd+K) — DEFERRED.** Per CONTEXT.md "Claude's
Discretion" — explicitly not built in Phase 8.

### 5.9 ThinkingBubble — `<ThinkingBubble />` (D-08)

**Markup:**

```tsx
<div className="flex flex-col items-start">
  <div className="bg-surface-alt border border-border-muted rounded-lg px-3 py-3 flex items-center gap-1" aria-label="Assistant is thinking">
    <span className="thinking-dot" />
    <span className="thinking-dot" />
    <span className="thinking-dot" />
  </div>
</div>
```

**CSS:**

```css
.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
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

| Property | Value |
|----------|-------|
| Dot size | 6×6 px |
| Dot color | `var(--color-foreground-muted)` (`#8b949e`) |
| Dot gap | 4px (`gap-1`) |
| Cycle | 1200ms infinite |
| Stagger | 0ms / 200ms / 400ms (typewriter feel) |
| Bubble background | `bg-surface-alt` (matches assistant bubbles) |
| Bubble padding | `px-3 py-3` (12 / 12) — slightly taller than text bubbles so the bouncing dots have room |
| `prefers-reduced-motion` | dots stay at full opacity, `transform: none`, animation disabled (see §7) |

Sits as the **last** child of the thread while `mutation.isPending`. Once the
mutation resolves, it's replaced by the real assistant turn.

---

## 6. Skeleton Loaders (D-13)

Per-panel cold-start skeletons. **Pure CSS** — no library. Renders while
`useQuery.isPending` is true (or, for the heatmap and P&L, while waiting for
both the portfolio response AND at least one SSE tick / one snapshot).

**Shared skeleton primitive:**

```tsx
function SkeletonBlock({ className }: { className?: string }) {
  return <div className={`bg-border-muted/50 rounded animate-pulse ${className ?? ''}`} />;
}
```

(`animate-pulse` is the Tailwind v4 built-in that emits a 2s opacity pulse.
`bg-border-muted/50` is `--color-border-muted` at 50% over the panel
background — visible but muted.)

**Per-panel skeleton specs:**

| Panel | Skeleton |
|-------|----------|
| Watchlist (Phase 7, mentioned for completeness) | 10 rows of `<tr>` with `<td><SkeletonBlock className="h-4 w-16" /></td>` for each column |
| Positions table (Phase 7) | 3 rows of skeleton bars: `h-4 w-12` ticker, `h-4 w-8` qty, `h-4 w-16` price, `h-4 w-16` P&L |
| Header totals (Phase 7) | both numeric spans show `—` (em-dash, `text-foreground-muted`) until first portfolio resolve |
| Heatmap (NEW) | one large `SkeletonBlock` filling the panel: `<SkeletonBlock className="flex-1 w-full" />` |
| P&L chart (NEW) | a faint axis: vertical and horizontal `SkeletonBlock` lines, no data line. Approx: `<SkeletonBlock className="h-4 w-full mt-auto" />` (X-axis position) + `<SkeletonBlock className="h-full w-4" />` (Y-axis position) inside a flex layout |
| Chat thread (NEW) | three alternating message bubbles: `SkeletonBlock` left-aligned `h-12 w-48`, right-aligned `h-12 w-32`, left-aligned `h-12 w-56`. `gap-3` between |

**Removal trigger per panel:**

| Panel | Skeleton hides when |
|-------|---------------------|
| Watchlist | `useQuery(['watchlist'])` resolves AND first SSE tick lands |
| Positions table | `useQuery(['portfolio'])` resolves |
| Heatmap | `useQuery(['portfolio'])` resolves; if `positions.length === 0` shows the empty-state copy from §5.3 |
| P&L chart | `useQuery(['portfolio','history'])` resolves; if 0 snapshots → skeleton stays; if 1 → empty-state copy from §5.4; if ≥2 → chart |
| Chat thread | `useQuery(['chat','history'])` resolves; if `messages.length === 0` shows the empty-state copy from §5.5 |

`prefers-reduced-motion`: skeleton blocks render at flat 50% opacity (no
pulse animation). See §7.

---

## 7. Motion & Animation Contract

Phase 08 has **four motion primitives**. All have `prefers-reduced-motion`
fallbacks.

| Primitive | Duration | Easing | Trigger | `prefers-reduced-motion` fallback |
|-----------|----------|--------|---------|-----------------------------------|
| Price-flash row background (Phase 7 D-01 — inherited unchanged) | 500ms | ease-out | tick where `raw.price !== prior.price` | no flash (immediate text update only) |
| Trade-flash row background (D-12) | **800ms** | ease-out | `executed` chat or manual trade for that ticker | no flash (text updates only) |
| Action-card pulse (D-12) | **800ms** | ease-out | freshly-rendered card from `postChat` resolve | no pulse |
| Drawer slide (D-07) | **300ms** | ease-out | toggle button click | width snaps instantly between `w-12` and `w-[380px]` (no transition) |
| Skeleton pulse | 2s | ease-in-out (Tailwind default) | panel `isPending` | flat opacity, no pulse |
| Thinking bubble dots (D-08) | 1200ms loop, 200ms stagger | ease-in-out | `mutation.isPending` true | dots stay at full opacity, no Y-translate |
| Heatmap rectangle reflow (Recharts) | 300ms | Recharts default | weights shift as prices tick | `isAnimationActive={false}` (reflow snaps) |

**Implementation rule:** wrap every `@keyframes`-based animation in:

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

This block lives at the bottom of `globals.css`. Static states are still
correct — colors, widths, opacities stay where they end up.

**Tempo language (the agentic-AI affordance, locked):**
- **Fast 500ms /10 alpha price flash** → "a price ticked"
- **Slower 800ms /20 alpha trade flash + 800ms card pulse** → "an action just executed"

Within a few seconds of the demo the eye learns the difference; this is the
core agentic-AI visual vocabulary CONTEXT.md `<specifics>` calls out.

---

## 8. Copywriting Contract (consolidated)

Every visible string introduced or modified by Phase 08. Executor copies
verbatim. Phase 7 strings are unchanged unless explicitly listed.

### 8.1 Tabs

| Location | String |
|----------|--------|
| TabBar tab — Chart | `Chart` |
| TabBar tab — Heatmap | `Heatmap` |
| TabBar tab — P&L | `P&L` |

### 8.2 Heatmap

| Location | String |
|----------|--------|
| Heatmap panel `<h2>` | `Heatmap` |
| Heatmap empty state | `No positions yet — use the trade bar or ask the AI to buy something.` |

### 8.3 P&L Chart

| Location | String |
|----------|--------|
| P&L panel `<h2>` | `P&L` |
| P&L header summary template | `{currentTotal} ({signedDelta} vs $10k)` (e.g., `$10,234.56 (+$234.56 vs $10k)`) — assembled at runtime |
| P&L 1-snapshot empty state | `Building P&L history… your first snapshot is in. The next one will arrive within 60s or right after your next trade.` |
| P&L error state | `Couldn't load P&L history. Retrying in 15s.` |
| P&L tooltip "vs $10k" suffix | ` vs $10k` |

### 8.4 Chat Drawer

| Location | String |
|----------|--------|
| Drawer header `<h2>` | `Assistant` |
| Drawer toggle aria-label (open) | `Collapse chat` |
| Drawer toggle aria-label (closed) | `Expand chat` |
| Drawer aside aria-label | `AI assistant` |
| Empty thread copy | `Ask me about your portfolio or tell me to trade.` |
| Input placeholder | `Ask me about your portfolio…` |
| Send button | `Send` |
| ThinkingBubble aria-label | `Assistant is thinking` |
| Send error copy | `Couldn't reach the assistant. Try again.` |

### 8.5 Action Cards (D-10, D-11)

**Verb labels:**

| Source field | Verb |
|--------------|------|
| `trades[i].side === 'buy'` | `Buy` |
| `trades[i].side === 'sell'` | `Sell` |
| `watchlist_changes[i].action === 'add'` | `Add` |
| `watchlist_changes[i].action === 'remove'` | `Remove` |

**Status labels (right side of card):**

| `status` | Label |
|----------|-------|
| `executed` | `executed` |
| `failed` | `failed` |
| `added` | `added` |
| `removed` | `removed` |
| `exists` | `already there` |
| `not_present` | `wasn't there` |

**Detail line (trade `executed`):**

`{quantity} @ {formatPrice(price)}` — e.g., `10 @ $191.23`. Mono font.

**Failed-action error map (extends Phase 7 D-07; locked from Claude's
Discretion):**

| `error` code (Phase 5 D-12) | Copy |
|------------------------------|------|
| `insufficient_cash` | `Not enough cash for that order.` |
| `insufficient_shares` | `You don't have that many shares to sell.` |
| `unknown_ticker` | `No such ticker.` |
| `price_unavailable` | `Price unavailable right now — try again.` |
| `invalid_ticker` | `That ticker symbol isn't valid.` |
| `internal_error` | `Something went wrong on our side. Try again.` |
| *(any other / missing)* | `Something went wrong. Try again.` |

These render as a **second line** inside the action card, in
`text-sm text-down`, immediately below the verb-row when `status === 'failed'`.

The first four codes match the Phase 7 D-07 trade-bar copy verbatim — same
errors, same wording, two surfaces. The last two (`invalid_ticker`,
`internal_error`) are Phase 8-new (Phase 5 D-12 codes that Phase 7 didn't
encounter).

### 8.6 Skeleton + Loading States

| Location | String |
|----------|--------|
| Heatmap loading | (skeleton block — no text) |
| P&L loading | (skeleton block — no text) |
| Chat thread loading | (3 skeleton bubbles — no text) |

**Notes:**
- Use ASCII apostrophes (`'`) and straight dashes or em-dash (`—`).
- Em-dashes are intentional in `Building P&L history…`, `Try again.`,
  `Reconnecting…`, etc.
- No emojis anywhere (CLAUDE.md rule).
- "Destructive actions" — Phase 8 has **none**. Watchlist remove and trade
  sell go through inline action cards / inline trade-bar feedback; no
  confirmation dialogs anywhere.

---

## 9. Routing Decision (locked)

**Unchanged from Phase 7.** Terminal renders at `/` (root). `/debug` from
Phase 06 still alive as a developer tool.

**APP-02 mount:** `backend/app/lifespan.py` mounts
`StaticFiles(directory="frontend/out", html=True)` at `/` **after** all
`/api/*` routers. Visiting `http://localhost:8000/` serves
`frontend/out/index.html` (the terminal). Visiting `/debug/` serves
`frontend/out/debug/index.html`. Hitting `/api/anything` still resolves to
the API routers because they're registered first.

**`next.config.mjs` patch (D-15):**
```js
export default {
  output: 'export',
  trailingSlash: true,
  skipTrailingSlashRedirect: true,  // NEW — Phase 8 D-15
  async rewrites() { /* unchanged */ },
};
```

This eliminates Phase 7's G1 dev-redirect chain. With this single line,
`npm run dev` SSE works (the rewrite chain stops issuing the 308) and the
prod static mount at `/` works (no trailing-slash bouncing through Next
middleware that the static export doesn't run).

---

## 10. Accessibility

| Element | Requirement |
|---------|-------------|
| Chat drawer toggle | `aria-label="Collapse chat"` / `aria-label="Expand chat"` + `aria-expanded={isOpen}` |
| Chat drawer aside | `aria-label="AI assistant"` (the whole drawer is an `<aside>`) |
| Chat thread auto-scroll | does not steal focus; only scrolls the container |
| Chat input | a `<textarea>` with `aria-label="Ask the assistant"` (or a visually-hidden `<label>`); the placeholder is informational, not a label substitute |
| Send button error region | the send-error line is a `<p role="alert">` so screen readers announce it |
| ThinkingBubble | `aria-label="Assistant is thinking"` on the bubble container so the announcement is clear |
| Tab buttons | each `<button>` has `aria-pressed={selectedTab === t.id}` |
| Heatmap | the `<g>` cells include a `<title>{ticker}: {formatPercent(pnl)}</title>` SVG element so screen readers can read each rectangle |
| P&L tooltip | Recharts default tooltip is keyboard-inaccessible; in Phase 8 we accept this and pair the chart with the header summary line (latest total + delta) so the data is announceable without hover |
| Action cards | non-interactive; `role` defaults to none. The verb + ticker + status word + (optional) error line are read in DOM order |
| Color as only signal | always paired with a sign (`+`/`-`), a status word (`executed`/`failed`/`added`/...), or both. Never color-only. |
| Focus rings | `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-blue` on textarea, Send, drawer toggle, tab buttons |
| Reduced motion | `@media (prefers-reduced-motion: reduce)` block disables pulses, slides, and skeletons (§7) |

**Recommendation (not required for Phase 08):** `aria-live="polite"` on the
P&L panel header summary line so total-value changes after trades are
announced. Plan may include or skip; v2 POLISH-01 will add full a11y pass.

---

## 11. Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | *(not initialized — no components.json)* | not applicable |
| *(no third-party registries)* | *(none)* | not applicable |

Only one new prod dep: `recharts@^2.x` (CONTEXT.md D-17). First-party,
audited, MIT-licensed, ~70k weekly downloads, no `shadcn view` / no diff
vetting required.

---

## 12. Component Inventory

| Component | Path | Role |
|-----------|------|------|
| `<TabBar>` | `src/components/terminal/TabBar.tsx` (NEW) | Three-tab switcher above the center surface (Chart / Heatmap / P&L) |
| `<Heatmap>` | `src/components/portfolio/Heatmap.tsx` (NEW) | Recharts `<Treemap>` — FE-05 |
| `<HeatmapCell>` | `src/components/portfolio/HeatmapCell.tsx` (NEW) | `content` prop renderer for one rectangle |
| `<PnLChart>` | `src/components/portfolio/PnLChart.tsx` (NEW) | Recharts `<LineChart>` + `<ReferenceLine>` — FE-06 |
| `<PnLTooltip>` | `src/components/portfolio/PnLTooltip.tsx` (NEW) | Custom Recharts tooltip |
| `<ChatDrawer>` | `src/components/chat/ChatDrawer.tsx` (NEW) | Right-edge collapsible drawer — FE-09 |
| `<ChatHeader>` | `src/components/chat/ChatHeader.tsx` (NEW) | Drawer header strip + toggle button |
| `<ChatThread>` | `src/components/chat/ChatThread.tsx` (NEW) | Scrolling message list + auto-scroll |
| `<ChatMessage>` | `src/components/chat/ChatMessage.tsx` (NEW) | One bubble (user or assistant) |
| `<ActionCardList>` | `src/components/chat/ActionCardList.tsx` (NEW) | Watchlist-first then trades (D-09 order) |
| `<ActionCard>` | `src/components/chat/ActionCard.tsx` (NEW) | One action confirmation; status-driven styling — D-10, D-11 |
| `<ChatInput>` | `src/components/chat/ChatInput.tsx` (NEW) | Textarea + Send + keyboard contract |
| `<ThinkingBubble>` | `src/components/chat/ThinkingBubble.tsx` (NEW) | 3-dot animated bubble — D-08 |
| `<SkeletonBlock>` | `src/components/skeleton/SkeletonBlock.tsx` (NEW) | Shared muted-grey pulsing block |
| Skeleton variants | inlined in each panel | per-panel skeleton — D-13 |
| `lib/api/portfolio.ts` | EXTEND | Add `getPortfolioHistory()` |
| `lib/api/chat.ts` | NEW | `getChatHistory()`, `postChat()` |
| `lib/price-store.ts` | EXTEND | Add `selectedTab` slice + `setSelectedTab` action; add `tradeFlash: Record<string, 'up'|'down'>` slice + `flashTrade(ticker, dir)` action + `selectTradeFlash(ticker)` selector (separate from Phase 7's `flashDirection`) |
| `src/app/globals.css` | EXTEND | Add `@keyframes action-pulse-up/down`, `@keyframes thinking-pulse`, `prefers-reduced-motion` block |
| `src/components/terminal/Terminal.tsx` | UPDATE | Wrap existing 3-col grid in flex row with `<ChatDrawer>`; insert `<TabBar>` and tabbed surface in center column |
| `next.config.mjs` | UPDATE | Add `skipTrailingSlashRedirect: true` (D-15) |
| `backend/app/lifespan.py` | UPDATE | Add `app.mount("/", StaticFiles(directory="frontend/out", html=True))` AFTER all routers (D-14) |
| `frontend/package.json` | UPDATE | Add `recharts@^2.x` to `dependencies` |

**Module size budget (inherited):** ≤120 lines per `.tsx`/`.ts` file. Split
when a file crosses the line. The chat sub-tree is intentionally split into
many small components so each one stays under budget.

---

## 13. Test Map (TEST-02 — D-16)

Vitest + RTL + MockEventSource (Phase 6 D-test pattern). All Phase 8 tests
go in `*.test.tsx` files alongside their components. Existing Phase 7 tests
must remain green.

| # | Test name | File | Covers |
|---|-----------|------|--------|
| 1 | `Heatmap renders one rect per position with binary coloring` | `Heatmap.test.tsx` | FE-05 — heatmap weight + color |
| 2 | `Heatmap click on rect dispatches setSelectedTicker` | `Heatmap.test.tsx` | FE-05 — D-03 click |
| 3 | `Heatmap empty state copy renders when positions.length === 0` | `Heatmap.test.tsx` | FE-05 — empty state |
| 4 | `Heatmap cell renders cold-cache gray when current_price is null` | `Heatmap.test.tsx` | FE-05 — fallback |
| 5 | `PnLChart line stroke is up when latest >= 10000` | `PnLChart.test.tsx` | FE-06 — D-06 stroke flip up |
| 6 | `PnLChart line stroke is down when latest < 10000` | `PnLChart.test.tsx` | FE-06 — D-06 stroke flip down |
| 7 | `PnLChart renders 1-snapshot empty state copy` | `PnLChart.test.tsx` | FE-06 — empty state |
| 8 | `PnLChart includes ReferenceLine at y=10000` | `PnLChart.test.tsx` | FE-06 — D-05 |
| 9 | `ChatDrawer is open by default and toggles to 48px on click` | `ChatDrawer.test.tsx` | FE-09 — D-07 |
| 10 | `ChatThread renders messages from /api/chat/history on mount` | `ChatThread.test.tsx` | FE-09 — D-09 |
| 11 | `ChatThread shows ThinkingBubble while postChat in flight` | `ChatThread.test.tsx` | FE-09 — D-08 |
| 12 | `ChatInput Enter submits, Shift+Enter inserts newline` | `ChatInput.test.tsx` | FE-09 — keyboard |
| 13 | `ActionCard renders executed status with up styling` | `ActionCard.test.tsx` | FE-09 — D-11 |
| 14 | `ActionCard renders failed status with down styling and error message` | `ActionCard.test.tsx` | FE-09 — D-11 |
| 15 | `ActionCard renders exists/not_present with muted styling` | `ActionCard.test.tsx` | FE-09 — D-11 |
| 16 | `ActionCardList renders watchlist_changes BEFORE trades` | `ActionCardList.test.tsx` | FE-09 — D-09 order |
| 17 | `Position row trade-flash applies bg-up/20 for ~800ms after executed trade` | `PositionRow.test.tsx` (extend Phase 7 test) | FE-11 — D-12 trade flash |
| 18 | `Position row 500ms price-flash and 800ms trade-flash do not interfere` | `PositionRow.test.tsx` | FE-11 — D-12 distinctness |
| 19 | `Heatmap weight calculation: weight = quantity * current_price` | `Heatmap.test.tsx` | TEST-02 portfolio calculation |
| 20 | `Heatmap P&L %: (current - avg) / avg * 100, rendered with sign` | `HeatmapCell.test.tsx` | TEST-02 portfolio calculation |
| 21 | `SkeletonBlock pulses while query isPending; hides after resolve` | `Heatmap.test.tsx` | FE-11 — D-13 |
| 22 | `Existing Phase 7 price-flash test stays green (regression guard)` | `WatchlistRow.test.tsx` | TEST-02 |

**Test totals:** ~22 new component tests + Phase 7 regression coverage.
Runtime budget: <2s for the new tests on top of Phase 7's existing suite.

**Mock fixtures:**
- `fixtures/portfolio.ts` — sample `PortfolioResponse` with 3 positions (one
  positive P&L, one negative, one cold-cache).
- `fixtures/history.ts` — sample 5-snapshot history bridging $10k.
- `fixtures/chat.ts` — sample `/api/chat/history` response with 4 messages
  (2 user, 2 assistant) including action cards covering all six statuses
  (`executed`, `failed`, `added`, `removed`, `exists`, `not_present`).

No Playwright in this phase. Out-of-process E2E (TEST-03/TEST-04) belongs to
Phase 10.

---

## 14. Pre-population Sources

| Field | Source |
|-------|--------|
| Spacing scale 4px base | Phase 06 / Phase 07 UI-SPEC §2 (inherited) |
| Typography sizes 28/20/16/14, weights 400/600 | Phase 06 / Phase 07 UI-SPEC §3 (inherited) |
| Monospace numerics rule | Phase 06 / Phase 07 (inherited) |
| `#0d1117` surface, `#1a1a2e` surface-alt, `#30363d` border-muted | Phase 06 / PLAN.md §2 |
| `#e6edf3` foreground, `#8b949e` foreground-muted | Phase 06 |
| `#ecad0a` accent-yellow, `#209dd7` accent-blue, `#753991` accent-purple | PLAN.md §2 |
| `#26a69a` up / `#ef5350` down | Phase 07 D-02 |
| Recharts `<Treemap>` for heatmap | CONTEXT.md D-01 |
| Binary up/down heatmap coloring | CONTEXT.md D-02 |
| Heatmap label = ticker + P&L %, click selects | CONTEXT.md D-03 |
| Recharts `<LineChart>` over all snapshots | CONTEXT.md D-04 |
| Dotted $10k reference line | CONTEXT.md D-05 |
| Stroke flips at break-even | CONTEXT.md D-06 |
| Right-edge ~380px drawer, default open, push layout | CONTEXT.md D-07 |
| 3-dot animated thinking bubble | CONTEXT.md D-08 |
| GET /api/chat/history on mount | CONTEXT.md D-09 |
| Inline action cards under assistant | CONTEXT.md D-10 |
| Status-coded card colors (green/gray/red) | CONTEXT.md D-11 |
| 800ms action-card pulse + position-row flash | CONTEXT.md D-12 |
| Per-panel skeleton blocks | CONTEXT.md D-13 |
| FastAPI StaticFiles mount AFTER routers | CONTEXT.md D-14 |
| `skipTrailingSlashRedirect: true` | CONTEXT.md D-15 |
| Vitest + RTL + MockEventSource | CONTEXT.md D-16 (Phase 6 inheritance) |
| `recharts` as new prod dep | CONTEXT.md D-17 |
| Heatmap empty-state copy + cold-cache fallback | Researcher locked from Claude's Discretion |
| P&L 1-snapshot empty state | Researcher locked from Claude's Discretion |
| P&L tooltip format (date + total + delta vs $10k) | Researcher locked from Claude's Discretion |
| Layout = tabbed center column (Chart / Heatmap / P&L) | Researcher locked from Claude's Discretion |
| Action card layout (verb + ticker + detail + status; mono numerics) | Researcher locked from Claude's Discretion |
| Failed-action error string map | Researcher locked from Claude's Discretion (extends Phase 7 D-07) |
| Chat input keyboard contract (Enter / Shift+Enter / Cmd+Enter) | Researcher locked from Claude's Discretion |
| Empty chat copy ("Ask me about your portfolio or tell me to trade.") | Researcher locked from Claude's Discretion |
| Manual-trade flash equivalence with agentic flash | Researcher locked from Claude's Discretion |
| Cmd+K drawer-focus shortcut | Deferred (CONTEXT.md "optional") |
| WCAG AA contrast checks | Researcher default; Phase 07 §4.3 inheritance |
| `prefers-reduced-motion` fallbacks for all four motion primitives | Researcher default |

---

## 15. Handoff Notes

**For the planner:** Tasks should land in roughly this order so each gate
catches issues early:

1. **APP-02 + dev-redirect fix** (single plan, single commit each):
   - Add `skipTrailingSlashRedirect: true` to `next.config.mjs` (D-15).
   - Mount `StaticFiles(directory="frontend/out", html=True)` at `/` AFTER
     routers in `backend/app/lifespan.py` (D-14).
   - Validation: `uv run uvicorn app.main:app` + `npm run build` + curl `/`
     returns the index, curl `/api/health` returns `{"status":"ok"}`, curl
     `/api/stream/prices` works in dev (no 308 chain).
2. **Install `recharts`** (D-17) and add the API client + store extensions:
   - `npm install recharts@^2.x`.
   - Add `getPortfolioHistory()` to `lib/api/portfolio.ts`.
   - Add `lib/api/chat.ts` with `getChatHistory()` + `postChat()`.
   - Extend `price-store.ts`: `selectedTab` slice, `tradeFlash` slice,
     `setSelectedTab`, `flashTrade(ticker, dir)`, `selectTradeFlash(ticker)`.
3. **TabBar + Tabbed center column rewire of `Terminal.tsx`** (small,
   localized).
4. **`<Heatmap />` + `<HeatmapCell />`** (FE-05).
5. **`<PnLChart />` + `<PnLTooltip />`** (FE-06).
6. **Skeleton primitive + per-panel skeletons** (FE-11 D-13). Land before
   chat so the chat-thread skeleton is testable on first paint.
7. **Chat drawer shell** (`<ChatDrawer />` + `<ChatHeader />` toggle).
   Default-open. Drawer slide animation. Wraps existing 3-col grid in flex
   row.
8. **Chat thread + messages + history fetch** (`<ChatThread />`,
   `<ChatMessage />`).
9. **Action cards** (`<ActionCardList />`, `<ActionCard />`). Includes the
   pulse + position-row flash machinery (D-12).
10. **Chat input + ThinkingBubble** (`<ChatInput />`, `<ThinkingBubble />`).
    Wires `postChat` mutation, optimistic user message, in-flight bubble,
    on-resolve action-card pulse trigger.
11. **`prefers-reduced-motion` block in `globals.css`** (one commit).
12. **Vitest tests per §13 Test Map** (~22 new tests).
13. **Build gate:** `npm run test:ci && npm run build` green; backend
    `uv run pytest` green; manual smoke: open `/`, see terminal, default
    chat is open, switch tabs, ask the assistant to "buy 1 AAPL", watch
    card pulse + position row flash + cash decrease.

**For the executor:**
- **Copy color hex values verbatim** — do not substitute Tailwind palette
  names like `teal-500` for the declared CSS-var-backed tokens. Use
  `bg-up`, `bg-down`, `bg-up/20`, `border-l-up`, `border-l-down`,
  `border-l-foreground-muted` — Tailwind v4 derives these from the `@theme`
  block.
- **Recharts inside Recharts:** wrap every Recharts chart in
  `<ResponsiveContainer width="100%" height="100%">`. Recharts requires
  explicit dimensions; without `ResponsiveContainer` the chart silently
  collapses to 0×0.
- **Heatmap content prop:** Recharts passes `(node) => ReactElement` —
  destructure `{x, y, width, height, depth, payload}` (your data merged
  in) and return a `<g>...</g>`. Do NOT use HTML tags inside; this is SVG.
- **Use `'use client'` at the top** of every Phase 8 component (heatmap,
  P&L, chat tree, tab bar). Recharts requires a browser; the chat tree
  uses `useState` + `useMutation`.
- **Do NOT open a second `EventSource`.** All live price data flows
  through the existing Phase 06 store. Heatmap and P&L subscribe via
  selectors only; chat does not subscribe to prices at all.
- **Do NOT introduce a toast / notification library.** Inline action cards
  (D-10/D-11), inline send-error (`<p role="alert">`), and the existing
  Phase 7 trade-bar inline error are the entire user-feedback surface.
- **800ms timer for trade-flash** must use `setTimeout` cleared on
  store `disconnect()` / `reset()`, mirroring Phase 7's price-flash timer
  Map pattern.
- **Auto-scroll the chat thread** with `useLayoutEffect` (not
  `useEffect`) so the scroll lands before paint and the user never sees
  the "old" position briefly.
- **`html=True` on StaticFiles** is critical — without it, `/` returns
  404 instead of `index.html`.
- **Keep each component ≤120 lines.** The action-card module is the most
  at risk; split rendering of trade vs watchlist into a sub-component if
  it grows.
- **No Cmd+K drawer-focus shortcut in Phase 8.** Deferred.

**For the UI checker:** Validate that:
1. Spacing uses only multiples of 4px (`w-[380px]` is the sole declared
   exception — width, not spacing).
2. Typography declares no new sizes/weights beyond Phase 7 (4 sizes, 2
   weights total).
3. Color tokens are unchanged — `globals.css` has the **same** `@theme`
   and `:root` values as after Phase 7.
4. Copy matches §8 verbatim, including the exact failed-action error
   strings.
5. No emojis anywhere.
6. No out-of-scope surfaces were built (no Dockerfile, no Playwright, no
   toast, no Cmd+K shortcut, no time-window selector on P&L, no sector
   coloring on heatmap, no suggested-prompt buttons, no responsive
   stacking).
7. `prefers-reduced-motion` block is present in `globals.css` and
   disables all four animations.
8. The `next.config.mjs` patch is exactly `skipTrailingSlashRedirect:
   true` — nothing else.
9. `lifespan.py` mounts `StaticFiles` AFTER all routers (the catch-all
   route precedence is non-negotiable).

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | *(not initialized — no components.json)* | not applicable |
| *(no third-party registries)* | *(none)* | not applicable |

Phase 08 adds exactly one prod npm dep (`recharts@^2.x`). First-party,
audited, MIT, widely deployed. No vetting gate triggered.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
