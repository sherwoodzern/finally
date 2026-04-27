---
status: diagnosed
trigger: "Phase 8 UAT test-3: chat returns HTTP 422; NVDA buy + PYPL watchlist add fail."
created: 2026-04-26
updated: 2026-04-26
---

## Current Focus

hypothesis: Frontend `postChat()` sends `{content}` but backend `ChatRequest` requires `{message}` with `extra='forbid'` -> Pydantic v2 rejects with two errors -> FastAPI 422.
test: Read both sides of the wire contract literally and compare field names.
expecting: Direct field-name mismatch with no aliases / pre-validators that would rescue it.
next_action: Write diagnosis writeup. Do not apply the fix.

## Symptoms

expected: POST /api/chat with the user's message returns 200 + ChatResponse; NVDA buy executes; PYPL added to watchlist.
actual: POST /api/chat returns HTTP 422 (FastAPI body validation error). No trade executed. Watchlist unchanged.
errors: HTTP 422 from /api/chat (visible in DevTools Network tab).
reproduction: Open http://localhost:8000/, open chat drawer, type "Buy 5 shares of NVDA and add PYPL to my watchlist.", press Enter.
started: First exercised in Phase 8 UAT test-3 (chat agentic auto-execute).

## Eliminated

(none — single hypothesis confirmed on first read of both sides.)

## Evidence

- timestamp: 2026-04-26
  checked: backend/app/chat/models.py
  found: line 51-56 — `class ChatRequest(BaseModel): model_config = ConfigDict(extra="forbid"); message: str = Field(min_length=1, max_length=8192)`. No alias. No `content` field. `extra="forbid"` rejects unknown keys.
  implication: Backend requires JSON body `{"message": "..."}`. Any other key shape -> 422.

- timestamp: 2026-04-26
  checked: backend/app/chat/routes.py
  found: line 38-42 — `@router.post("") async def post_chat_route(req: ChatRequest)`; service called with `req.message`. Comment at line 32-34 explicitly states `extra='forbid'` causes 422 via FastAPI default handler.
  implication: Route is wired correctly; the contract is `message`, not `content`.

- timestamp: 2026-04-26
  checked: frontend/src/lib/api/chat.ts
  found: line 63 — `export async function postChat(body: { content: string })`. line 67 — `body: JSON.stringify(body)`. Wire payload is `{"content":"<text>"}`.
  implication: Frontend sends `content`, not `message`. This violates the backend contract on two counts simultaneously: (a) missing required `message`, (b) extra forbidden key `content`.

- timestamp: 2026-04-26
  checked: frontend/src/components/chat/ChatThread.tsx
  found: line 77 — `mutation.mutate({ content: text })`. Sole caller of `postChat`.
  implication: Bug is at the API-client boundary (chat.ts), not in the React component. Fixing chat.ts alone cures all callers.

- timestamp: 2026-04-26
  checked: backend/tests/chat/test_routes_chat.py
  found: lines 61, 76, 91, 99, 106, 114 — every backend route test posts `json={"message": ...}` or `json={}`.
  implication: Backend tests don't exercise the actual frontend payload, which is why the contract drift slipped through. A regression test should send the *frontend's* exact body shape and assert 200 (or assert that posting `{content: "..."}` is 422 and posting `{message: "..."}` is 200, locking the contract).

## Resolution

root_cause: |
  Field-name mismatch at the /api/chat wire boundary. Frontend `postChat()` 
  (frontend/src/lib/api/chat.ts:63) types its body as `{ content: string }` and 
  serializes `{"content": "..."}` to the network. Backend `ChatRequest` 
  (backend/app/chat/models.py:51-56) requires field `message` and is configured 
  with `model_config = ConfigDict(extra="forbid")`. Pydantic v2 raises two 
  validation errors (missing required field `message`; extra forbidden key 
  `content`); FastAPI's default validation handler returns HTTP 422. The chat 
  request never reaches `service.run_turn`, so neither the NVDA buy nor the PYPL 
  watchlist-add ever execute.

fix: |
  Single-side, two-line change in `frontend/src/lib/api/chat.ts`:
    - line 63 type:   `body: { content: string }`  ->  `body: { message: string }`
    - line 67 payload is auto-correct after the type change (still `JSON.stringify(body)`)
  And the lone caller `frontend/src/components/chat/ChatThread.tsx:77`:
    - `mutation.mutate({ content: text })`  ->  `mutation.mutate({ message: text })`
  Backend is the source of truth (PLAN.md Section 9, Phase 5 D-07 contract); 
  frontend is what drifted. Fix on the frontend only.

verification: (not applied — diagnosis only.)
files_changed: []
