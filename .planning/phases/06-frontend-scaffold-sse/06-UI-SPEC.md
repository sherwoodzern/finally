---
phase: 06
name: frontend-scaffold-sse
status: draft
design_system: manual (Tailwind v4 CSS-first, no shadcn)
created: 2026-04-23
---

# Phase 06 — UI Design Contract

## Scope & Intent

Phase 06 ships the **frontend scaffold and the SSE wire** — not product UI.
Anything a user would recognize as the FinAlly trading terminal (watchlist,
charts, positions, trade bar, header value ticker, portfolio heatmap, P&L
chart, AI chat) is deferred to Phase 07 and Phase 08 and will have its own
UI-SPEC.md written at that time.

What this phase renders for a human to look at:

1. **`src/app/page.tsx`** — placeholder landing. One heading, one short
   sentence of dev-facing copy. Not a product surface.
2. **`src/app/debug/page.tsx`** — developer diagnostic table that proves the
   SSE wire is alive and the Zustand price store is populated. Minimal
   styling, dark-theme defaults, monospace numbers.
3. **Global theme tokens** — the dark palette, the three brand accents, the
   surface/border semantic names. Every later phase imports these.

Everything in this document is prescriptive. The executor should not invent
additional visual elements.

---

## 1. Design System State

| Item                      | Value                                                       |
|---------------------------|-------------------------------------------------------------|
| shadcn initialized?       | No                                                          |
| `components.json` present | No                                                          |
| Tool                      | none — manual tokens via Tailwind v4 `@theme` in CSS        |
| Component library         | None in phase 06 (shadcn may be introduced later if needed) |
| Styling                   | Tailwind v4 CSS-first (`@import "tailwindcss"` + `@theme`)  |
| Icon library              | None in phase 06                                            |
| Registry safety gate      | N/A — no external registries referenced                     |

**Rationale:** Phase 06 intentionally avoids component libraries because the
only visible surface is a debug table. Introducing shadcn here would be
over-engineering. Later phases may initialize shadcn when real product UI
lands.

---

## 2. Spacing

Tailwind v4 defaults (4px base unit — `0.25rem` at `16px` root) are used
unchanged.

| Token          | Value   | Usage                                          |
|----------------|---------|------------------------------------------------|
| `p-2` / `gap-2` | `8px`  | Table cell padding, stack gap between rows     |
| `p-4` / `gap-4` | `16px` | Section padding, header-to-table gap           |
| `p-6`          | `24px` | Page outer padding (main container on `/debug` and `/`) |
| `p-8`          | `32px` | Not used in phase 06 — reserved for later      |

**Rule:** Only multiples of 4px. No arbitrary `px-[13px]` style values.

---

## 3. Typography

System font stack (no external web font loaded in phase 06). Monospace is
reserved for numeric data in the debug table.

| Role                 | Family                                                            | Size  | Weight | Line-height |
|----------------------|-------------------------------------------------------------------|-------|--------|-------------|
| Body / default       | `ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif` | 16px  | 400    | 1.5         |
| Heading (h1)         | same                                                              | 28px  | 600    | 1.2         |
| Heading (h2)         | same                                                              | 20px  | 600    | 1.3         |
| Small / caption      | same                                                              | 14px  | 400    | 1.4         |
| **Monospace (data)** | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`        | 14px  | 400    | 1.4         |

**Sizes declared:** 4 (28, 20, 16, 14). **Weights declared:** 2 (400, 600).
Matches the 3–4 sizes / 2 weights ceiling.

**Usage rule:** Every numeric price, change, delta, timestamp in the debug
table uses the monospace family so digit columns align. Ticker symbols may
use monospace as well.

---

## 4. Color Contract

### 4.1 Palette (CSS custom properties)

All colors are declared once in `src/app/globals.css` inside a Tailwind v4
`@theme` block. Nothing lives in a `tailwind.config.ts` — there is no config
file in phase 06.

```css
/* src/app/globals.css */
@import "tailwindcss";

@theme {
  /* Surfaces — the 60% + 30% */
  --color-surface:      #0d1117;  /* primary background (60%)  */
  --color-surface-alt:  #1a1a2e;  /* opt-in elevated panels (30%) */
  --color-border-muted: #30363d;  /* dividers / table grid lines */

  /* Text */
  --color-foreground:        #e6edf3;  /* primary text on surface */
  --color-foreground-muted:  #8b949e;  /* secondary text / labels */

  /* Accents — the 10%, brand-reserved */
  --color-accent-yellow: #ecad0a;
  --color-accent-blue:   #209dd7;
  --color-accent-purple: #753991;

  /* Semantic (for price direction — reserved for later phases but
     declared now so phase 07 does not re-open this decision) */
  --color-up:   #3fb950;  /* green, uptick / positive P&L */
  --color-down: #f85149;  /* red, downtick / negative P&L */
}
```

### 4.2 60 / 30 / 10 Split

| Share | Role              | Color(s)                                |
|-------|-------------------|-----------------------------------------|
| 60%   | Dominant surface  | `--color-surface` (`#0d1117`)           |
| 30%   | Secondary surface | `--color-surface-alt` (`#1a1a2e`) and `--color-border-muted` (`#30363d`) |
| 10%   | Accent            | `--color-accent-yellow`, `--color-accent-blue`, `--color-accent-purple` |

**Accent is reserved for (phase 06 scope only):**
- Links and focus rings on `/` and `/debug` → `--color-accent-blue`
- The h1 heading underline/label on the placeholder landing (optional,
  Claude's discretion) → `--color-accent-yellow`
- `--color-accent-purple` is **not used** in phase 06. It is reserved for the
  Submit button on the trade bar (phase 07).

**Semantic colors:**
- `--color-up` and `--color-down` are declared but **not rendered** in phase
  06. The debug table shows the `direction` field as plain text (`"up"`,
  `"down"`, `"flat"`) — color encoding arrives in phase 07 with the real
  watchlist.

### 4.3 Utility Class Names (Tailwind v4 auto-generated)

The `@theme` block above generates these utilities automatically:

| Utility              | Maps to                    |
|----------------------|----------------------------|
| `bg-surface`         | `--color-surface`          |
| `bg-surface-alt`     | `--color-surface-alt`      |
| `border-border-muted`| `--color-border-muted`     |
| `text-foreground`    | `--color-foreground`       |
| `text-foreground-muted` | `--color-foreground-muted` |
| `text-accent-yellow` | `--color-accent-yellow`    |
| `text-accent-blue`   | `--color-accent-blue`      |
| `text-accent-purple` | `--color-accent-purple`    |
| `text-up` / `text-down` | semantic up/down        |

The executor should apply `bg-surface text-foreground` on the root `<body>`
(via `src/app/layout.tsx`) so every page defaults to dark.

### 4.4 Accessibility

Contrast ratios (WCAG AA text minimum 4.5:1):

| Pair                                         | Ratio    | Pass |
|----------------------------------------------|----------|------|
| `#e6edf3` foreground on `#0d1117` surface    | ~15.4:1  | AAA  |
| `#8b949e` muted on `#0d1117` surface         | ~6.3:1   | AA   |
| `#e6edf3` foreground on `#1a1a2e` surface-alt| ~13.9:1  | AAA  |
| `#209dd7` accent-blue on `#0d1117`           | ~5.6:1   | AA   |
| `#ecad0a` accent-yellow on `#0d1117`         | ~9.1:1   | AAA  |

**Focus rings:** use `focus-visible:outline-2 focus-visible:outline-accent-blue`
on any interactive element. Phase 06 has no buttons, but the executor must
ensure `<a>` links pick up the default ring.

---

## 5. Page Contracts

### 5.1 `/` — Placeholder Landing (`src/app/page.tsx`)

**Purpose:** Prove the app boots and the theme tokens are wired. Not a
product page.

**Layout:**

```
┌─────────────────────────────────────────┐
│  (body: bg-surface, text-foreground)    │
│                                         │
│   FinAlly                               │  ← h1, 28px/600
│                                         │
│   AI Trading Workstation                │  ← p, 16px/400, foreground-muted
│                                         │
│   Dev note: see /debug for the live     │  ← p, 14px, foreground-muted
│   price stream.                         │
│                                         │
└─────────────────────────────────────────┘
```

**Rules:**
- Outer container: `min-h-screen p-6` with `bg-surface text-foreground`.
- Content vertically centered or left-aligned at top — Claude's discretion.
- No images, no logo file, no marketing copy, no product UI.
- No emojis. Anywhere.
- The `/debug` reference is plain text — may be wrapped in an `<a>` using
  `text-accent-blue underline underline-offset-2`.

**Copywriting contract (exact strings):**
- H1: `FinAlly`
- Subtitle: `AI Trading Workstation`
- Dev note: `Dev note: see /debug for the live price stream.`

### 5.2 `/debug` — Price Stream Diagnostic (`src/app/debug/page.tsx`)

**Purpose:** Prove `PriceStreamProvider` is mounted, `EventSource` is open,
and the Zustand store is receiving `price_update` events. Developer-facing.

**Layout — vertical stack:**

```
┌────────────────────────────────────────────────────────────┐
│  (body: bg-surface text-foreground, p-6)                   │
│                                                            │
│  Price Stream Debug                               [h1]     │
│  ────────────────────────────────────────────────          │
│                                                            │
│  Status: connected   |   Tickers: 10   |   Last tick: 12:34:56 UTC │
│                                                            │
│  ┌───────┬────────┬────────┬────────┬──────┬──────────┬──────────────┬──────────────┐
│  │Ticker │ Price  │ Prev   │ Change │  Δ%  │ Direction│ Session Start│ Last Tick    │
│  ├───────┼────────┼────────┼────────┼──────┼──────────┼──────────────┼──────────────┤
│  │ AAPL  │190.23  │190.21  │ +0.02  │+0.01%│   up     │ 189.50       │ 12:34:56.120 │
│  │ ...   │        │        │        │      │          │              │              │
│  └───────┴────────┴────────┴────────┴──────┴──────────┴──────────────┴──────────────┘
└────────────────────────────────────────────────────────────┘
```

**Header strip (connection status):**
- Plain text, 14px, foreground-muted, separated by a pipe character with
  `px-2` space on each side.
- Three fields, in order: `Status: <connected|reconnecting|disconnected>`,
  `Tickers: <count>`, `Last tick: <ISO-time-of-most-recent-event or "—">`.
- No colored dots in phase 06. The header-dot component belongs to phase 07.

**Table:**
- Columns in order: `Ticker`, `Price`, `Prev`, `Change`, `Δ%`, `Direction`,
  `Session Start`, `Last Tick`.
- Table classes: `w-full border-collapse font-mono text-sm`.
- `thead` cells: `text-left px-2 py-2 border-b border-border-muted text-foreground-muted`.
- `tbody` rows: `border-b border-border-muted`.
- `tbody` cells: `px-2 py-2 text-foreground`.
- Numeric columns (`Price`, `Prev`, `Change`, `Δ%`, `Session Start`) are
  right-aligned: add `text-right`.
- `Direction` column renders the plain string (`up` / `down` / `flat`) with
  no color coding, no icons. Phase 07 adds color.
- `Last Tick` renders `HH:MM:SS.sss` format from the event timestamp.

**Empty state (no ticks received yet):**
- Render a single `<tr>` with one cell spanning all columns:
  `Awaiting first price tick...` in `text-foreground-muted text-center py-4`.

**Error state (SSE disconnected):**
- The header strip status field shows `disconnected`.
- The existing table rows remain visible (stale data is better than no data
  for a debug view).
- Below the table, show: `Connection lost. Reconnecting...` in
  `text-foreground-muted text-sm mt-2`. No retry button in phase 06 —
  `EventSource` reconnects automatically.

**Copywriting contract (exact strings):**
- H1: `Price Stream Debug`
- Status labels: exactly `Status:`, `Tickers:`, `Last tick:` (capitalized,
  trailing colon, space before value).
- Status values: exactly `connected`, `reconnecting`, `disconnected` (lower
  case, matching the `ConnectionStatus` type already defined in RESEARCH.md).
- Empty state: `Awaiting first price tick...`
- Disconnect message: `Connection lost. Reconnecting...`

---

## 6. Interaction Contracts

Phase 06 has essentially no interactions. Explicit non-requirements:

| Interaction            | Status in phase 06                             |
|------------------------|------------------------------------------------|
| Click a ticker row     | **Not interactive.** Just a data row.          |
| Sort columns           | **Not in scope.** Tickers render in insertion / store order. |
| Filter / search        | **Not in scope.**                              |
| Price flash animation  | **Not in scope.** Phase 07 adds it on the real watchlist. |
| Keyboard nav beyond default browser tab order | **Not in scope.**      |
| Theme toggle           | **Locked out** (D-10: dark permanent, no toggle). |

The single interactive element in the whole phase is the `<a href="/debug">`
link on the landing page. It uses `text-accent-blue underline
underline-offset-2 hover:text-accent-yellow`.

---

## 7. Component Inventory

Minimum components created in phase 06:

| Component                    | Path                                    | Role                                  |
|------------------------------|-----------------------------------------|---------------------------------------|
| Root layout                  | `src/app/layout.tsx`                    | `<html>` / `<body>` with dark theme classes; wraps children in `<PriceStreamProvider>` |
| Landing page                 | `src/app/page.tsx`                      | The placeholder described in §5.1     |
| Debug page                   | `src/app/debug/page.tsx`                | The diagnostic table described in §5.2 |
| `PriceStreamProvider`        | `src/components/PriceStreamProvider.tsx` | Invisible — opens `EventSource`, writes into Zustand store |
| Price store                  | `src/store/priceStore.ts`               | Zustand store (not a React component) |

No other components (no Table component, no StatusPill component). Markup is
inline in `debug/page.tsx`. Phase 06 resists the urge to abstract.

---

## 8. Copywriting Contract (consolidated)

Every visible string in the phase. Executor must match exactly.

| Location                         | String                                           |
|----------------------------------|--------------------------------------------------|
| `/` h1                           | `FinAlly`                                        |
| `/` subtitle                     | `AI Trading Workstation`                         |
| `/` dev note                     | `Dev note: see /debug for the live price stream.`|
| `/debug` h1                      | `Price Stream Debug`                             |
| `/debug` status label            | `Status:`                                        |
| `/debug` tickers label           | `Tickers:`                                       |
| `/debug` last-tick label         | `Last tick:`                                     |
| `/debug` status value (live)     | `connected`                                      |
| `/debug` status value (retrying) | `reconnecting`                                   |
| `/debug` status value (dead)     | `disconnected`                                   |
| `/debug` column headers          | `Ticker`, `Price`, `Prev`, `Change`, `Δ%`, `Direction`, `Session Start`, `Last Tick` |
| `/debug` empty state             | `Awaiting first price tick...`                   |
| `/debug` disconnect banner       | `Connection lost. Reconnecting...`               |

**Empty / error / destructive / CTA notes:**
- **CTA:** none in phase 06 (no buttons). The landing page link to `/debug`
  is the only clickable element.
- **Empty state:** see above.
- **Error state:** see above.
- **Destructive actions:** none in phase 06.

No emojis in any string — enforced by project rule (`CLAUDE.md`).

---

## 9. Out of Scope (explicit)

The executor must **not** build the following in phase 06. Each belongs to a
later phase and will have its own UI-SPEC.md.

| Surface                    | Target phase                               |
|----------------------------|--------------------------------------------|
| Watchlist panel            | Phase 07                                   |
| Main ticker chart          | Phase 07                                   |
| Portfolio heatmap          | Phase 07                                   |
| P&L line chart             | Phase 07                                   |
| Positions table            | Phase 07                                   |
| Trade bar (buy/sell)       | Phase 07                                   |
| Header (portfolio total, cash, connection dot) | Phase 07               |
| AI chat panel              | Phase 08                                   |
| Price flash animations     | Phase 07                                   |
| Sparkline mini-charts      | Phase 07                                   |
| Responsive breakpoints beyond default | Phase 07                        |
| shadcn initialization      | Phase 07 (if adopted)                      |
| Light theme / theme toggle | Never in v1 (D-10)                         |

---

## 10. Pre-population Sources

| Field                       | Source                                                        |
|-----------------------------|---------------------------------------------------------------|
| Dark-only theme             | CONTEXT.md D-10                                               |
| `#0d1117` primary surface   | CONTEXT.md color palette; PLAN.md §2                          |
| `#1a1a2e` alt surface       | CONTEXT.md color palette; PLAN.md §2                          |
| `#30363d` muted border      | CONTEXT.md color palette                                      |
| `#ecad0a` accent yellow     | PLAN.md §2 color scheme                                       |
| `#209dd7` accent blue       | PLAN.md §2 color scheme                                       |
| `#753991` accent purple     | PLAN.md §2 color scheme (reserved for submit button)          |
| Tailwind v4 CSS-first `@theme` | CONTEXT.md (Tailwind v4, no `tailwind.config.ts`)          |
| Debug page is minimal dev-only | CONTEXT.md §Out of scope + phase brief                     |
| Landing page is placeholder | CONTEXT.md D-24 (Claude's discretion, minimal)                |
| No emojis                   | `CLAUDE.md` project rule                                      |
| Monospace for numeric data  | Trading-terminal aesthetic, PLAN.md §2; defaulted by researcher |
| Semantic up/down colors declared but unused | Defaulted by researcher to avoid re-opening in phase 07 |
| WCAG AA contrast target     | Defaulted by researcher (industry baseline)                   |

---

## 11. Handoff Notes

**For the planner:** Tasks should cover (a) write `src/app/globals.css` with
the `@theme` block from §4.1, (b) set `bg-surface text-foreground` on
`<body>` in `layout.tsx`, (c) render the exact strings from §8, (d) build
the `/debug` table with the exact columns from §5.2. No abstraction tasks
(no "create a Table component") — keep markup inline.

**For the executor:** The executor should copy color hex values verbatim.
Do not substitute `slate-900` or `zinc-800` for the declared custom tokens.
Do not add Tailwind default accent colors — the brand accents are the only
accents allowed.

**For the UI checker:** The 6 quality dimensions collapse in phase 06
because there is so little visible surface. Validate that:
1. Spacing uses only multiples of 4px.
2. Typography has exactly 4 sizes + 2 weights as declared.
3. Color tokens match §4.1 verbatim.
4. Copy matches §8 verbatim.
5. No emojis anywhere.
6. No out-of-scope surfaces were built.

---

## UI-SPEC COMPLETE

**Phase:** 06 - frontend-scaffold-sse
**Design System:** manual (Tailwind v4 CSS-first, no shadcn)

### Contract Summary
- Spacing: Tailwind v4 4px base, tokens p-2/p-4/p-6 only
- Typography: 4 sizes (28, 20, 16, 14), 2 weights (400, 600), system + monospace
- Color: 60% `#0d1117` / 30% `#1a1a2e` + `#30363d` / 10% yellow+blue+purple brand accents; semantic up/down declared but unused
- Copywriting: 13 exact strings defined (§8)
- Registry: none (no shadcn, no third-party blocks)

### File Created
`.planning/phases/06-frontend-scaffold-sse/06-UI-SPEC.md`

### Pre-Populated From
| Source                | Decisions Used |
|-----------------------|----------------|
| CONTEXT.md            | 7              |
| RESEARCH.md           | 2              |
| PLAN.md               | 4              |
| `CLAUDE.md`           | 1              |
| Researcher defaults   | 3              |
| User input            | 0 (--auto)     |

### Ready for Verification
UI-SPEC complete. Checker can now validate.
