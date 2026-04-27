---
status: resolved
phase: 08-portfolio-visualization-chat-ui
source: [08-VERIFICATION.md]
started: 2026-04-26T13:30:00Z
updated: 2026-04-26T15:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Heatmap recolors live as ticks flow
expected: "Treemap shows one cell per position, sized by quantity*price, fill flips between var(--color-up) and var(--color-down) within ~1s of P&L crossing break-even; cold-cache cells render var(--color-surface-alt)"
result: pass

### 2. P&L chart extends in real time over a multi-snapshot session
expected: "Stroke flips at break-even (last_total >= 10000 → up green, < 10000 → down red); dotted $10k ReferenceLine remains visible; chart redraws when a new snapshot arrives via the 15s refetch"
result: pass

### 3. Agentic-trade visual moment (chat → trade + watchlist + flash)
expected: "ThinkingBubble appears within ~100ms of submit; assistant message + ActionCards render in the order watchlist_changes → trades; executed cards pulse for ~800ms; PositionRow flashes bg-up/20 simultaneously"
result: pass
fixed_by: "commit c2a2c88 (postChat body field rename content -> message); verified by user after rebuild"

### 4. Chat drawer collapse/expand transition feel
expected: "w-[380px] ↔ w-12 transition runs over 300ms with no jank; under prefers-reduced-motion the transition is instant"
result: pass

### 5. ChatInput keyboard contract
expected: "Shift+Enter inserts a newline; Enter on whitespace-only content is a no-op; Enter on non-empty content submits"
result: pass

### 6. G1 SSE dev fix end-to-end
expected: "On `npm run dev` (Next dev :3000), EventSource against /api/stream/prices stays connected and SSE frames flow without the 308→307 redirect chain"
result: pass
fixed_by: "Environmental — clean dev restart (rm -rf frontend/.next + npm run dev). On-disk config unchanged. Verified by user after operational fix."

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Chat-driven trades execute and chat-driven watchlist changes are applied; assistant ActionCards reflect the executed actions; PositionRow + watchlist update simultaneously"
  status: resolved
  reason: "User reported: fail - the purchase of NVDA did not work and PYPL was not added to the watchlist. Follow-up: the chat request returned HTTP 422 (FastAPI body validation error)."
  severity: major
  test: 3
  artifacts: []
  missing: []
  diagnosis_lead: "HTTP 422 on POST /api/chat → frontend request body shape mismatches backend ChatRequest Pydantic schema. Inspect frontend/src/lib/api/chat.ts postChat() body vs backend/app/chat/models.py ChatRequest."

- truth: "On `npm run dev` (Next dev :3000), EventSource against /api/stream/prices stays connected and SSE frames flow continuously to the watchlist UI"
  status: resolved
  reason: "User reported: fail - the prices no longer appear in the watchlist"
  severity: major
  test: 6
  artifacts: []
  missing: []
  diagnosis_lead: "next.config.mjs has both skipTrailingSlashRedirect: true (G1 fix) AND an async rewrites() proxy for /api/stream/:path* and /api/:path* → http://localhost:8000. Two likely causes: (1) backend on :8000 is not running while dev :3000 is open — the proxy has nothing to forward to. (2) Next dev rewrites buffer long-lived SSE responses, breaking EventSource even with the redirect fix. Inspect DevTools network tab for the actual /api/stream/prices request status (404 vs pending vs immediately-closed) and whether the backend uvicorn process is still up."
  diagnosis_resolution: "Environmental. Backend SSE streams correctly on :8000 (curl -i -N confirmed 6 frames in 3s). next.config.mjs is correct on-disk. Next 16.2.4 rewrites pipe upstream responses without buffering (proxy.web in next/dist/compiled/http-proxy). Most likely root cause: dev server (PID 27013) is running on a stale .next cache predating commit 50ad4c7 (Plan 08-01 G1 fix), so the in-memory routes manifest still has the 308 trailingSlash redirect rules active. Operational fix: in the frontend/ terminal: Ctrl-C the dev server; rm -rf .next; npm run dev; reload localhost:3000. If still broken after clean restart, capture curl -i -N http://localhost:3000/api/stream/prices for decisive evidence. Production path is unaffected — UAT 1-5 already confirmed FastAPI static mount on :8000 works."
