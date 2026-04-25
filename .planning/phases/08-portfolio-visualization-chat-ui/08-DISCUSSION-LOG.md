# Phase 8: Portfolio Visualization & Chat UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or
> execution agents. Decisions are captured in CONTEXT.md — this log
> preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 08-portfolio-visualization-chat-ui
**Areas selected by user:** Visualization styling, Demo polish priorities
**Areas presented but not selected:** Layout & chat dock, Action confirmations in chat
*(Layout/dock and action-confirmation specifics ended up captured during the demo-polish discussion.)*

---

## Visualization styling

### Q1 — Heatmap implementation (FE-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Recharts `<Treemap>` | One new dep, SVG matches P&L chart, content prop allows custom rectangle rendering | ✓ |
| Hand-rolled CSS grid | Flex/grid divs sized by computed weights; no library, full control, more code (~50–100 LOC) | |
| Dedicated treemap lib (e.g., `react-d3-treemap`) | Best treemap layout quality (squarified) but a third chart-ish dep | |

**User's choice:** Recharts `<Treemap>` (Recommended)
**Notes:** Reuses Recharts (which we're already adding for P&L chart) — one
new dep total for the phase, consistent SVG visual with the line chart.

### Q2 — Heatmap color scale

| Option | Description | Selected |
|--------|-------------|----------|
| Binary up/down | Green `#26a69a` when P&L ≥ 0 else red `#ef5350`, reuses Phase 7 D-02 palette | ✓ |
| P&L % gradient | Color intensity scales with magnitude (-10% deep red → +10% deep green) | |
| Sector-coded with P&L overlay | Color by sector, P&L badge overlay; Bloomberg-like | |

**User's choice:** Binary up/down (Recommended)
**Notes:** Phase 7's D-02 rationale (instant trading-green/red readability)
applies. One palette serves four surfaces (price flash, sparkline stroke,
P&L text, heatmap).

### Q3 — Heatmap content & interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Ticker + P&L %, click selects ticker | Bold ticker, P&L % below; click drives main chart selection; cash excluded | ✓ |
| Ticker only, click selects | Just ticker; tooltip shows P&L on hover | |
| Ticker + P&L $/%, no click (display-only) | Richer label, no interaction | |

**User's choice:** Ticker + P&L %, click selects (Recommended)
**Notes:** Uses Phase 7's existing `selectedTicker` state, so heatmap and
watchlist drive the main chart from the same handler. Cash lives in the
header; the heatmap is positions-only.

### Q4 — P&L line chart time window & reference line (FE-06)

| Option | Description | Selected |
|--------|-------------|----------|
| All snapshots + $10k reference line | All rows from `/api/portfolio/history`, dotted horizontal at $10k starting cash | ✓ |
| Last 24h window, no reference line | Filter to recent snapshots only; loses the reference anchor | |
| Tabbed time window selector (1h / 1d / All) | More UX, more state — Phase 7 D-Main-Chart parallel: timeframe is a polish-pass concern | |

**User's choice:** All snapshots + $10k starting reference line (Recommended)
**Notes:** Stroke flips at break-even (`--color-up` when ≥ $10k else
`--color-down`). $10k is the demo's emotional anchor — instant "am I up
or down vs starting?".

---

## Demo polish priorities

### Q1 — Visible payoff for LLM auto-executed trades (the agentic "wow")

| Option | Description | Selected |
|--------|-------------|----------|
| Action card pulse + position-row flash | Two coordinated ~800ms animations; chat card pulses, positions row flashes the same color; header total/cash re-renders | ✓ |
| Action card pulse only | Just chat side; positions update without flash | |
| Implicit (no animations), numbers update silently | Clean, but underplays the agentic moment PROJECT.md calls "non-negotiable" | |

**User's choice:** Action card pulse + position-row flash (Recommended)
**Notes:** Phase 7 D-08 ("implicit confirmation") deferred position-row
flash; Phase 8 D-12 picks it up — but tagged at 800ms vs Phase 7's 500ms
price flash so the two read as distinct events.

### Q2 — LLM loading state inside chat (FE-09)

| Option | Description | Selected |
|--------|-------------|----------|
| Animated 3-dot "thinking" bubble | Pure CSS keyframes; chat-app convention; reads "AI thinking" | ✓ |
| Skeleton message placeholder | Grey rounded rectangle hinting at incoming message shape | |
| Spinner next to Send button | Minimal; eye is on the thread, not the input | |

**User's choice:** Animated 3-dot "thinking" bubble (Recommended)
**Notes:** Cerebras inference is ~1–3s, so this rarely lingers — perfect
brief anchor moment.

### Q3 — Initial page load (cold start)

| Option | Description | Selected |
|--------|-------------|----------|
| Skeleton blocks per panel | Each panel renders muted-grey skeleton matching final shape | ✓ |
| Loading spinner overlay | Single full-screen or panel spinner; generic | |
| Empty state text per panel | Each panel shows "loading..." copy until data lands | |

**User's choice:** Skeleton blocks per panel (Recommended)
**Notes:** Removes the "flicker of empty/zero" on cold start. Polish
element non-developers actually feel; generic spinner reads as
"broken/slow".

### Q4 — Chat panel dock & toggle (FE-09)

| Option | Description | Selected |
|--------|-------------|----------|
| Right-edge drawer, default open, push layout | ~380px column, opens by default; toggle collapses to icon strip; smooth slide | ✓ |
| Right-edge drawer, default closed, overlay | Hidden behind header button; opens floating over right side | |
| Bottom drawer, slides up from footer | Full-width bottom; eats viz space; breaks PLAN.md §10 "sidebar" framing | |

**User's choice:** Right-edge drawer, default open, push layout (Recommended)
**Notes:** Default open trades horizontal real estate for first-impression
impact — the demo lands with the AI visible. Pushes the existing 3-col
grid leftward; full page becomes ~1760px wide (consistent with desktop-
first boundary from Phase 7).

---

## Claude's Discretion

The following decisions were left to the planner without explicit
user-facing questions:

- Layout placement of heatmap and P&L chart (tabbed center column vs
  stacked second row)
- Action-card detail layout (icon, padding, monospace numerics)
- Chat input UX (Enter / Shift+Enter), empty chat welcome line
- Failed-action error message strings (reuse Phase 7 D-07 map)
- Manual trade-bar flash-on-success for consistency with chat auto-trades
- Optional Cmd+K / Ctrl+K shortcut to focus chat input
- P&L chart with 0/1 snapshots (skeleton + empty state until ≥ 2 points)
- Tooltip detail on the P&L chart

## Deferred Ideas

- Tabbed P&L chart time-window selector (1h / 1d / All) — polish/v2
- Heatmap with a cash slice — polish/v2
- Sector coloring on heatmap — needs taxonomy, v2 only
- Suggested-prompt buttons in empty chat — polish-phase concern
- Token-by-token chat streaming (CHAT-07) — already v2
- Toast / global notification system — explicitly rejected (Phase 7 carry)
- Dedicated trade-history view (HIST-01) — v2
- Mobile/tablet responsive stacking + a11y (POLISH-01) — v2
- Heatmap drill/zoom interactions — out of scope
