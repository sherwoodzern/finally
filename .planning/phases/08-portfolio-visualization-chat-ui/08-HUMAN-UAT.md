---
status: partial
phase: 08-portfolio-visualization-chat-ui
source: [08-VERIFICATION.md]
started: 2026-04-26T13:30:00Z
updated: 2026-04-26T13:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Heatmap recolors live as ticks flow
expected: "Treemap shows one cell per position, sized by quantity*price, fill flips between var(--color-up) and var(--color-down) within ~1s of P&L crossing break-even; cold-cache cells render var(--color-surface-alt)"
result: [pending]

### 2. P&L chart extends in real time over a multi-snapshot session
expected: "Stroke flips at break-even (last_total >= 10000 → up green, < 10000 → down red); dotted $10k ReferenceLine remains visible; chart redraws when a new snapshot arrives via the 15s refetch"
result: [pending]

### 3. Agentic-trade visual moment (chat → trade + watchlist + flash)
expected: "ThinkingBubble appears within ~100ms of submit; assistant message + ActionCards render in the order watchlist_changes → trades; executed cards pulse for ~800ms; PositionRow flashes bg-up/20 simultaneously"
result: [pending]

### 4. Chat drawer collapse/expand transition feel
expected: "w-[380px] ↔ w-12 transition runs over 300ms with no jank; under prefers-reduced-motion the transition is instant"
result: [pending]

### 5. ChatInput keyboard contract
expected: "Shift+Enter inserts a newline; Enter on whitespace-only content is a no-op; Enter on non-empty content submits"
result: [pending]

### 6. G1 SSE dev fix end-to-end
expected: "On `npm run dev` (Next dev :3000), EventSource against /api/stream/prices stays connected and SSE frames flow without the 308→307 redirect chain"
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
