# Phase 10 — Deferred / Out-of-scope items

Discovered during execution but not fixed because the fix would touch files
outside the executing plan's `files_modified` list. The orchestrator (or a
follow-on plan) should address these.

## D-10-A: HSTS preload upgrade blocks Chromium + Firefox against compose service `app` — RESOLVED (2026-04-27)

- **Status: RESOLVED.** Compose service renamed `app` → `appsvc`; `BASE_URL` and `playwright.config.ts` `baseURL` updated to `http://appsvc:8000`. CONTEXT.md D-09 carries an override note pointing to this entry. Three independent Wave 2 executors (10-02, 10-03, 10-04) had previously reproduced the failure with trace evidence; the rename eliminates the HSTS preload match.
- **Discovered during:** Plan 10-02, Task 3 (full 3-browser harness gate).
- **Symptom:** `01-fresh-start.spec.ts` fails on chromium with
  `net::ERR_SSL_PROTOCOL_ERROR at http://app:8000/` and on firefox with
  `SSL_ERROR_UNKNOWN`. WebKit passes. The Playwright `request` fixture (used by
  `02-watchlist-crud.spec.ts`) passes on all 3 projects because it doesn't go
  through the browser HSTS code path.
- **Root cause (proven via trace):** Chromium issues a `307 Internal Redirect`
  with `Non-Authoritative-Reason: HSTS` and `Location: https://app:8000/` for
  the bare hostname `app`. The compose service name `app` matches the `.app`
  TLD HSTS preload entry baked into Chrome and Firefox. The browsers force the
  request to HTTPS, which the FastAPI server doesn't speak, so TLS handshake
  fails. Trace evidence:
  `test/test-results/01-fresh-start-...-chromium-retry1/trace.zip` ->
  `0-trace.network` shows the upgrade redirect explicitly.
- **Scope of fix:** Rename the compose service from `app` to a non-`.app`
  hostname (e.g., `appsvc`, `finally-app`, `backend`), and update
  `playwright.config.ts` `baseURL` + `docker-compose.test.yml`
  `BASE_URL` env + `depends_on` accordingly. Two files, four edits total.
  CONTEXT.md D-09 (`baseURL: 'http://app:8000'`) needs updating to reflect the
  new hostname. The change does not alter any architecture — same compose, same
  Dockerfile, same Playwright config shape; only the DNS label changes.
- **Why not fixed in 10-02:** Plan 10-02's `verification` section says
  "No files modified outside `test/01-fresh-start.spec.ts` and
  `test/02-watchlist-crud.spec.ts`". Modifying compose / config violates that
  hard scope boundary, and Wave 2 plans 10-03 / 10-04 / 10-05 are running in
  parallel against the same `app` service name; renaming mid-flight would
  invalidate their work.
- **Recommended owner:** Phase 10 orchestrator OR a small follow-on
  remediation plan (e.g., 10-01.1) executed AFTER all Wave 2 plans land.
- **Impact today:** 4 of 6 (spec, project) pairs in Plan 10-02 pass green.
  WebKit covers the cross-browser story for 01-fresh-start. The two failing
  pairs (chromium + firefox 01-fresh-start) are foundation-blocked, not
  spec-quality issues.
