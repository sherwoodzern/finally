---
phase: 10-e2e-validation
plan: 02
subsystem: testing

tags: [playwright, e2e, sse, watchlist-rest, fresh-start]

requires:
  - phase: 10-e2e-validation
    provides: 10-01 harness foundation (compose, playwright.config.ts, package.json, .gitignore)
  - phase: 04-watchlist
    provides: GET/POST/DELETE /api/watchlist contract with status discriminator
  - phase: 07-ui-spec
    provides: WatchlistRow aria-label="Select {ticker}" + Header data-testid="header-cash"
  - phase: 02-database-bootstrap
    provides: 10-ticker default seed (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX) + cash 10000.0
provides:
  - test/01-fresh-start.spec.ts (PLAN.md §12 row 1)
  - test/02-watchlist-crud.spec.ts (PLAN.md §12 row 2)
affects: [10-03 buy spec, 10-04 sell spec, 10-05 viz/chat/sse specs, 10-06 final harness gate]

tech-stack:
  added: []
  patterns:
    - "Selector hierarchy: data-testid (where Plan 10-00 shipped) > aria-label role-based selectors"
    - "REST-only specs use Playwright `request` fixture (no browser process) for pure-API scenarios"
    - "Streaming proof = absence of '—' em-dash placeholder within 10s"

key-files:
  created:
    - test/01-fresh-start.spec.ts
    - test/02-watchlist-crud.spec.ts
    - .planning/phases/10-e2e-validation/deferred-items.md
  modified: []

key-decisions:
  - "01-fresh-start uses getByTestId('header-cash') because Plan 10-00 has shipped and the testid is present in Header.tsx (verified line 49). Locator-fallback path NOT exercised."
  - "02-watchlist-crud uses PYPL per D-08 — PYPL is not in the default seed and not used by any other §12 spec, so add+remove leaves the watchlist back to seed-only state for any spec that runs after 02 in the same `up`."
  - "01-fresh-start streaming proof uses AAPL row + `not.toContainText('—', { timeout: 10_000 })`. Em-dash is the documented placeholder per WatchlistRow.tsx:59,62."
  - "10-second timeouts on the per-row visibility loop and on the streaming proof, per Pitfall 7 (WebKit first-paint slowness)."

patterns-established:
  - "Spec contract: one `test(...)` block per file, no `describe`, no `beforeEach`, no `test.only`, no `test.skip`, no `waitForTimeout`."
  - "REST contract assertions: assert `response.ok()` AND parse `.status` against the documented literal regex (`/^(added|exists)$/`, `/^(removed|not_present)$/`)."

requirements-completed: [TEST-04]

duration: 8min
completed: 2026-04-27
---

# Phase 10 Plan 02: First Two §12 Spec Files Summary

**Two of seven Phase 10 §12 spec files: 01-fresh-start (default seed + cash + SSE proof) and 02-watchlist-crud (PYPL add+remove via REST). Discovered Plan 10-01 foundation bug: compose service name `app` triggers Chromium/Firefox HSTS upgrade to https — escalated, not fixed in scope.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-27T17:35:00Z (approx)
- **Completed:** 2026-04-27T17:50:00Z (approx)
- **Tasks:** 3 attempted; Tasks 1+2 complete, Task 3 partially green
- **Files modified:** 2 spec files + 1 deferred-items.md + this summary

## Accomplishments

- `test/01-fresh-start.spec.ts` written with the verbatim shape from PLAN's `<interfaces>` block: 10-ticker visibility loop, `header-cash` testid assertion of `$10,000.00`, AAPL streaming-proof via em-dash absence within 10s.
- `test/02-watchlist-crud.spec.ts` written using Playwright's `request` fixture (no browser process) — POST/GET/DELETE `/api/watchlist` against PYPL, asserting `add.ok()` + status regex on each call.
- Both specs committed atomically with conventional-commit `test(10-02):` messages.
- Full `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` executed against the just-built image. Result: **4 of 6 (spec, project) pairs PASS**. The two failing pairs are 01-fresh-start on chromium + firefox, blocked by a foundation-level HSTS preload bug (see Issues Encountered).
- Foundation bug captured with proof (Playwright trace: `Non-Authoritative-Reason: HSTS`, `Location: https://app:8000/`) and documented in `deferred-items.md` for orchestrator follow-up.

## Task Commits

1. **Task 1: Write `test/01-fresh-start.spec.ts`** — `adc8b5c` (test)
2. **Task 2: Write `test/02-watchlist-crud.spec.ts`** — `0a2fc2d` (test)
3. **Task 3: Full 3-browser harness gate** — partial green (4/6 pass); 2 failures are foundation-blocked, not spec-quality. No fix applied; escalated. Committed as part of this SUMMARY.

## Files Created/Modified

- `test/01-fresh-start.spec.ts` — single `test()` block, 38 lines. Reads `/`, asserts 10 watchlist rows, asserts `$10,000.00` cash via `getByTestId('header-cash')`, asserts AAPL row leaves em-dash placeholder within 10s.
- `test/02-watchlist-crud.spec.ts` — single `test()` block, 28 lines. POST `/api/watchlist {ticker:'PYPL'}`, GET `/api/watchlist` (assert PYPL in `items[].ticker`), DELETE `/api/watchlist/PYPL`. All assertions check `response.ok()` AND status-string regex.
- `.planning/phases/10-e2e-validation/deferred-items.md` — new file logging the HSTS-preload foundation bug.

## Decisions Made

- **Header cash selector:** preferred `getByTestId('header-cash')` over the locator fallback. Verified Plan 10-00 already shipped `data-testid="header-cash"` at frontend/src/components/terminal/Header.tsx:49.
- **Streaming proof ticker:** AAPL. Any seed ticker is acceptable per the plan; AAPL is the canonical example in RESEARCH.md and has no cross-spec collision.
- **02-watchlist-crud test ticker:** PYPL per D-08 — confirmed NOT in the default seed and NOT used by any other §12 spec (03-buy uses NVDA, 04-sell uses JPM, 05-viz uses META, 06-chat uses AMZN).
- **Did not adjust per-test timeout:** the 30s `timeout` in playwright.config.ts is more than sufficient. The per-loop 10_000ms timeouts were used for the visibility checks per Pitfall 7 guidance.

## Deviations from Plan

### Deferred (NOT auto-fixed — out of plan scope)

**1. [Rule 4 — Architectural] HSTS preload of compose service hostname `app` blocks chromium + firefox**

- **Found during:** Task 3 (full 3-browser harness gate).
- **Symptom:** 01-fresh-start fails on chromium (`net::ERR_SSL_PROTOCOL_ERROR`) and firefox (`SSL_ERROR_UNKNOWN`) when calling `page.goto('http://app:8000/')`. WebKit passes (1.9s). Playwright `request` fixture passes on all 3 (02-watchlist-crud green across the board).
- **Root cause (proven, not guessed):** Trace `test/test-results/01-fresh-start-...-chromium-retry1/trace.zip` `0-trace.network` shows Chromium issuing a `307 Internal Redirect` with `Non-Authoritative-Reason: HSTS` and `Location: https://app:8000/`. The bare hostname `app` matches the HSTS preload list bundled in Chrome and Firefox (the `.app` TLD entry plus the apex). The browsers force the request to HTTPS; FastAPI doesn't speak TLS; handshake fails.
- **Why not fixed here:** The fix is to rename the compose service from `app` to a non-HSTS hostname (e.g., `appsvc`) and update `baseURL` in `test/playwright.config.ts` + `BASE_URL` in `test/docker-compose.test.yml` accordingly. Plan 10-02's `<verification>` section explicitly forbids modifying anything other than the two spec files. CONTEXT.md decision D-09 locks `baseURL: 'http://app:8000'`. Wave 2 plans 10-03 / 10-04 / 10-05 are running in parallel against the same hostname — renaming mid-flight would invalidate their work.
- **Recommended owner:** Phase 10 orchestrator OR a small follow-on remediation plan executed AFTER Wave 2 lands. Full details + recommended fix in `.planning/phases/10-e2e-validation/deferred-items.md` entry D-10-A.
- **Files NOT modified (intentionally):** `test/playwright.config.ts`, `test/docker-compose.test.yml`.

---

**Total deviations:** 1 deferred to orchestrator (Rule 4 — architectural)
**Impact on plan:** Both spec files (the actual deliverables of Plan 10-02) are correctly written and pass on every browser they reach. The 2 chromium+firefox failures of 01-fresh-start are foundation-blocked, not spec-quality issues. WebKit alone validates the cross-browser browser-driven path; chromium and firefox both validate the REST-only path (02). The plan's content goal — landing the two spec files with the documented assertion shapes — is achieved.

## Issues Encountered

- **HSTS upgrade on `app` hostname:** documented above; deferred. The 4 green (spec, project) pairs prove every spec assertion that's reachable; the 2 red pairs prove a clean foundation bug in 10-01.
- **Orphan `test-playwright-run-...` container appeared after the Playwright service exited.** This is a stale container left over from a previous abandoned `docker compose run` (visible only in stdout tail; did not affect the test result tally). Not addressed — pre-existing environmental noise.

## Threat Flags

None — both specs are read-only or REST-only against documented Phase 4 endpoints. No new surface introduced.

## Self-Check

- [x] `test/01-fresh-start.spec.ts` exists at the absolute path under the worktree.
- [x] `test/02-watchlist-crud.spec.ts` exists at the absolute path under the worktree.
- [x] Commit `adc8b5c` (Task 1) present in git log.
- [x] Commit `0a2fc2d` (Task 2) present in git log.
- [x] Spec contents match the plan's `<interfaces>` shape (verified via grep gates).
- [x] No files modified outside `test/` and `.planning/phases/10-e2e-validation/` (the deferred-items + summary).
- [ ] Full 3-browser harness green: **PARTIAL — 4 of 6 pairs pass.** The 2 failures are foundation-bug blocked (HSTS), not spec-quality issues. Documented and escalated.

## Self-Check: PARTIAL

The two new spec files exist and are correctly committed. The full 3-browser harness gate has 2 known failures attributable to a foundation bug in Plan 10-01's compose service naming (HSTS preload of `app`). No silent failures, no flakes — the failures are deterministic, reproduced on retry, and traced to a specific root cause with proof artefacts on disk. Orchestrator decision required to remediate before Phase 10 can declare "all green on chromium+firefox+webkit".

## Next Phase Readiness

- Plan 10-03 (buy spec), 10-04 (sell spec), and 10-05 (viz / chat / sse specs) can proceed in parallel — their REST-only assertions will pass on all 3 browsers immediately, and their browser-driven assertions will inherit the same 01-style HSTS issue.
- After all Wave 2 plans land, the orchestrator (or a small follow-on plan) should rename the compose service away from `app` (recommended: `appsvc`) and update the two `baseURL` references. Single commit, no architectural change.
- Plan 10-06 (final harness gate) cannot be declared green until the HSTS issue is fixed.

---
*Phase: 10-e2e-validation*
*Plan: 02*
*Completed: 2026-04-27*
