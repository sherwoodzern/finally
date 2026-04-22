---
phase: 05
slug: ai-chat-integration
status: audited
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-21
audited: 2026-04-22
audit_total_requirements: 7
audit_covered: 7
audit_partial: 0
audit_missing: 0
audit_gaps_found: 1
audit_gaps_resolved: 1
audit_gaps_escalated: 0
audit_manual_only: 1
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ with pytest-asyncio 0.24+, pytest-cov 5.0+, httpx, asgi-lifespan |
| **Config file** | `backend/pyproject.toml` `[tool.pytest.ini_options]` — `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"` |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/chat -x -q` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -v` |
| **Coverage command** | `cd backend && uv run --extra dev pytest --cov=app --cov-report=term-missing` |
| **Lint command** | `cd backend && uv run --extra dev ruff check app/chat tests/chat` |
| **Estimated runtime** | ~10s quick (chat tests only) / ~30s full suite |

Baseline per `.planning/STATE.md`: 207/207 tests green as of 2026-04-21. Phase 5 adds ~40 new tests in `backend/tests/chat/`; the existing 207 MUST still be green after Phase 5.

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run --extra dev pytest tests/chat -x -q` (< 10s target)
- **After every plan wave:** Run `cd backend && uv run --extra dev pytest -v` (full suite; < 30s target)
- **Before `/gsd-verify-work`:** Full suite must be green + `--cov=app.chat` coverage ≥ 93% (Phase 3/4 precedent)
- **Max feedback latency:** 10 seconds for per-commit sampling

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-W0 | 01 | 0 | Test infra | — | N/A | wave-0 | `pytest tests/chat --collect-only` | ✅ | ✅ green |
| 05-01-01 | 01 | 1 | CHAT-02 | — | N/A | unit | `pytest tests/chat/test_models.py -x` | ✅ | ✅ green |
| 05-01-02 | 01 | 1 | CHAT-02 | — | N/A | unit | `pytest tests/chat/test_client_live.py -x` | ✅ | ✅ green |
| 05-01-03 | 01 | 1 | CHAT-06 | — | Mock mode deterministic | unit | `pytest tests/chat/test_mock_client.py -x` | ✅ | ✅ green |
| 05-01-04 | 01 | 1 | CHAT-03 | — | N/A | unit | `pytest tests/chat/test_prompts.py -x` | ✅ | ✅ green |
| 05-02-01 | 02 | 2 | CHAT-04, CHAT-05 | T-05-01 | Validation path preserved in auto-exec | unit | `pytest tests/chat/test_service_run_turn.py -x` | ✅ | ✅ green |
| 05-02-02 | 02 | 2 | CHAT-04 | T-05-01 | Continue-on-failure surfaces per-action failures | unit | `pytest tests/chat/test_service_failures.py -x` | ✅ | ✅ green |
| 05-02-03 | 02 | 2 | CHAT-05 | — | User turn persists before LLM, NULL actions | unit | `pytest tests/chat/test_service_persistence.py -x` | ✅ | ✅ green |
| 05-03-01 | 03 | 3 | CHAT-01, CHAT-06 | T-05-02 | Structured input rejects extras | integration | `pytest tests/chat/test_routes_chat.py -x` | ✅ | ✅ green |
| 05-03-02 | 03 | 3 | CHAT-01 | — | History bounds enforced | integration | `pytest tests/chat/test_routes_history.py -x` | ✅ | ✅ green |
| 05-03-03 | 03 | 3 | CHAT-04 | T-05-03 | LLM failure → 502 with user-turn-only | integration | `pytest tests/chat/test_routes_llm_errors.py -x` | ✅ | ✅ green |
| 05-03-04 | 03 | 3 | TEST-01 | — | Full regression + coverage | regression | `pytest -v && pytest --cov=app.chat --cov-fail-under=93` | ✅ | ✅ green (295/295, 99.17%) |
| 05-AUDIT-01 | — | audit | Replay idempotency property | — | Append-only log: replay leaves prior rows byte-identical | integration | `pytest tests/chat/test_routes_idempotency.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/chat/__init__.py` — package marker
- [ ] `backend/tests/chat/conftest.py` — `fresh_db`, `warmed_cache`, `fake_chat_client` (Protocol-compatible stub) fixtures; copy template from `backend/tests/watchlist/conftest.py`
- [ ] `backend/tests/chat/test_models.py` — stubs for StructuredResponse / ChatRequest (CHAT-02)
- [ ] `backend/tests/chat/test_client_live.py` — stubs for LiveChatClient call-shape (CHAT-02)
- [ ] `backend/tests/chat/test_mock_client.py` — stubs for MockChatClient regex patterns (CHAT-06)
- [ ] `backend/tests/chat/test_prompts.py` — stubs for `build_messages` / `build_portfolio_context` / history window (CHAT-03)
- [ ] `backend/tests/chat/test_service_run_turn.py` — stubs for happy-path run_turn (CHAT-04)
- [ ] `backend/tests/chat/test_service_failures.py` — stubs for D-12 exception matrix (CHAT-04)
- [ ] `backend/tests/chat/test_service_persistence.py` — stubs for user-before-LLM, assistant-after, NULL actions (CHAT-05)
- [ ] `backend/tests/chat/test_routes_chat.py` — stubs for POST /api/chat integration (CHAT-01)
- [ ] `backend/tests/chat/test_routes_history.py` — stubs for GET /api/chat/history integration (CHAT-01)
- [ ] `backend/tests/chat/test_routes_llm_errors.py` — stubs for LLM failure → 502 (CHAT-04)

Framework install: **not required** — `[project.optional-dependencies].dev` already includes pytest / pytest-asyncio / pytest-cov / httpx / asgi-lifespan. `uv sync --extra dev` is idempotent and will install `litellm` after D-21 adds it.

---

## Property & Contract Coverage

| Property | Owner | How Verified |
|----------|-------|--------------|
| Chat turn is idempotent-adjacent: replaying the same user message yields a new chat_messages pair without mutating prior rows | service | Integration test: count chat_messages rows before/after 2× same POST |
| LLM schema contract: golden sample JSON strings from PLAN.md §9 validate via `StructuredResponse.model_validate_json` | models | Unit test: golden strings pass parse |
| Response shape invariant: `trades` / `watchlist_changes` arrays are always present (empty allowed) | models | Unit test: ChatResponse from empty lists serializes with keys present |
| Error-boundary invariant: LLM errors NEVER become per-action `failed` entries | service | Integration test: client raises → response is 502, not 200-with-failed-actions |
| DB write ordering invariant: user turn exists with NULL actions even if LLM raises | service | Integration test in test_routes_llm_errors.py |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live LLM end-to-end smoke (OpenRouter + Cerebras structured output round-trip against a real key) | CHAT-02 (live path) | Requires a real `OPENROUTER_API_KEY`; not run in CI. Mock-mode tests exercise the code path; live path is a manual "does it talk to the provider" smoke. | With `.env` containing a valid `OPENROUTER_API_KEY` and `LLM_MOCK` unset, start the backend and `curl -X POST http://localhost:8000/api/chat -d '{"message":"What is my portfolio worth?"}'`; assert 200 with a non-empty `message` field and `trades=[], watchlist_changes=[]`. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags (`-f`, `--watch`, etc.)
- [x] Feedback latency < 10s per-commit (chat suite runs in ~0.15s)
- [x] `nyquist_compliant: true` set in frontmatter (after checker approval)

**Approval:** audited 2026-04-22

---

## Validation Audit 2026-04-22

**Auditor:** gsd-validate-phase Nyquist auditor
**Scope:** Phase 05 requirements CHAT-01..06 + TEST-01 (seven requirements total)
**Baseline at audit start:** 87 chat tests passing, 294 full-suite tests passing, `app.chat` coverage 99.17%

### Requirement Map (COVERED / PARTIAL / MISSING)

| Requirement | Source | Coverage | Evidence |
|-------------|--------|----------|----------|
| CHAT-01 | 05-03 SUMMARY, 05-RESEARCH §Test Map | COVERED | `test_routes_chat.py::TestPostChat` (6 tests incl. happy/extras/empty/missing/overlen/auto-exec); `test_routes_history.py::TestGetHistory` (4 tests incl. empty/ASC+shape/bounds/truncation) |
| CHAT-02 | 05-01 + 05-02 SUMMARY | COVERED | `test_client_live.py` (6 tests locking model, response_format, reasoning_effort, extra_body, messages; factory selection; structured content parse); `test_models.py::TestStructuredResponse` (4 tests incl. PLAN.md §9 schema parse + extra-key rejection) |
| CHAT-03 | 05-01 SUMMARY | COVERED | `test_prompts.py` (12 tests covering SYSTEM_PROMPT / CHAT_HISTORY_WINDOW==20 / default user_id / build_portfolio_context shape+JSON / build_messages ordering + 20-cap + user_id filter) |
| CHAT-04 | 05-02 + 05-03 SUMMARY | COVERED | `test_service_failures.py` (8 tests: D-12 four-code matrix + continue-on-failure + watchlist-first + internal_error fallback + ChatTurnError boundary); `test_service_run_turn.py::TestRunTurnRemove` + `::TestRunTurnWatchlistInternalError`; `test_routes_llm_errors.py` locks 502 envelope |
| CHAT-05 | 05-02 + 05-03 SUMMARY | COVERED | `test_service_persistence.py` (9 tests: user-before-LLM + assistant-after + user_id filter + get_history ASC + commit count); `test_routes_llm_errors.py` HTTP-boundary proof of D-18 |
| CHAT-06 | 05-01 SUMMARY | COVERED | `test_client_live.py::TestCreateChatClientFactory` (3 tests: LLM_MOCK=true → MockChatClient; absent → LiveChatClient; other value → LiveChatClient); `test_mock_client.py` (12 tests: buy/sell/add/remove/drop/combinations/no-match/case-insensitive/last-user-message/deterministic); end-to-end lifespan wiring proven via `test_routes_chat.py::test_mock_buy_keyword_executes_trade_and_echoes_result` (real `app.lifespan.lifespan` under `LLM_MOCK=true`) |
| TEST-01 | 05-01..05-03 SUMMARY | COVERED | Full suite: 294/294 green pre-audit; `--cov=app.chat --cov-fail-under=93` passes at 99.17% |

### Gaps Found

| # | Gap | Source | Action |
|---|-----|--------|--------|
| 1 | "Chat turn is idempotent-adjacent: replaying the same user message yields a new chat_messages pair without mutating prior rows" — listed in this document's own **Property & Contract Coverage** table as a service-layer invariant but never locked by a test. | 05-VALIDATION.md §Property & Contract Coverage row 1 | Added `tests/chat/test_routes_idempotency.py::TestReplayIdempotency::test_same_message_twice_appends_without_mutating_priors` — integration test that POSTs the same body twice under the real lifespan, snapshots chat_messages before and after, and asserts the first two rows are byte-identical across replay while two brand-new rows with distinct ids are appended. |

### Resolution

**1 gap found, 1 gap resolved, 0 escalated.**

- New file: `backend/tests/chat/test_routes_idempotency.py` (1 test, green first run).
- No implementation changes; only test additions.
- Re-run of `pytest tests/chat -q`: **88 passed** (prior 87 + 1 new).
- Re-run of full backend suite `pytest -q`: **295 passed** (prior 294 + 1 new).
- Coverage: `app.chat` still **99.17%** (gate 93%).
- Lint: `ruff check tests/chat/test_routes_idempotency.py` — clean.

### Manual-Only (Unchanged)

| Behavior | Why |
|----------|-----|
| Live LLM end-to-end smoke against real OpenRouter + Cerebras | Requires a real `OPENROUTER_API_KEY`; not runnable in CI. Mock-mode tests exercise the code path via `LiveChatClient` call-shape (unit) + `MockChatClient` (integration). Instructions already documented in §Manual-Only Verifications above. |

### Files for Commit (this audit)

- `backend/tests/chat/test_routes_idempotency.py` (new)
- `.planning/phases/05-ai-chat-integration/05-VALIDATION.md` (updated)

### Final Status

**NYQUIST COMPLIANT** — 7/7 requirements COVERED, all 12 per-task verify commands green, one documented property-contract gap filled, coverage gate passed at 99.17% (target ≥93%).
