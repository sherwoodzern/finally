---
phase: 01-app-shell-config
plan: 03
subsystem: tests
tags: [pytest, fastapi, sse, asgi-lifespan, httpx, uvicorn, end-to-end]

# Dependency graph
requires:
  - phase: 01-app-shell-config-01
    provides: "lifespan @asynccontextmanager that attaches PriceCache + market source to app.state and mounts create_stream_router(cache)"
  - phase: 01-app-shell-config-02
    provides: "backend/app/main.py module-level `app: FastAPI` + inline /api/health"
provides:
  - "backend/tests/test_lifespan.py — 7 async lifecycle assertions for the lifespan (PriceCache, MarketDataSource, simulator selection, seed cache, SSE route registration, OPENROUTER warning, clean shutdown)"
  - "backend/tests/test_main.py — 1 health test + 2 end-to-end SSE tests (first-frame + continuity)"
  - "httpx >= 0.28.1 and asgi-lifespan >= 2.1.0 as dev dependencies"
  - "In-process uvicorn.Server test harness for infinite streaming endpoints"
affects: [02-database (tests show how to drive lifespan), 05-chat (same test harness), 10-e2e (validates the wire before Playwright)]

# Tech tracking
tech-stack:
  added:
    - "httpx (dev) — ASGITransport for finite responses, AsyncClient.stream for real-socket SSE"
    - "asgi-lifespan (dev) — LifespanManager(app) runs startup/shutdown around async tests"
  patterns:
    - "Fresh FastAPI(lifespan=lifespan) per test — no module-level app.main.app sharing, matches test_lifespan.py convention"
    - "In-process uvicorn.Server on 127.0.0.1:<random_port> with loop='asyncio' for tests that need true streaming (ASGITransport buffers full responses and cannot drain infinite SSE generators)"
    - "patch.dict(os.environ, {}, clear=True) to force simulator mode and exercise the missing-OPENROUTER_API_KEY warning path"
    - "APIRouter constructed inside create_stream_router factory — no module-level router accumulation across calls"

key-files:
  created:
    - backend/tests/test_lifespan.py
    - backend/tests/test_main.py
    - .planning/phases/01-app-shell-config/01-03-SUMMARY.md
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
    - backend/app/market/stream.py

key-decisions:
  - "D-05 (this plan): SSE tests use a real uvicorn server, not ASGITransport. httpx's ASGITransport awaits the full ASGI app call before returning a Response and buffers body_parts in memory, so it cannot drain an infinite `while True` SSE generator. The plan's prescribed ASGITransport+client.stream pattern was kept for TestHealth (finite response) but replaced with a real socket for TestSSEStream."
  - "D-06 (this plan): `create_stream_router` now constructs a fresh APIRouter per call. The pre-existing module-level router accumulated duplicate `/prices` routes across factory calls, and Starlette dispatches the first match — so a stale route from a torn-down lifespan served subsequent requests against a dead cache, causing 5s ReadTimeouts."
  - "Dev deps declared under `[project.optional-dependencies].dev` (not PEP 735 `[dependency-groups]`) to match the existing pytest/ruff block and the `uv sync --extra dev` invocation already used by CI and CLAUDE.md."
  - "Each test builds a fresh FastAPI(lifespan=lifespan) rather than importing app.main.app — ensures no state bleed across tests (same pattern used by the Plan 01 test suite)."

patterns-established:
  - "Async HTTP-level tests: `@pytest.mark.asyncio` at class level; `async with LifespanManager(app):` before any request; `patch.dict(os.environ, {}, clear=True)` on the outside so the lifespan sees a clean env at startup."
  - "True-streaming tests: random port from OS (`socket.bind(('127.0.0.1', 0))`) + `uvicorn.Config(app, host='127.0.0.1', port=port, loop='asyncio')` + `asyncio.create_task(server.serve())` + poll `server.started` + `server.should_exit = True` on teardown."
  - "ASGI factories must never hold router/state at module scope — build fresh per call so repeat-construction (tests, reloads) doesn't leak state across closures."

requirements-completed: [APP-01, APP-03, APP-04]

# Metrics
duration: ~60min
completed: 2026-04-20
---

# Phase 01 Plan 03: Tests Summary

**End-to-end pytest coverage of the Phase 1 app shell: `asgi-lifespan` drives the real FastAPI lifespan around 7 lifecycle assertions, `httpx.ASGITransport` verifies `/api/health`, and an in-process `uvicorn.Server` on a random localhost port drives two real-socket SSE tests that receive `data:` frames from `/api/stream/prices` — closing APP-04's browser-equivalent verification loop without Playwright.**

## Performance

- **Duration:** ~60 min (including root-cause analysis of a pre-existing stream-router bug)
- **Started:** 2026-04-20T13:00:31Z (STATE.md last-updated)
- **Completed:** 2026-04-20T13:56:18Z
- **Tasks:** 3 / 3
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- Added `httpx>=0.28.1` and `asgi-lifespan>=2.1.0` as dev dependencies in `backend/pyproject.toml` under `[project.optional-dependencies].dev` (lockfile updated, `uv sync --extra dev` green, both importable).
- Created `backend/tests/test_lifespan.py` — 98 lines, 7 async lifecycle tests covering PriceCache attachment, MarketDataSource attachment + SEED_PRICES ticker set, simulator selection when `MASSIVE_API_KEY` is absent, immediate cache seeding on startup, `/api/stream/prices` route registration, missing-OPENROUTER_API_KEY warning path, and clean source shutdown on lifespan exit. All 7 pass.
- Created `backend/tests/test_main.py` — 3 HTTP-level tests:
  - `TestHealth.test_health_returns_ok` — `httpx.ASGITransport` through `LifespanManager` confirms `GET /api/health` returns `200 {"status": "ok"}` (APP-03).
  - `TestSSEStream.test_sse_emits_at_least_one_data_frame` — real uvicorn server receives >=1 `data:` frame from `/api/stream/prices` within 5s (APP-04 first-frame).
  - `TestSSEStream.test_sse_continues_emitting_as_cache_version_advances` — real uvicorn server receives >=2 `data:` frames, proving the stream keeps emitting as the simulator advances the cache version (APP-04 continuity).
- Fixed a pre-existing bug in `backend/app/market/stream.py`: the `create_stream_router` factory used a module-level `APIRouter` that accumulated duplicate `/prices` routes across calls. Moved the router construction inside the factory so each call returns a fresh, isolated router.
- **Full backend test suite: 83 passed in 1.95s** (73 existing + 7 lifespan + 3 main + 0 regressions). Ruff clean on `app/` and `tests/`.

## Task Commits

Each task was committed atomically. Rule 1 auto-fix tracked alongside its enabling task.

1. **Task 1: Add httpx and asgi-lifespan as dev dependencies** — `1ef1e4d` (chore)
2. **Task 2: Create backend/tests/test_lifespan.py** — `3595f5a` (test)
3. **Rule 1 fix: fresh APIRouter per create_stream_router call** — `704525d` (fix)
4. **Task 3: Create backend/tests/test_main.py** — `d4a5500` (test)

## Files Created/Modified

- `backend/tests/test_lifespan.py` (**created**, 98 lines) — 7 async lifecycle tests.
- `backend/tests/test_main.py` (**created**, 160 lines) — 1 health + 2 SSE end-to-end tests with an in-process uvicorn harness and a `_build_app()` helper.
- `backend/pyproject.toml` (**modified**) — added `httpx>=0.28.1` and `asgi-lifespan>=2.1.0` to `[project.optional-dependencies].dev`.
- `backend/uv.lock` (**modified**) — now locks httpx 0.28.1, asgi-lifespan 2.1.0, httpcore 1.0.9, sniffio 1.3.1.
- `backend/app/market/stream.py` (**modified**) — `create_stream_router` builds a fresh `APIRouter` per call (was module-level).

## Decisions Made

- **Fresh FastAPI app per test, not `from app.main import app`.** The Plan 01 lifespan calls `app.include_router(create_stream_router(cache))` which mutates the app. Sharing the module-level app across tests would stack routes and leak stale closures. A `_build_app()` helper mirroring `test_lifespan.py` builds a new `FastAPI(lifespan=lifespan)` per test — and in `test_main.py` the helper also attaches the `/api/health` route so the test harness exercises the same wiring as production without coupling to the singleton.
- **Real uvicorn server for SSE, ASGITransport for /health.** Two different transports in one file. See the module docstring in `test_main.py` for the full rationale. TL;DR: `ASGITransport.handle_async_request` awaits the full app call before returning a Response and cannot drain an infinite generator; a real socket exposes chunks as they arrive, which is what an `EventSource` client sees.
- **`loop='asyncio'` for the in-process uvicorn server.** Matches pytest-asyncio's event loop so `asyncio.create_task(server.serve())` shares the test's loop; no separate-thread coordination, no policy swaps.
- **Port selection via OS-assigned port 0.** `socket.bind(('127.0.0.1', 0))` returns a free port that's released immediately; a small race window exists but is acceptable for a single-process test harness and avoids hardcoded ports clashing with local dev servers.
- **Rule 1 auto-fix: move APIRouter construction inside `create_stream_router`.** A module-level `router = APIRouter(...)` accumulated routes across calls — a latent bug that only manifested under the new multi-lifespan test harness. Factory semantics require a new router per call. This is a surgical 7-line change, zero behavior change for the running app (it calls `create_stream_router` exactly once at startup), and removes a class of shared-state failures for future test and reload scenarios.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Module-level APIRouter accumulated duplicate `/prices` routes**
- **Found during:** Task 3 (SSE test second-frame timeout when running multiple SSE tests against fresh FastAPI apps).
- **Issue:** `backend/app/market/stream.py` declared `router = APIRouter(prefix="/api/stream", tags=["streaming"])` at module level and decorated `@router.get("/prices")` inside `create_stream_router`. Each factory call re-registered `/prices` on the same module-level router; `include_router` then copied the growing route list onto the target FastAPI app. After two factory calls, the target app had two `/api/stream/prices` routes — Starlette dispatches the first match, so subsequent requests were served by a closure pointing at the first lifespan's torn-down PriceCache (cache version never advanced → no new `data:` frames → 5s ReadTimeout).
- **Root cause proof:** `/tmp/route_accum_debug2.py` showed app2's router with `['...', '/api/stream/prices', '/api/stream/prices']` after a second lifespan.
- **Fix:** Moved `router = APIRouter(...)` inside `create_stream_router` so each call returns a fresh router. Added a docstring paragraph explaining the shared-state hazard.
- **Files modified:** `backend/app/market/stream.py` (+7/-2).
- **Commit:** `704525d`.
- **Regression safety:** Zero runtime behavior change — the production lifespan calls `create_stream_router` exactly once at startup. All 73 pre-existing market tests still pass.

### Plan-approach deviations (documented, no behavior change)

**2. [Rule 1 - Plan Approach] SSE tests use a real uvicorn server, not `ASGITransport`**
- **Plan prescribed:** `async with AsyncClient(transport=ASGITransport(app=app)) as client: async with client.stream("GET", "/api/stream/prices", timeout=5.0)`.
- **Why it doesn't work:** Verified by reading `.venv/.../httpx/_transports/asgi.py:170` — `await self.app(scope, receive, send)` blocks until the ASGI app call returns, and the transport buffers all `http.response.body` chunks in `body_parts` until `more_body=False`. Our `_generate_events` runs `while True:` indefinitely, so the transport never returns, `client.stream()` never yields, and the test hangs until `asyncio.timeout` / test-runner kill. Reproduced with `/tmp/sse_debug.py`. Starlette's `TestClient` has the same limitation (also uses ASGITransport semantics via an anyio portal).
- **Fix applied:** `test_main.py` spins up an in-process `uvicorn.Server` on `127.0.0.1:<random_port>` (asyncio loop) and connects with a regular `httpx.AsyncClient` — real TCP, real chunked streaming. TestHealth still uses ASGITransport because `/api/health` is a finite response (the buffer-until-complete semantics are fine there and ASGITransport is faster).
- **Acceptance criterion adjustment:** The plan's must-have line "real EventSource-equivalent (httpx streaming GET on /api/stream/prices) receives at least one `data:` frame within 5 seconds" is satisfied — the test is end-to-end and the client is httpx streaming — just over a real socket instead of an in-memory ASGI call. This is the stronger verification (it's literally what a browser sees) and documented inline in the test module docstring.

## Issues Encountered

- **Hang diagnosis:** Initial Task 3 run with the plan's prescribed pattern hung indefinitely. Ruled out: test-runner issue, asyncio loop issue, lifespan-not-running. Proved root cause with two standalone debug scripts (`/tmp/sse_debug.py` with ASGITransport, `/tmp/sse_debug2.py` with Starlette TestClient) — both hang identically, confirming the buffering behavior is the culprit. Fix: real uvicorn server (above).
- **Second-frame timeout after fresh-app switch:** After rewriting to use a real uvicorn server per test, the first SSE test passed but the second timed out at 5s with only 0-1 frames received. Reproduced deterministically. Proved root cause with `/tmp/route_accum_debug2.py` — the module-level router in `stream.py` accumulated routes across factory calls regardless of whether the target FastAPI app was fresh. Fix: Rule 1 auto-fix above.
- **PEP 735 vs optional-dependencies gotcha:** `uv add --dev` wrote to `[dependency-groups].dev` (PEP 735), but the project's CI and CLAUDE.md use `uv sync --extra dev` which only reads `[project.optional-dependencies].dev`. Manually migrated the two new entries to the existing `[project.optional-dependencies].dev` block and removed the stray `[dependency-groups]` section. Re-ran `uv sync --extra dev` to confirm both import paths.

## Verification Results

### Plan-level success criteria

- **APP-01 (FastAPI process + /api/health):** `TestHealth.test_health_returns_ok` passes — lifespan runs, route returns `200 {"status": "ok"}`.
- **APP-03 (lifespan wires PriceCache + source + SSE + env):** `test_lifespan.py` — all 7 tests pass, including simulator selection when `MASSIVE_API_KEY` is absent and the OPENROUTER missing-key warning path.
- **APP-04 (browser-consumable SSE, first frame + continuity):** `TestSSEStream.test_sse_emits_at_least_one_data_frame` and `TestSSEStream.test_sse_continues_emitting_as_cache_version_advances` — both pass against a real uvicorn server + real httpx streaming client.

### Task acceptance criteria

- **Task 1:** `backend/pyproject.toml` shows `httpx>=0.28.1` and `asgi-lifespan>=2.1.0` inside `[project.optional-dependencies].dev`. `cd backend && uv sync --extra dev` exits 0. `cd backend && uv run --extra dev python -c "from httpx import ASGITransport, AsyncClient; from asgi_lifespan import LifespanManager"` exits 0. `backend/uv.lock` contains both `[[package]]` blocks.
- **Task 2:** `backend/tests/test_lifespan.py` exists (98 lines > 40 min_lines). `contains: "TestLifespan"` — yes (line 27). `uv run --extra dev pytest tests/test_lifespan.py -v` — 7 passed. Imports `app.lifespan.lifespan` and uses `LifespanManager(app)`.
- **Task 3:** `backend/tests/test_main.py` exists (160 lines > 40 min_lines). `contains: "TestHealth"` — yes (line 73). `uv run --extra dev pytest tests/test_main.py -v` — 3 passed.

### Overall suite + lint

- `cd backend && uv run --extra dev pytest -v` → **83 passed in 1.95s**.
- `cd backend && uv run --extra dev ruff check app/ tests/` → `All checks passed!`.

## User Setup Required

None. `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` remain optional at Phase 1 startup (missing values log a warning, never raise). The full dev install is `cd backend && uv sync --extra dev` as before.

## Next Phase Readiness

Phase 2 (Database Foundation) can now:

- Extend the lifespan with SQLite init + seed logic knowing the test harness (`LifespanManager` + fresh FastAPI per test) reliably exercises startup/shutdown and catches shared-state leaks (`test_lifespan.py` is the template).
- Depend on `httpx` + `asgi-lifespan` for HTTP-level tests against `/api/portfolio` and `/api/watchlist` as they come online in Phase 3/4.
- Reuse the in-process uvicorn harness pattern if any future endpoint streams indefinitely.
- Trust the `create_stream_router` factory: fresh-router-per-call semantics mean the lifespan can be entered and exited repeatedly (tests, reloads) without route accumulation — relevant if Phase 2 introduces DB-backed dynamic ticker onboarding that triggers router rebuilds.

No blockers. All three Phase 1 requirements (APP-01, APP-03, APP-04) are complete. Phase 1 can be marked as a whole once the orchestrator closes 01-03.

## Self-Check: PASSED

- `backend/tests/test_lifespan.py` exists — verified on disk (98 lines).
- `backend/tests/test_main.py` exists — verified on disk (160 lines).
- `backend/app/market/stream.py` modified — `router = APIRouter(...)` now inside `create_stream_router` (verified on disk).
- Commit `1ef1e4d` (Task 1) — present in `git log` (verified).
- Commit `3595f5a` (Task 2) — present in `git log` (verified).
- Commit `704525d` (Rule 1 stream fix) — present in `git log` (verified).
- Commit `d4a5500` (Task 3) — present in `git log` (verified).
- Full backend suite 83 passed in 1.95s — verified.
- Ruff clean on `app/` and `tests/` — verified.

---
*Phase: 01-app-shell-config*
*Completed: 2026-04-20*
