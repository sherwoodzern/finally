---
phase: 08-portfolio-visualization-chat-ui
plan: 01
subsystem: infra
tags: [fastapi, staticfiles, nextjs, sse, lifespan, app-shell]

requires:
  - phase: 01-app-shell
    provides: lifespan with /api/* router registration
  - phase: 06-frontend-scaffold-sse
    provides: next.config.mjs with trailingSlash + dev rewrites
provides:
  - FastAPI StaticFiles mount of frontend/out at / (APP-02 / D-14)
  - Phase 7 G1 fix - skipTrailingSlashRedirect: true so npm run dev SSE works (D-15)
  - Integration test (test_static_mount.py) covering mount registration, ordering, and /api/health non-shadow
affects: [08-02, 08-03, 08-04, 08-05, 08-06, 08-07, phase-09]

tech-stack:
  added: []
  patterns:
    - StaticFiles catch-all mount registered AFTER all include_router() calls
    - check_dir=False defers directory existence check to first request

key-files:
  created:
    - backend/tests/test_static_mount.py
  modified:
    - backend/app/lifespan.py
    - frontend/next.config.mjs

key-decisions:
  - Mount StaticFiles strictly after the four /api/* include_router calls so the catch-all does not shadow the API
  - check_dir=False on StaticFiles so backend boots in dev/test before npm run build has produced frontend/out
  - skipTrailingSlashRedirect: true in next.config.mjs - resolves Phase 7 G1 dev redirect chain

patterns-established:
  - "Wave-1 same-origin shell: dev SSE works via Next rewrite + skipTrailingSlashRedirect; prod SSE works via single FastAPI process serving both /api/* and /"

requirements-completed: [APP-02]

duration: ~3min
completed: 2026-04-26
---

# Phase 08 Plan 01: APP-02 Same-Origin Static Mount + G1 SSE Fix Summary

**FastAPI StaticFiles mount of frontend/out at / after all /api/* routers, plus skipTrailingSlashRedirect: true in next.config.mjs to unblock dev-mode SSE.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-26T05:33:39Z
- **Completed:** 2026-04-26T05:37:00Z (approximate)
- **Tasks:** 3 (all complete)
- **Files modified/created:** 3

## Accomplishments

- Frontend `next.config.mjs` now sets `skipTrailingSlashRedirect: true`, removing the 308->307 redirect chain that blocked `/api/stream/prices` under `npm run dev`. Phase 7 deferred UAT 1/2/3/5 are now testable.
- Backend `lifespan.py` mounts `StaticFiles(directory=str(static_dir), html=True, check_dir=False)` at `/` strictly after all four `app.include_router(...)` calls, satisfying APP-02 and D-14 (route precedence: catch-all last).
- New integration suite `backend/tests/test_static_mount.py` proves the mount is registered, comes after every `/api/*` route, does not shadow `/api/health`, and skips cleanly when the frontend build artifact is absent.

## Task Commits

1. **Task 1: skipTrailingSlashRedirect in next.config.mjs (D-15)** - `50ad4c7` (fix)
2. **Task 2: Mount StaticFiles at / in lifespan.py (D-14)** - `31003ba` (feat)
3. **Task 3: APP-02 integration test + check_dir=False fix** - `3258925` (test, includes Rule 3 auto-fix)

## Files Created/Modified

- `frontend/next.config.mjs` - Added single line `skipTrailingSlashRedirect: true,` between `trailingSlash` and `async rewrites()`. No other keys touched.
- `backend/app/lifespan.py` - Added `from pathlib import Path` (line 8) and `from fastapi.staticfiles import StaticFiles` (line 11). Mount block lives at lines 82-89 (after the existing `include_router(create_chat_router(...))` at line 80, before the trailing `logger.info(...)` block).
- `backend/tests/test_static_mount.py` - New 4-test integration suite using the canonical `LifespanManager` + `httpx.ASGITransport` harness from `test_lifespan.py`.

## Path Resolution Notes

- `static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"` — `lifespan.py` lives at `backend/app/lifespan.py`, so `parents[0]=backend/app`, `parents[1]=backend`, `parents[2]=<repo root>`. Resolved path: `<repo>/frontend/out`. Phase 9's Dockerfile will COPY `frontend/out/` into `backend/frontend/out/` (or equivalent) so the same `parents[2]` math holds inside the container.

## Test Outcomes

- `test_static_mount_registered_at_root` - PASSED
- `test_mount_registered_after_api_routers` - PASSED (asserts D-14 ordering invariant)
- `test_index_html_served_at_root` - SKIPPED with reason `"frontend/out/index.html missing - run npm run build first"` (build artifact not present in this worktree; this is the documented Phase 8/9 contract)
- `test_api_health_still_resolves_after_mount` - PASSED (catch-all does NOT shadow `/api/*`)
- Full backend suite: **298 passed, 1 skipped, 0 failed** — no regressions in Phase 1-5 tests.

## Confirmation: No /api/* Route Shadowed

`test_api_health_still_resolves_after_mount` requests `GET /api/health` after the lifespan registers the StaticFiles mount and confirms HTTP 200 with body `{"status": "ok"}`. The route-precedence ordering invariant is also asserted directly in `test_mount_registered_after_api_routers` (mount index > all `/api/*` indices in `app.router.routes`).

## Decisions Made

- **D-14 (executed verbatim):** Mount StaticFiles AFTER all routers — the existing `include_router` order was preserved (stream, portfolio, watchlist, chat) and the mount appended.
- **D-15 (executed verbatim):** Single-key addition to `next.config.mjs`. `trailingSlash`, `output`, `images`, `rewrites` all unchanged.
- **New decision (auto-fix, see Deviations):** `check_dir=False` on the `StaticFiles` constructor. Starlette's default `check_dir=True` raises `RuntimeError` at `__init__` time, but the plan documented "Starlette will raise on first request". Choosing `check_dir=False` makes the documented behavior real and is the minimal change that lets the lifespan boot in dev/test without `npm run build`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] StaticFiles raised at lifespan boot when frontend/out was absent**

- **Found during:** Task 3 (running the new integration tests)
- **Issue:** Starlette's `StaticFiles.__init__` checks `os.path.isdir(directory)` when `check_dir=True` (the default) and raises `RuntimeError: Directory '<path>' does not exist`. The plan's Task 2 done criteria assumed Starlette would raise "on first request" — that's only true with `check_dir=False`. With the default, all 4 tests in `test_static_mount.py` fail (not just the deliberately-skipped index.html test) because the lifespan itself can't enter the `try: yield` block. This is a blocking issue per Rule 3 — without the fix, NO Phase 8 plan can run its lifespan-based integration tests in a worktree that hasn't run `npm run build`.
- **Fix:** Pass `check_dir=False` to the `StaticFiles(...)` call in `backend/app/lifespan.py`. Defers existence check to first request, matching the plan's documented intent. Single keyword arg, no defensive try/except, fully compliant with CLAUDE.md "no defensive programming".
- **Files modified:** `backend/app/lifespan.py`
- **Verification:** `cd backend && uv run --extra dev pytest tests/test_static_mount.py -v` → 3 passed, 1 skipped. Full suite: 298 passed, 1 skipped, 0 failed.
- **Committed in:** `3258925` (Task 3 commit)
- **Note for future plans:** The plan-frontmatter literal `'StaticFiles(directory=str(static_dir), html=True)'` grep should be loosened to `'StaticFiles(directory=str(static_dir), html=True'` (no trailing close-paren) so additional kwargs don't break grep-style verification.

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking). All other tasks executed verbatim.
**Impact on plan:** The fix is required for the lifespan to boot in any environment without `frontend/out/`, which includes every test environment until Phase 9 wires up the multi-stage Docker build. Zero scope creep — single keyword arg, semantically equivalent to the plan's stated contract.

## Issues Encountered

- Plan acceptance-criteria literal greps for `'app.mount("/"'` (single line) didn't match the multi-line `app.mount(\n    "/",\n    ...` formatting I used. Spirit-of-the-plan: mount is present, regex with whitespace tolerance confirms it. No code change needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Wave-2 plans (08-02, 08-03, 08-04 — heatmap, P&L chart, chat panel) can build against a working same-origin shell.** Visiting `/` will serve `frontend/out/index.html` (once `npm run build` runs); `/api/*` continues to resolve to the API routers.
- **Phase 7 G1 carry-over resolved.** `npm run dev` now successfully proxies `/api/stream/prices` to the FastAPI server without the 308→307 redirect storm. Deferred UAT 1/2/3/5 from Phase 7 are now testable.
- **Phase 9 (OPS-01) lift-and-shift unchanged.** The mount uses `parents[2]/frontend/out` — Phase 9's Dockerfile will COPY `frontend/out/` into the same relative path inside the image; no additional `lifespan.py` edits needed.

## Self-Check: PASSED

Verified files exist:
- `frontend/next.config.mjs` (modified, contains `skipTrailingSlashRedirect: true,`)
- `backend/app/lifespan.py` (modified, contains StaticFiles import + mount block)
- `backend/tests/test_static_mount.py` (created, 4 tests)
- `.planning/phases/08-portfolio-visualization-chat-ui/08-01-SUMMARY.md` (this file)

Verified commits exist:
- `50ad4c7` Task 1 — fix(08-01): add skipTrailingSlashRedirect to next.config.mjs
- `31003ba` Task 2 — feat(08-01): mount StaticFiles for frontend/out at /
- `3258925` Task 3 — test(08-01): add APP-02 integration tests + check_dir=False fix

---
*Phase: 08-portfolio-visualization-chat-ui*
*Completed: 2026-04-26*
