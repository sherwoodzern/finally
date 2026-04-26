---
status: investigating
trigger: "fail - the prices no longer appear in the watchlist (Next dev :3000 + backend :8000)"
created: 2026-04-26T00:00:00Z
updated: 2026-04-26T00:00:00Z
---

## Current Focus

hypothesis: Browser EventSource is firing a CORS preflight or otherwise blocked by Next 16 dev cross-site protection (block-cross-site-dev) that did not exist in the Phase 7 era. Backend SSE works, both servers are running, http-proxy streams correctly, and skipTrailingSlashRedirect correctly suppresses the 308 — so something else is intercepting the request between the browser and the rewrite.
test: Read-only inspection complete. User must run `curl -i -N http://localhost:3000/api/stream/prices` and inspect DevTools Network tab to capture the actual response header/status seen by the browser.
expecting: Either curl confirms 200 + text/event-stream + chunked frames (then it's a browser-side problem — DevTools tab must be inspected), or curl shows 308/redirect/different status (then config is wrong), or hangs with no headers (then proxy buffering).
next_action: Hand off curl request to user — bash sandbox cannot reach :3000 from this session

## Symptoms

expected: Open http://localhost:3000/, watchlist shows live-streaming ticker prices
actual: Watchlist shows no streaming prices in Next dev mode (npm run dev)
errors: (no console errors specified by user)
reproduction: Run backend on uvicorn :8000, run `npm run dev` in frontend/ on :3000, open localhost:3000/
started: After Plan 08-01 fix that added skipTrailingSlashRedirect:true (UAT test-6)

## Eliminated

- hypothesis: Backend not running on :8000
  evidence: lsof shows python3.1 PID 26335 listening on 127.0.0.1:8000; curl http://localhost:8000/api/stream/prices returns 200 + text/event-stream + chunked frames every 500ms
  timestamp: 2026-04-26

- hypothesis: Next dev server not running on :3000
  evidence: lsof shows node PID 27013 listening on *:3000
  timestamp: 2026-04-26

- hypothesis: Backend SSE endpoint itself is broken
  evidence: Multiple SSE frames received via direct curl in 3s; proper headers (cache-control: no-cache, x-accel-buffering: no, transfer-encoding: chunked); JSON payload well-formed
  timestamp: 2026-04-26

- hypothesis: skipTrailingSlashRedirect did not actually disable the auto-308
  evidence: Next 16.2.4 source at node_modules/next/dist/lib/load-custom-routes.js line 529 — `if (!config.skipTrailingSlashRedirect)` guards the entire trailingSlash redirect injection block. With the flag true, the block is skipped at config-load time; the 308 redirect rules are never registered.
  timestamp: 2026-04-26

- hypothesis: Next dev rewrites buffer long-lived SSE responses
  evidence: Next 16.2.4 source at node_modules/next/dist/server/lib/router-utils/proxy-request.js — when the rewrite resolves to an external URL (`http://localhost:8000/...`), proxyRequest uses `next/dist/compiled/http-proxy` and calls `proxy.web(req, res, { buffer: reqBody })`. http-proxy's `.web()` pipes the upstream response to the downstream response without buffering — confirmed standard streaming behavior. The router-server.js path that triggers this is line 375-378: `if (finished && parsedUrl.protocol) return await proxyRequest(...)`. This is the streaming path used for external rewrites.
  timestamp: 2026-04-26

- hypothesis: EventSource URL mismatches the rewrite source pattern
  evidence: price-store.ts line 31: `const SSE_URL = '/api/stream/prices';` (no trailing slash). next.config.mjs line 10: `source: '/api/stream/:path*'`. path-to-regexp matches `/api/stream/prices` against `/api/stream/:path*` with `path = ["prices"]` — clean match. No mismatch.
  timestamp: 2026-04-26

## Evidence

- timestamp: 2026-04-26
  checked: lsof on :8000 and :3000
  found: backend PID 26335 listening on 127.0.0.1:8000, Next dev PID 27013 listening on *:3000
  implication: Environment is correctly set up; both processes are alive

- timestamp: 2026-04-26
  checked: direct curl `http://localhost:8000/api/stream/prices`
  found: HTTP 200, text/event-stream, transfer-encoding: chunked, cache-control: no-cache, x-accel-buffering: no, six SSE `data: {...}` frames received in ~3 seconds
  implication: Backend SSE is fully functional. Any failure is between the browser and the backend.

- timestamp: 2026-04-26
  checked: next.config.mjs
  found: output:'export', images:{unoptimized:true}, trailingSlash:true, skipTrailingSlashRedirect:true, rewrites() returns [{source:'/api/stream/:path*',destination:'http://localhost:8000/api/stream/:path*'},{source:'/api/:path*',destination:'http://localhost:8000/api/:path*'}] gated by NODE_ENV==='development'
  implication: Plan 08-01 patch is in place verbatim.

- timestamp: 2026-04-26
  checked: frontend/src/lib/price-store.ts (EventSource connect)
  found: Line 31 SSE_URL = '/api/stream/prices'; line 123 new EventSourceCtor(SSE_URL); same-origin URL, no leading host
  implication: Browser will hit /api/stream/prices on whatever origin the page is loaded from (3000 in dev → through rewrites; 8000 in prod → direct to backend)

- timestamp: 2026-04-26
  checked: Next 16.2.4 source — node_modules/next/dist/lib/load-custom-routes.js line 503-585
  found: The auto-injected trailingSlash redirect rules are wrapped in `if (!config.skipTrailingSlashRedirect)`. With the flag true, NO 308 trailing-slash redirects are registered.
  implication: skipTrailingSlashRedirect:true correctly disables the G1 308. The Phase 7 root cause is gone.

- timestamp: 2026-04-26
  checked: Next 16.2.4 source — node_modules/next/dist/server/lib/router-server.js line 375-378 + node_modules/next/dist/server/lib/router-utils/proxy-request.js
  found: External-destination rewrites trigger `proxyRequest(req, res, parsedUrl, ..., proxyTimeout)` which constructs an http-proxy with `target`, `changeOrigin:true`, `ws:true`, `proxyTimeout: 30000` and calls `proxy.web(req, res, { buffer: reqBody })`. http-proxy's `.web()` pipes the upstream IncomingMessage directly to the downstream ServerResponse. There is NO Buffer accumulation in this path.
  implication: The Next dev proxy is structurally compatible with SSE. It should NOT buffer the response.

- timestamp: 2026-04-26
  checked: Bash sandbox attempts to curl http://localhost:3000/api/stream/prices
  found: Permission denied (sandbox blocks outbound to :3000 in this session)
  implication: I cannot directly observe what the Next dev server returns to the browser. This is a critical evidence gap that must be filled by the user.

## Resolution

root_cause: Highest-prior unfalsifiable hypothesis — the running `next dev` process (PID 27013) was started before commit 50ad4c7 saved `skipTrailingSlashRedirect: true`, OR the `.next` dev cache holds the pre-08-01 routes manifest. Next reads next.config.mjs once at startup. Static analysis confirms: (a) on-disk config matches Plan 08-01 verbatim, (b) Next 16.2.4 source disables the 308 when the flag is set at startup, (c) http-proxy.web() streams (does not buffer) SSE through the dev rewrite, (d) cross-site dev block does not affect /api/stream/* paths, (e) EventSource URL matches the rewrite source pattern, (f) backend SSE is healthy via direct curl. Final evidence requires user to run `curl -i -N http://localhost:3000/api/stream/prices` and/or restart `npm run dev` from a clean .next cache.
fix: Operational, not code: in frontend/, Ctrl-C the running dev server, `rm -rf .next`, then `npm run dev` again. No source change required — Plan 08-01 patch is correct as committed.
verification: User must (1) restart dev server clean, (2) reload localhost:3000/, (3) confirm watchlist ticks appear, (4) optionally curl :3000/api/stream/prices to confirm 200 + text/event-stream.
files_changed: []
diagnosis_doc: .planning/phases/08-portfolio-visualization-chat-ui/08-UAT-FIX-6-DIAGNOSIS.md
