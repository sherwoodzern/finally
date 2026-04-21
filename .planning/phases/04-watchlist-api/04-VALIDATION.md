---
phase: 4
slug: watchlist-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
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

Filled in during planning. Tasks must map to WATCH-01 / WATCH-02 / WATCH-03 and the
four phase success criteria. Planner is responsible for populating rows that
reference concrete `tests/watchlist/test_*.py` files.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | WATCH-01 | — | N/A | unit+integration | `pytest tests/watchlist/test_routes_get.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WATCH-02 | — | N/A | unit+integration | `pytest tests/watchlist/test_routes_post.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WATCH-03 | — | N/A | unit+integration | `pytest tests/watchlist/test_routes_delete.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/watchlist/__init__.py` — package marker
- [ ] `backend/tests/watchlist/conftest.py` — shared fixtures (warmed cache, mock source)
- [ ] Reuse `backend/tests/conftest.py` `_build_app` and `fresh_db` fixtures
- [ ] No new dependencies required — pytest/pytest-asyncio already installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SSE stream reflects watchlist add/remove end-to-end | Success #2, #3 | SSE cadence is 500ms and crosses async boundaries; covered by Phase 10 Playwright | Run `uv run uvicorn app.main:app`, `curl -N http://localhost:8000/api/stream/prices`, POST+DELETE tickers |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
