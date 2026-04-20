---
phase: 02
slug: database-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio 0.24+ (already pinned in `backend/pyproject.toml:17-23`) |
| **Config file** | `backend/pyproject.toml` — `[tool.pytest.ini_options]`, `asyncio_mode = "auto"` |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/db/ -v` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -v` |
| **Estimated runtime** | ~15 seconds full suite (~2 seconds quick) |

---

## Sampling Rate

- **After every task commit:** `cd backend && uv run --extra dev pytest tests/db/ -x`
- **After every plan wave:** `cd backend && uv run --extra dev pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DB-01 | — | Tables and unique constraints created idempotently | unit | `uv run --extra dev pytest tests/db/test_schema.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | DB-02 | — | Seed inserts exactly SEED_PRICES keys + 1 users_profile(cash=10000) | unit | `uv run --extra dev pytest tests/db/test_seed.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | DB-01, DB-02 | — | Lifespan attaches `app.state.db` after init+seed | integration | `uv run --extra dev pytest tests/test_lifespan.py::TestLifespan::test_attaches_db_to_app_state -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | DB-02 (implicit D-05) | — | Tickers come from DB watchlist, not SEED_PRICES directly | integration | `uv run --extra dev pytest tests/test_lifespan.py::TestLifespan::test_tickers_come_from_db_watchlist -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | DB-03 | — | Second startup against same DB file is a no-op (no duplicate seed) | integration | `uv run --extra dev pytest tests/test_lifespan.py::TestLifespan::test_second_startup_is_no_op -x` | ❌ W0 | ⬜ pending |
| 02-02-04 | 02 | 2 | DB-03 | — | Open → seed → close → re-open same path preserves seed rows | integration | `uv run --extra dev pytest tests/db/test_persistence.py -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | D-06 | — | `market_data_demo.py` reuses `list(SEED_PRICES.keys())` — no local TICKERS constant | unit | `uv run --extra dev pytest tests/db/test_demo_refactor.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/db/__init__.py` — empty package marker
- [ ] `backend/tests/db/test_schema.py` — DB-01 stubs (tables exist, UNIQUE constraints, defaults)
- [ ] `backend/tests/db/test_seed.py` — DB-02 stubs (seed content + idempotence)
- [ ] `backend/tests/db/test_persistence.py` — DB-03 stubs (reopen cycle)
- [ ] `backend/tests/db/test_demo_refactor.py` — D-06 stub (demo reuses SEED_PRICES)
- [ ] Extend `backend/tests/conftest.py` with `db_path` fixture (monkeypatches `DB_PATH` → `tmp_path / "finally.db"`)
- [ ] Extend `backend/tests/test_lifespan.py` with: `test_attaches_db_to_app_state`, `test_tickers_come_from_db_watchlist`, `test_second_startup_is_no_op`
- [ ] No framework install needed — `uv sync --extra dev` already pulls pytest-asyncio, asgi-lifespan, httpx

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Data survives a real Docker volume mount across container restarts | DB-03 (end-to-end) | Requires Docker, not just a process — deferred to Phase 9/10 when Docker ships | Phase 10 Playwright suite runs two `docker run` cycles against the same named volume and verifies `cash_balance` + watchlist persist |

*All unit/integration behaviors have automated verification above; only the end-to-end "Docker volume persists across container restarts" is manual and deferred.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
