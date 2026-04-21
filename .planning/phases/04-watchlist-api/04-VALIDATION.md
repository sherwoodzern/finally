---
phase: 4
slug: watchlist-api
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-21
revised: 2026-04-21
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24 (asyncio_mode=auto) |
| **Config file** | `backend/pyproject.toml` (tool.pytest.ini_options) |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/watchlist -x -q` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -q` |
| **Estimated runtime** | ~30 seconds (quick) / ~90 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Revised for the 2-plan layout (Plan 04-01 = models + service; Plan 04-02 = routes
+ lifespan mount + integration tests, atomic per the Phase 3 `03-03-PLAN.md`
precedent). Plan 04-03 was dropped during revision iteration 1; route coverage
now lives entirely under Plan 04-02.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 4-01-01 | 04-01 | 1 | WATCH-01/02/03 | T-04-06, T-04-07 | normalize_ticker regex + extra="forbid" | unit | `pytest tests/watchlist/test_models.py -q` | ✅ | ✅ green |
| 4-01-02 | 04-01 | 1 | WATCH-01 | T-04-12 | parameterized SELECT | unit | `pytest tests/watchlist/test_service_get.py -q` | ✅ | ✅ green |
| 4-01-03a | 04-01 | 1 | WATCH-02 | T-04-12 | parameterized INSERT ... ON CONFLICT | unit | `pytest tests/watchlist/test_service_add.py -q` | ✅ | ✅ green |
| 4-01-03b | 04-01 | 1 | WATCH-03 | T-04-12 | parameterized DELETE + rowcount | unit | `pytest tests/watchlist/test_service_remove.py -q` | ✅ | ✅ green |
| 4-02-01 | 04-02 | 2 | WATCH-01/02/03 | T-04-06, T-04-07, T-04-09 | 422 on malformed ticker; log-and-continue on post-commit source failure | unit | `pytest tests/watchlist/ -q` (indirectly via integration) | ✅ | ✅ green |
| 4-02-02 | 04-02 | 2 | WATCH-01/02/03 | T-04-13, T-04-14 | lifespan registers `/api/watchlist` + `/api/watchlist/{ticker}` before `yield` | integration | `pytest tests/test_lifespan.py::*::test_includes_watchlist_router_during_startup -q` | ✅ | ✅ green |
| 4-02-03a | 04-02 | 2 | WATCH-01 | T-04-09 | GET returns 200 with 10-ticker seed + cold-cache None-price contract | integration | `pytest tests/watchlist/test_routes_get.py -q` | ✅ | ✅ green |
| 4-02-03b | 04-02 | 2 | WATCH-02, SC#4 | T-04-06, T-04-10, T-04-12 | POST dup → `status="exists"` (NOT 409); source-fail → 200 + WARNING | integration | `pytest tests/watchlist/test_routes_post.py -q` | ✅ | ✅ green |
| 4-02-03c | 04-02 | 2 | WATCH-03, SC#4 | T-04-07, T-04-10 | DELETE missing → `status="not_present"` (NOT 404); 422 on malformed path | integration | `pytest tests/watchlist/test_routes_delete.py -q` | ✅ | ✅ green |
| 4-02-04 | 04-02 | 2 | all | — | full backend suite regression | integration | `pytest -q && ruff check app/ tests/` | ✅ | ✅ green |

*Status: ✅ green · ✅ green · ❌ red · ⚠️ flaky*

Every task row has a concrete `<automated>` command backed by an existing or
planned test file. No `❌ W0` entries remain — Wave 0 test scaffolding is
absorbed into Plan 04-01 Task 1 (models test file) and Plan 04-02 Task 3
(three integration test files written in the same plan that wires the router).

---

## Wave 0 Requirements

All Wave 0 work for Phase 4 is absorbed into the plans themselves (Plan 04-01
creates `tests/watchlist/__init__.py` + `test_models.py` alongside the models;
Plan 04-02 creates three integration test files alongside the router).

- [x] `backend/tests/watchlist/__init__.py` — package marker (Plan 04-01 Task 1)
- [x] Fixture conventions established: module-scoped `app_with_lifespan` using
      `@pytest_asyncio.fixture(scope="module")` with `LifespanManager` (Plan 04-02 Task 3)
- [x] Reuse `backend/tests/conftest.py` `db_path` fixture where appropriate
- [x] No new dependencies required — `pytest-asyncio` and `asgi-lifespan` already installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE stream reflects watchlist add/remove end-to-end | Success #2, #3 | SSE cadence is 500ms and crosses async boundaries; covered by Phase 10 Playwright | Run `uv run uvicorn app.main:app`, `curl -N http://localhost:8000/api/stream/prices`, POST+DELETE tickers |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none remain)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (module-scoped lifespan fixture keeps per-file
      SimulatorDataSource starts to exactly 1, not 6+)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (revised for 2-plan atomic layout on 2026-04-21)

---

## Phase Split Provenance

Original draft layout: 3 plans (models, service, routes-and-lifespan). During
revision iteration 1 the checker flagged the routes plan as unsafe because it
mounted the router via a post-startup `_mount(app)` shim (undefined FastAPI
behavior after `LifespanManager.__aenter__()` returns). Remediation merged the
service + routes/lifespan work back into a single atomic plan (04-02), mirroring
the Phase 3 `03-03-PLAN.md` precedent that shipped portfolio routes + lifespan
mount + integration tests in one plan. Final layout: 2 plans, 0 shims,
route mounted natively in the lifespan before `yield`.

> Phase split: original 3-plan layout merged to 2 plans on revision iteration 1
> per checker (Plan 02+03 atomic per 03-03-PLAN.md precedent).
