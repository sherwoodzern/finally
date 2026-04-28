---
status: complete
phase: 08-portfolio-visualization-chat-ui
test: UAT 3 — chat agentic auto-execute (HTTP 422)
created: 2026-04-26
updated: 2026-04-28
resolution: "Fix shipped in commit c2a2c88 — frontend/src/lib/api/chat.ts postChat body field renamed content -> message; ChatThread.tsx caller updated. Phase 8 UAT test-3 subsequently passed (see 08-HUMAN-UAT.md test 3 result: pass)."
---

# Phase 8 UAT Fix-3 — Root Cause Diagnosis

**UAT test:** test-3 (chat agentic auto-execute)
**Symptom:** POST `/api/chat` returns HTTP 422; NVDA buy and PYPL watchlist-add never execute.
**Status:** Root cause proven on direct evidence. Fix shipped in commit c2a2c88; UAT test-3 subsequently passed.

---

## Root Cause

The frontend `postChat()` request body and the backend `ChatRequest` Pydantic v2 model
disagree on the field name for the user's prompt text.

| Side | File:Line | Field name | Source of truth? |
|------|-----------|------------|------------------|
| Backend (server) | `backend/app/chat/models.py:56` | **`message`** (required, `min_length=1`, `max_length=8192`) | Yes — PLAN.md Section 9 / Phase 5 D-07 |
| Frontend (client) | `frontend/src/lib/api/chat.ts:63` | **`content`** (typed as `body: { content: string }`) | No — drifted |

Backend `ChatRequest` is declared with `model_config = ConfigDict(extra="forbid")`
(`backend/app/chat/models.py:54`), so an incoming `{"content":"..."}` payload triggers
**two** Pydantic validation errors simultaneously:

1. `message` — `Field required` (the required field is absent)
2. `content` — `Extra inputs are not permitted` (forbidden by `extra="forbid"`)

FastAPI's default request-validation handler maps Pydantic `ValidationError` to **HTTP 422**.
Execution never reaches `service.run_turn(...)` (`backend/app/chat/routes.py:42`), so no
trade is placed and no watchlist change is recorded.

### Caller chain (frontend)

```
ChatInput submit
  -> ChatThread.tsx:77    mutation.mutate({ content: text })
  -> chat.ts:63-68        postChat({ content }) -> JSON.stringify({ content }) -> POST /api/chat
                          wire payload: {"content":"Buy 5 shares of NVDA and add PYPL..."}
```

### Receiver (backend)

```
routes.py:38-42           @router.post("") async def post_chat_route(req: ChatRequest)
models.py:51-56           ChatRequest: message: str (required), extra="forbid"
                          -> Pydantic v2 rejects -> FastAPI 422
```

### Why it wasn't caught earlier

Every backend route test posts the correct field name (`backend/tests/chat/test_routes_chat.py`
lines 61, 76, 91, 99, 114 — all `json={"message": ...}`). No test exercises the
**frontend's actual payload shape**, so the drift was invisible to CI.

---

## Minimum-Change Fix

**Side to fix:** Frontend. The backend contract matches PLAN.md Section 9 ("Send a message,
receive complete JSON response") and the Phase 5 D-07 schema; the frontend is what drifted.

**Two lines, one file (and one matching call site):**

`frontend/src/lib/api/chat.ts` line 63:
```diff
-export async function postChat(body: { content: string }): Promise<ChatResponse> {
+export async function postChat(body: { message: string }): Promise<ChatResponse> {
```

`frontend/src/components/chat/ChatThread.tsx` line 77:
```diff
-    mutation.mutate({ content: text });
+    mutation.mutate({ message: text });
```

`JSON.stringify(body)` on `chat.ts:67` does not need to change — it serializes whatever the
new type declares.

That is the entire change. No backend edits. No other call sites of `postChat` exist
(`grep -rn "postChat" frontend/src/` returns only the chat module).

---

## Regression Test

Add a thin wire-shape test that locks the field-name contract from the **frontend's** side.
This catches any future drift the moment a developer renames the payload key on either side.

### Option A (preferred) — backend integration test that pins the contract

`backend/tests/chat/test_routes_chat.py`:

```python
class TestChatRequestContract:
    """Lock the wire shape that the frontend's postChat() sends."""

    async def test_message_is_the_required_key(self, client):
        # The exact shape produced by frontend/src/lib/api/chat.ts postChat()
        resp = await client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 200

    async def test_content_key_is_rejected_422(self, client):
        # Guards against the UAT test-3 bug ever reappearing on the frontend.
        resp = await client.post("/api/chat", json={"content": "hello"})
        assert resp.status_code == 422
        body = resp.json()
        # Pydantic v2 reports both: missing 'message' AND extra 'content'.
        locs = {tuple(err["loc"]) for err in body["detail"]}
        assert ("body", "message") in locs
        assert ("body", "content") in locs
```

### Option B (complementary) — frontend unit test for `postChat`

`frontend/src/lib/api/chat.test.ts`:

```ts
import { postChat } from './chat';

it('sends { message } at the wire boundary', async () => {
  const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ message: 'ok', trades: [], watchlist_changes: [] }),
                 { status: 200, headers: { 'Content-Type': 'application/json' } }),
  );
  await postChat({ message: 'hi' });
  const [, init] = fetchSpy.mock.calls[0];
  expect(JSON.parse(init!.body as string)).toEqual({ message: 'hi' });
});
```

Either test alone would have failed against the current code with a clear, single-cause
error message. Together they pin both ends of the contract.

---

## Files Inspected (read-only)

- `frontend/src/lib/api/chat.ts` — `postChat()` definition (the bug)
- `frontend/src/components/chat/ChatThread.tsx` — sole caller
- `backend/app/chat/models.py` — `ChatRequest` schema (the contract)
- `backend/app/chat/routes.py` — POST endpoint binding
- `backend/tests/chat/test_routes_chat.py` — confirms backend tests use `message`, not `content`
