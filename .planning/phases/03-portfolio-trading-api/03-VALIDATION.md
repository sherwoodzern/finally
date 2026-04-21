---
phase: 3
slug: portfolio-trading-api
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Filled from 03-RESEARCH.md "## Validation Architecture" section by the planner.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio (auto mode) — already configured in `backend/pyproject.toml` |
| **Config file** | `backend/pyproject.toml` (pytest section) + `backend/tests/conftest.py` |
| **Quick run command** | `cd backend && uv run --extra dev pytest backend/tests/portfolio -x -q` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -q` |
| **Estimated runtime** | ~8 seconds (portfolio subset) / ~20 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick command (portfolio subset only)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

> Planner will populate this table from plan task breakdown. Each PORT-XX must map to at least one automated command.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | MARKET-ABC | — | Tick observer contract | unit | `cd backend && uv run --extra dev pytest tests/market/test_observer.py -q` | ✅ | ✅ green |
| 03-02-01 | 02 | 2 | PORT-02 | — | Weighted avg_cost on BUY | unit | `cd backend && uv run --extra dev pytest tests/portfolio/test_service_buy.py -q` | ✅ | ✅ green |
| 03-02-02 | 02 | 2 | PORT-02 | — | Partial/full sell + zero-row delete | unit | `cd backend && uv run --extra dev pytest tests/portfolio/test_service_sell.py -q` | ✅ | ✅ green |
| 03-02-03 | 02 | 2 | PORT-03 | — | Domain exceptions raised | unit | `cd backend && uv run --extra dev pytest tests/portfolio/test_service_validation.py -q` | ✅ | ✅ green |
| 03-03-01 | 03 | 3 | PORT-01 | — | GET /api/portfolio shape + fallback | integration | `cd backend && uv run --extra dev pytest tests/portfolio/test_routes_portfolio.py -q` | ✅ | ✅ green |
| 03-03-02 | 03 | 3 | PORT-02, PORT-03 | — | POST /trade 200/400 contract | integration | `cd backend && uv run --extra dev pytest tests/portfolio/test_routes_trade.py -q` | ✅ | ✅ green |
| 03-03-03 | 03 | 3 | PORT-04 | — | GET /history ordering + limit | integration | `cd backend && uv run --extra dev pytest tests/portfolio/test_routes_history.py -q` | ✅ | ✅ green |
| 03-03-04 | 03 | 3 | PORT-05 | — | 60s cadence + trade-reset clock | integration | `cd backend && uv run --extra dev pytest tests/portfolio/test_snapshot_observer.py -q` | ✅ | ✅ green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/portfolio/__init__.py` — package marker
- [ ] `backend/tests/portfolio/conftest.py` — cache-warming fixture + in-memory app harness (extends Phase 1/2 `_build_app`)
- [ ] `backend/tests/market/test_observer.py` — new test file for `register_tick_observer` contract
- [ ] `backend/tests/portfolio/test_service_buy.py` — Wave 0 stubs for BUY-side service tests
- [ ] `backend/tests/portfolio/test_service_sell.py` — Wave 0 stubs for SELL-side service tests
- [ ] `backend/tests/portfolio/test_service_validation.py` — Wave 0 stubs for domain-exception tests
- [ ] `backend/tests/portfolio/test_routes_portfolio.py` — Wave 0 stubs for GET /api/portfolio
- [ ] `backend/tests/portfolio/test_routes_trade.py` — Wave 0 stubs for POST /trade
- [ ] `backend/tests/portfolio/test_routes_history.py` — Wave 0 stubs for GET /history
- [ ] `backend/tests/portfolio/test_snapshot_observer.py` — Wave 0 stubs for snapshot observer

No framework install needed — pytest + pytest-asyncio already in `[project.optional-dependencies].dev`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end portfolio view in browser | PORT-01 | Requires Phase 6 frontend wiring — not Phase 3 scope | Deferred to Phase 7 UI integration. |
| Real-money trade integration | — | Explicitly out of scope — simulated money only | N/A (scope exclusion). |

*All Phase 3 behaviors required by success criteria have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
