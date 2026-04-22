---
phase: 05
slug: ai-chat-integration
status: verified
threats_total: 22
threats_closed: 22
threats_open: 0
asvs_level: 1
created: 2026-04-22
---

# Phase 05 — Security (AI Chat Integration)

> Per-phase security contract: threat register, accepted risks, and audit trail for the chat subsystem (`backend/app/chat/`, `backend/app/lifespan.py`).
>
> Threat IDs are disambiguated by plan prefix because Plan 01 and Plan 02 use the same `T-05-NN` shorthand in their own registers:
>
> - `T-05-01-NN` → Plan 01 threat NN (Chat Foundations — models, client, mock, prompts)
> - `T-05-02-NN` → Plan 02 threat NN (Chat Service Orchestration — run_turn, get_history)
> - `T-05-03-NN` → Plan 03 threat NN (Chat Routes — HTTP edge + lifespan wiring)

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser → FastAPI (`POST /api/chat`, `GET /api/chat/history`) | Untrusted JSON input crosses the wire; Pydantic v2 with `extra="forbid"` is the ONLY validator before the service layer is called | `ChatRequest.message` (user text, up to 8KB); `limit` query param (int 1..500) |
| `run_turn` ← LLM structured output | `StructuredResponse` from third-party LLM (Cerebras via OpenRouter via LiteLLM) crosses into auto-exec | `trades[]`, `watchlist_changes[]` |
| FastAPI lifespan ← `os.environ` | `LLM_MOCK` and `OPENROUTER_API_KEY` read once at startup | env strings; key value never logged |
| `service` → `portfolio.execute_trade` | TradeAction data flows into the validated manual-trade path — same guarantees as `POST /api/portfolio/trade` | ticker, side, quantity |
| `service` → `watchlist.{add,remove}_ticker` | WatchlistAction data flows into the validated mutation path — same guarantees | ticker |
| `service` → `chat_messages.actions` JSON | `TradeActionResult`/`WatchlistActionResult` serialized via `model_dump(mode="json")` + `json.dumps` | enriched per-action results |
| `chat_messages` ← user message content | `ChatRequest.message` persisted to `chat_messages.content` without further sanitization (trusted single-user demo) | user text |

---

## Threat Register

### Plan 01 — Chat Foundations (`backend/app/chat/{models,client,mock,prompts}.py`)

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-01-01 | Tampering | `StructuredResponse` parsing in `LiveChatClient` | mitigate | `ConfigDict(extra="forbid")` on `StructuredResponse`, `TradeAction`, `WatchlistAction` forces `additionalProperties:false`. Evidence: `backend/app/chat/models.py:15,30,44`. `LiveChatClient` boundary parse via `StructuredResponse.model_validate_json(raw)` at `backend/app/chat/client.py:49`. Locked by `backend/tests/chat/test_models.py:37-45` (rejects extras/missing `message`). | closed |
| T-05-01-02 | DoS / Info Disclosure | `ChatRequest.message` (unbounded input) | mitigate | `Field(min_length=1, max_length=8192)` at `backend/app/chat/models.py:56`. Locked by `backend/tests/chat/test_models.py:85-95` (`test_rejects_empty_message`, `test_enforces_max_length`). | closed |
| T-05-01-03 | Tampering | `TradeAction.ticker` / `WatchlistAction.ticker` from LLM output | mitigate | `@field_validator("ticker", mode="before")` at `backend/app/chat/models.py:21-24` and `:35-38` delegates to `app.watchlist.models.normalize_ticker` (regex `^[A-Z][A-Z0-9.]{0,9}$`). Locked by `backend/tests/chat/test_models.py:49-51,69-71` (`test_normalizes_ticker`). | closed |
| T-05-01-04 | Info Disclosure | `OPENROUTER_API_KEY` leakage via `LiveChatClient` | mitigate | `LiveChatClient` never reads or stores the key — LiteLLM picks it up from the environment at call time. Verification: `grep -nE "OPENROUTER_API_KEY|api_key" backend/app/chat/client.py` → only a docstring match at line 32 ("LiteLLM picks it up from the environment at call time"), zero code references. | closed |
| T-05-01-05 | DoS | Malformed LLM JSON crashing service | accept (deferred to Plan 02) | Accepted at Plan 01 boundary; Plan 02 wraps the call in `ChatTurnError` → HTTP 502 (covered by T-05-02-04 below). Plan 01 test `test_client_live.py` asserts the happy parse path. | closed |
| T-05-01-06 | Tampering | `MockChatClient` regex false-match ("buyout AAPL") | mitigate | All four regexes in `backend/app/chat/mock.py:12-15` use word-boundary anchors (`\b...\b`). Locked by `backend/tests/chat/test_mock_client.py:24-26` (`test_buyout_is_not_a_buy`). | closed |

### Plan 02 — Chat Service Orchestration (`backend/app/chat/service.py`)

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-02-01 | Tampering | Auto-exec bypasses manual-trade validation | mitigate | `_run_one_trade` calls `execute_trade(conn, cache, ta.ticker, ta.side, ta.quantity)` at `backend/app/chat/service.py:100` — the same function used by `POST /api/portfolio/trade`. Same `TradeValidationError` hierarchy caught as tuple at `:101-106`. Locked by `backend/tests/chat/test_service_failures.py:21-71` (`TestAutoExecFailureTranslation` — one test per code: insufficient_cash, insufficient_shares, unknown_ticker, price_unavailable). | closed |
| T-05-02-02 | Elevation of Privilege | LLM injects malformed `side` or negative `quantity` into `TradeAction` | mitigate | `TradeAction` Pydantic model: `ConfigDict(extra="forbid")`, `side: Literal["buy","sell"]`, `quantity: float = Field(gt=0)` at `backend/app/chat/models.py:15-19`. Validation happens at `client.complete()` parse time before `run_turn` sees the object. `ValueError` fallback at `backend/app/chat/service.py:122-132` maps to `error="invalid_ticker"`. Locked by `backend/tests/chat/test_models.py:53-65` (`test_rejects_zero_quantity`, `test_rejects_bad_side`, `test_rejects_extra_keys`). | closed |
| T-05-02-03 | Denial of Service | Runaway loop of failed actions (LLM emits 1000 bad trades) | accept | Structured output schema is small; typical turns emit ≤5 actions. Single-user demo; no per-turn cap planned until multi-user + auth phase. Failed trades short-circuit on validation with no DB writes. Documented in Plan 02 threat register. | closed |
| T-05-02-04 | Information Disclosure | LLM failure message could leak upstream provider details | mitigate | `logger.error("LLM call failed", exc_info=True)` at `backend/app/chat/service.py:257` writes the full traceback to the local process log only. `ChatTurnError(str(exc))` at `:258` carries only the stringified message into the HTTP 502 body — acceptable for single-user local demo. Single-user contract documented; Plan 03 PLAN acknowledges no redaction layered on top. | closed |
| T-05-02-05 | Tampering | Race between two concurrent `run_turn` calls for the same user | accept | Single-user demo; concurrent POSTs are unlikely. SQLite connection-level serialization would linearize `execute_trade` writes anyway. Deferred to v2 auth per CONTEXT.md. | closed |
| T-05-02-06 | Repudiation | No `chat_messages` row for a failed LLM call leaves an unlogged turn | mitigate | D-18 persistence ordering: `_persist_user_turn(conn, user_message)` at `backend/app/chat/service.py:250` is called BEFORE `await client.complete(messages)` at `:255`. Locked by `backend/tests/chat/test_service_persistence.py:23-35` (`TestUserTurnBeforeLLM::test_user_row_persisted_even_if_llm_raises` asserts exactly 1 row with role='user' and actions IS NULL after an LLM raise). | closed |
| T-05-02-07 | Tampering | JSON in `chat_messages.actions` could be unparseable on history read | mitigate | `_persist_assistant_turn` uses `json.dumps` on `model_dump(mode="json")` output at `backend/app/chat/service.py:70-77` — guaranteed serializable. `get_history` uses `json.loads(actions_raw) if actions_raw is not None else None` at `:296-297`. Locked by `backend/tests/chat/test_service_persistence.py:38-54` (`TestAssistantTurnAfterAutoExec::test_assistant_row_actions_column_is_enriched_json`). | closed |

### Plan 03 — Chat Routes (`backend/app/chat/routes.py`, `backend/app/lifespan.py`)

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-03-01 | Spoofing | `POST /api/chat` (no auth per single-user contract) | accept | Phase 5 scope is single-user default; PLAN.md §7 hardcodes `user_id="default"`. Multi-user is out of scope. Single-user invariant enforced by greppable absence of `user_id` in the HTTP surface (see T-05-03-08). Documented in 05-03-SUMMARY.md "Threats Mitigated" §. | closed |
| T-05-03-02 | Tampering | `ChatRequest.message` body | mitigate | Pydantic v2 `ConfigDict(extra="forbid")` + `Field(min_length=1, max_length=8192)` at `backend/app/chat/models.py:54-56`. Locked by `backend/tests/chat/test_routes_chat.py:87-116` (4 × 422 tests: `test_empty_message_returns_422`, `test_extra_key_returns_422`, `test_missing_message_returns_422`, `test_message_over_limit_returns_422`). | closed |
| T-05-03-03 | Tampering | `GET /api/chat/history?limit=N` — unbounded pagination | mitigate | `Query(default=50, ge=1, le=500)` at `backend/app/chat/routes.py:54`. Locked by `backend/tests/chat/test_routes_history.py:85-88` (`limit=0` and `limit=501` → 422). | closed |
| T-05-03-04 | Repudiation | Chat audit trail survives LLM failures | mitigate | D-18 invariant enforced in Plan 02's `run_turn` (see T-05-02-06). Plan 03 proves the invariant at the HTTP boundary via `backend/tests/chat/test_routes_llm_errors.py:110-131` (`TestLLMFailureBoundary::test_chat_turn_error_maps_to_502_with_error_envelope` — a 502 response still leaves exactly 1 new `chat_messages` row using `RaisingChatClient`). | closed |
| T-05-03-05 | Information Disclosure | `OPENROUTER_API_KEY` leaking via logs or error bodies | mitigate | Startup warning at `backend/app/lifespan.py:48-55` is a fixed string that never formats the key value — only its presence/absence gates the warning. Verification: `grep -nE "%s.*OPENROUTER_API_KEY" backend/app/lifespan.py` → zero matches. `ChatTurnError` wraps LiteLLM/OpenRouter exceptions whose messages do not include the key. | closed |
| T-05-03-06 | Denial of Service | Large `message` bodies or pathological regex | mitigate | `max_length=8192` at `backend/app/chat/models.py:56` caps input at 8 KB. `MockChatClient` regexes are linear, word-boundary-anchored (`backend/app/chat/mock.py:12-15`) — no catastrophic backtracking. Live mode's latency is bounded by OpenRouter's own request timeout. | closed |
| T-05-03-07 | Denial of Service | History-query large `limit` | mitigate | `limit ≤ 500` at the Query level (see T-05-03-03). The two-level subquery in `get_history` at `backend/app/chat/service.py:286-292` selects only the most recent `limit` rows via SQL — no Python-side slicing of an unbounded fetch. | closed |
| T-05-03-08 | Elevation of Privilege | Route handler bypassing `user_id` scoping | accept | Single-user mode: `run_turn` and `get_history` both default `user_id="default"`. Route handlers never reference `user_id`. Verification: `grep -nE "user_id" backend/app/chat/routes.py` → zero matches. Future multi-user phase will add auth + route-level scoping. | closed |
| T-05-03-09 | Elevation of Privilege | Chat-initiated trades bypass manual trade validation | mitigate | `_run_one_trade` at `backend/app/chat/service.py:100` calls `portfolio.service.execute_trade` — the SAME path as `POST /api/portfolio/trade`. Full `TradeValidationError` hierarchy surfaces as per-action `failed` entries with `exc.code` (see T-05-02-01). Plan 03 does not weaken the path. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-01-05 | Malformed LLM JSON at Plan-01 boundary — accepted at Plan 01 scope only; covered by T-05-02-04's `ChatTurnError` → HTTP 502 wrapper in Plan 02 | Planner (05-01-PLAN.md `<threat_model>`) | 2026-04-22 |
| AR-05-02 | T-05-02-03 | No per-turn action cap on LLM-emitted trades. Single-user demo; typical turns emit ≤5 actions; failed trades short-circuit on validation with ~0 DB writes. Goes with auth + multi-user in v2 | Planner (05-02-PLAN.md `<threat_model>`) | 2026-04-22 |
| AR-05-03 | T-05-02-04 | `ChatTurnError(str(exc))` surfaces stringified upstream LLM exception into HTTP 502 body. Dev-grade local demo; not exposed to network; no redaction layered on top. Plan 03 explicitly declined to add a redaction layer | Planner (05-02-PLAN.md `<threat_model>`, 05-03-PLAN.md D-14) | 2026-04-22 |
| AR-05-04 | T-05-02-05 | Concurrent `run_turn` races for the same user. Single-user demo; SQLite connection-level serialization linearizes writes. Deferred to v2 auth | Planner (05-02-PLAN.md `<threat_model>`) | 2026-04-22 |
| AR-05-05 | T-05-03-01 | No authentication on `POST /api/chat`. Single-user capstone; PLAN.md §7 hardcodes `user_id="default"`. Future auth phase adds route-level scoping | Planner (05-03-PLAN.md `<threat_model>`) | 2026-04-22 |
| AR-05-06 | T-05-03-08 | `run_turn` / `get_history` default `user_id="default"` with no HTTP exposure. Greppable invariant (`grep -nE "user_id" backend/app/chat/routes.py` → zero matches). Future multi-user phase adds auth + route-level scoping | Planner (05-03-PLAN.md `<threat_model>`) | 2026-04-22 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Threat Flags

No `## Threat Flags` section present in any of the three Phase 05 SUMMARY.md files (`05-01-SUMMARY.md`, `05-02-SUMMARY.md`, `05-03-SUMMARY.md`). No unregistered flags to report.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-22 | 22 | 22 | 0 | gsd-secure-phase (Claude Opus 4.7) |

Verification summary:
- 16 mitigate-disposition threats verified by grep in implementation files + test-locked invariants
- 6 accept-disposition threats verified as present in the Accepted Risks Log above
- All greppable invariants from 05-03-PLAN.md `<threat_model>` hold:
  - `grep -nE "user_id" backend/app/chat/routes.py` → **0 matches** (T-05-03-08)
  - `grep -nE "%s.*OPENROUTER_API_KEY" backend/app/lifespan.py` → **0 matches** (T-05-03-05)
  - Word-boundary `\b` anchors present on all four `MockChatClient` regexes at `backend/app/chat/mock.py:12-15` (T-05-01-06)
  - `ConfigDict(extra="forbid")` present on `StructuredResponse`, `TradeAction`, `WatchlistAction`, `ChatRequest` (T-05-01-01, T-05-03-02)
  - `_persist_user_turn` at `service.py:250` strictly precedes `await client.complete(...)` at `:255` (T-05-02-06, T-05-03-04)

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (6 entries)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-22
