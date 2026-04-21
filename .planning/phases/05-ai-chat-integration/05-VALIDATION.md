---
phase: 05
slug: ai-chat-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
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
| 05-01-W0 | 01 | 0 | Test infra | — | N/A | wave-0 | `pytest tests/chat --collect-only` | ❌ W0 | ⬜ pending |
| 05-01-01 | 01 | 1 | CHAT-02 | — | N/A | unit | `pytest tests/chat/test_models.py -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | CHAT-02 | — | N/A | unit | `pytest tests/chat/test_client_live.py -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | CHAT-06 | — | Mock mode deterministic | unit | `pytest tests/chat/test_mock_client.py -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | CHAT-03 | — | N/A | unit | `pytest tests/chat/test_prompts.py -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | CHAT-04, CHAT-05 | T-05-01 | Validation path preserved in auto-exec | unit | `pytest tests/chat/test_service_run_turn.py -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | CHAT-04 | T-05-01 | Continue-on-failure surfaces per-action failures | unit | `pytest tests/chat/test_service_failures.py -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | CHAT-05 | — | User turn persists before LLM, NULL actions | unit | `pytest tests/chat/test_service_persistence.py -x` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 3 | CHAT-01, CHAT-06 | T-05-02 | Structured input rejects extras | integration | `pytest tests/chat/test_routes_chat.py -x` | ❌ W0 | ⬜ pending |
| 05-03-02 | 03 | 3 | CHAT-01 | — | History bounds enforced | integration | `pytest tests/chat/test_routes_history.py -x` | ❌ W0 | ⬜ pending |
| 05-03-03 | 03 | 3 | CHAT-04 | T-05-03 | LLM failure → 502 with user-turn-only | integration | `pytest tests/chat/test_routes_llm_errors.py -x` | ❌ W0 | ⬜ pending |
| 05-03-04 | 03 | 3 | TEST-01 | — | Full regression + coverage | regression | `pytest -v && pytest --cov=app.chat --cov-fail-under=93` | ✅ (207 existing) | ⬜ pending |

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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags (`-f`, `--watch`, etc.)
- [ ] Feedback latency < 10s per-commit
- [ ] `nyquist_compliant: true` set in frontmatter (after checker approval)

**Approval:** pending
