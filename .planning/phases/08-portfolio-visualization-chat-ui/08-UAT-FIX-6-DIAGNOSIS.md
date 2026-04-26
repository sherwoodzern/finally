---
status: diagnosis-pending-final-evidence
phase: 08-portfolio-visualization-chat-ui
test: UAT 6 — G1 SSE dev fix end-to-end
related_debug_session: ../../.planning/debug/uat-test6-next-dev-sse.md
created: 2026-04-26
mode: read-only investigation, no fix applied
---

## Verdict

**Most-likely root cause:** A *runtime* condition the agent could not directly observe — the user's running `next dev` process (PID 27013) was started **before** the Plan 08-01 commit `50ad4c7` saved `skipTrailingSlashRedirect: true` to disk, OR the `.next` dev cache holds the pre-08-01 routes manifest. Next.js reads `next.config.mjs` once at startup and bakes the redirect rules into the in-memory routes manifest; editing the file while the dev server is running does **not** retroactively remove the auto-308 trailing-slash redirect. The visible symptom is identical to Phase 7 G1: `/api/stream/prices` → 308 → `/api/stream/prices/` → rewritten to `:8000/api/stream/prices/` → FastAPI 307 → `:8000/api/stream/prices` → cross-origin → EventSource refuses to follow → no ticks.

**Confidence:** Medium. All other static evidence (config file, EventSource client URL, Next 16.2.4 source, http-proxy streaming behavior, both processes alive, backend SSE healthy) is consistent with dev SSE *working*. The single hypothesis the agent could not falsify is whether the running dev server is using the new config. This category — config-on-disk vs config-in-memory — is the most common cause of "I applied the fix and it still fails."

**Category:** Environmental (stale dev server / stale `.next` cache). NOT structural (Next dev rewrite is streaming-compatible — http-proxy.web pipes upstream IncomingMessage to downstream ServerResponse without buffering). NOT config (the on-disk config matches the Plan 08-01 spec verbatim).

## Evidence (for the conclusion above)

### Confirmed by direct observation

| Check | Result | Implication |
|---|---|---|
| `lsof -nP -iTCP:8000 -sTCP:LISTEN` | python3.1 PID 26335 LISTEN 127.0.0.1:8000 | Backend is up. |
| `lsof -nP -iTCP:3000 -sTCP:LISTEN` | node PID 27013 LISTEN *:3000 | Dev server is up. |
| `curl -i -N http://localhost:8000/api/stream/prices` (3-second window) | HTTP 200, `text/event-stream`, `transfer-encoding: chunked`, `cache-control: no-cache`, `x-accel-buffering: no`, six `data: {...}` SSE frames received | Backend SSE is fully functional. The bug is between the browser and the backend. |
| Read of `frontend/next.config.mjs` | `skipTrailingSlashRedirect: true` is present on line 6, alongside `trailingSlash: true` (line 5) and the rewrites block | Plan 08-01 patch is on-disk verbatim. |
| Read of `frontend/src/lib/price-store.ts` line 31 | `const SSE_URL = '/api/stream/prices';` (no trailing slash) | EventSource hits the same path the rewrite source pattern expects. |
| Git log of `frontend/next.config.mjs` | Two commits: 3e05fd1 (06-01 initial) and 50ad4c7 (08-01 patch). No subsequent edits. | The flag is not being unset by a later commit. |

### Confirmed by reading Next.js 16.2.4 source

| Question | Answer | Source |
|---|---|---|
| Does `skipTrailingSlashRedirect: true` actually disable the auto-308? | Yes. The entire trailingSlash redirect injection block is wrapped in `if (!config.skipTrailingSlashRedirect) { ... }`. With the flag true at startup, those redirect rules are never registered. | `frontend/node_modules/next/dist/lib/load-custom-routes.js` line 529-585 |
| Does Next dev's external rewrite buffer SSE? | No. External-destination rewrites call `proxyRequest()`, which constructs an `http-proxy` and calls `proxy.web(req, res, { buffer: reqBody })`. `http-proxy.web()` pipes upstream `IncomingMessage` directly to downstream `ServerResponse` — no Buffer accumulation. The proxy is structurally streaming-compatible. | `frontend/node_modules/next/dist/server/lib/router-server.js` lines 375-378 + `frontend/node_modules/next/dist/server/lib/router-utils/proxy-request.js` lines 25-110 |
| Is `block-cross-site-dev` interfering? | No. It only fires when `isInternalEndpoint(req)` is true — that matches `/_next/*` and `/__nextjs*` paths only. `/api/stream/prices` is not internal. | `frontend/node_modules/next/dist/server/lib/router-utils/block-cross-site-dev.js` lines 63-87 |
| Does the rewrite source `/api/stream/:path*` match `/api/stream/prices`? | Yes. path-to-regexp matches `:path*` as zero-or-more segments; `prices` becomes `["prices"]`. Clean match. | next.config.mjs line 10 + Next docs |

### Could NOT confirm directly (sandbox restriction)

| Check | Why blocked |
|---|---|
| `curl -i -N http://localhost:3000/api/stream/prices` | Bash sandbox refused outbound to localhost:3000 throughout the session. Only :8000 was reachable. The single most useful piece of evidence (does the proxy currently return 308 or 200?) cannot be captured from this agent. |
| `ps -p 27013 -o lstart` (when did the dev server start, before or after 50ad4c7?) | Sandbox blocked process inspection. |
| DevTools Network panel for the EventSource on `/api/stream/prices` | Browser-only, requires the user. |

## How to verify (commands for the user — run on the host)

These three commands, run in this order, will discriminate between every hypothesis below in under a minute:

1. **Force a clean dev restart so the on-disk config is loaded**

   ```bash
   # In the frontend/ terminal where `npm run dev` is running, press Ctrl-C.
   cd frontend
   rm -rf .next
   npm run dev
   ```

   Then reload `http://localhost:3000/` and watch the watchlist for ticks.

   - **If prices appear** → root cause was the running dev server holding stale config (the most likely environmental cause).
   - **If prices still do not appear** → continue to step 2.

2. **Capture what the dev server actually returns**

   In a third terminal (with `npm run dev` and `uvicorn` both up):

   ```bash
   curl -i -N --max-time 5 http://localhost:3000/api/stream/prices
   ```

   Expected (good): `HTTP/1.1 200 OK`, `content-type: text/event-stream`, then `data: {...}` frames every ~500ms.

   - **If you see `HTTP/1.1 308`** → the redirect is still being injected. The config is not being honored. Confirm Next 16.2.4's CLI is loading `next.config.mjs` (not a stale `next.config.ts`); confirm there's no second config in `frontend/`.
   - **If you see `HTTP/1.1 200` but no frames flow before the 5-second timeout** → buffering somewhere (extremely unlikely given the source-code analysis above, but possible if a Node version or http-proxy version issue exists). Capture the response and reopen this diagnosis.
   - **If you see `HTTP/1.1 200` and frames flow** → the proxy is healthy. The bug is browser-side; open DevTools Network tab and look at the `/api/stream/prices` row's status, response headers, and EventSource events.

3. **(If step 1 fixed it) Confirm the prod path still works**

   Already verified by UAT 1-5 (passed). The production path is FastAPI's `StaticFiles` mount in `backend/app/lifespan.py:86-91` (mount of `frontend/out` at `/`); EventSource is same-origin on port 8000 in prod, so the rewrite chain is irrelevant. **Production is not affected.**

## The minimum-change fix

**No code change.** The Plan 08-01 patch is correct as committed.

The fix is operational:

```bash
# Stop the running `next dev` (Ctrl-C in the dev terminal)
cd frontend
rm -rf .next        # clear the dev routes-manifest cache
npm run dev         # restart with the on-disk config
```

If after a clean restart `curl -i -N http://localhost:3000/api/stream/prices` still does not stream, escalate with the curl output captured from step 2 above. At that point we'd be looking at a Next 16.2.4 dev-server-specific regression that would require either pinning to an older Next version or filing an upstream issue — but the evidence so far does not justify that path.

## Production path — not affected

Verified by reading `backend/app/lifespan.py` lines 86-91:

```python
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"
app.mount(
    "/",
    StaticFiles(directory=str(static_dir), html=True, check_dir=False),
    name="frontend",
)
```

In production (single Docker container, `uvicorn` on :8000), the browser loads the static export from `:8000/`, EventSource opens `/api/stream/prices` on the **same origin** (`:8000`), and the FastAPI router matches it directly. There is no Next.js dev server, no rewrite, no proxy — the entire G1/UAT-6 surface does not exist. UAT tests 1-5 passing confirms this.

## What was ruled out (with citations)

1. **Backend not running.** `lsof` + curl direct to :8000 — backend is up and healthy.
2. **Backend SSE broken.** Direct curl returns 200 + chunked `text/event-stream` + 6 frames in 3s.
3. **`skipTrailingSlashRedirect: true` is a no-op.** Source code: `if (!config.skipTrailingSlashRedirect)` guards the entire 308 injection block in `load-custom-routes.js`.
4. **Next dev rewrite buffers SSE.** Source code: `http-proxy.web()` pipes — no buffer accumulation.
5. **Next 16 cross-site dev block.** Source code: only fires for `/_next/*` and `/__nextjs*` paths, which `/api/stream/prices` is not.
6. **EventSource URL mismatches the rewrite pattern.** `/api/stream/prices` matches `/api/stream/:path*` cleanly via path-to-regexp.
7. **Subsequent commit reverted the flag.** Git log shows no edits to `next.config.mjs` after `50ad4c7`.

## Open question for follow-up

The single piece of evidence neither the agent nor static analysis can supply: **what does `curl -i -N http://localhost:3000/api/stream/prices` actually return on the user's machine right now**. That one command discriminates between every remaining hypothesis. Until that is captured, the "stale dev server / stale `.next`" hypothesis is the highest-prior explanation given that the on-disk config is correct and the Phase 7 known root cause (the auto-308) is the only thing standing between this working and not working.
