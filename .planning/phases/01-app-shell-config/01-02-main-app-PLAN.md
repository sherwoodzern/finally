---
phase: 01-app-shell-config
plan: 02
type: execute
wave: 2
depends_on: ["01-app-shell-config-01"]
files_modified:
  - backend/app/main.py
autonomous: true
requirements: [APP-01, APP-03]
tags: [fastapi, entrypoint, env-config, health-check]

must_haves:
  truths:
    - "`uv run uvicorn app.main:app` from backend/ starts a FastAPI process listening on the configured port."
    - "GET /api/health returns HTTP 200 with body `{\"status\": \"ok\"}`."
    - "`.env` at the repo root is loaded ONCE via load_dotenv() at app construction, BEFORE the FastAPI app is built — so MASSIVE_API_KEY drives create_market_data_source correctly when lifespan runs."
    - "Missing OPENROUTER_API_KEY, MASSIVE_API_KEY, or LLM_MOCK does not crash startup; the simulator is selected when MASSIVE_API_KEY is absent (delegated to factory.create_market_data_source)."
    - "There is NO `if __name__ == \"__main__\":` block in main.py (D-03)."
  artifacts:
    - path: "backend/app/main.py"
      provides: "FastAPI application entrypoint with /api/health and lifespan wired"
      contains: "app = FastAPI(lifespan=lifespan)"
      min_lines: 25
  key_links:
    - from: "backend/app/main.py"
      to: "backend/app/lifespan.py"
      via: "from .lifespan import lifespan"
      pattern: "from \\.lifespan import lifespan"
    - from: "backend/app/main.py"
      to: ".env file at repo root"
      via: "load_dotenv() called before app = FastAPI(...)"
      pattern: "load_dotenv\\(\\)"
    - from: "uvicorn CLI"
      to: "backend/app/main.py:app"
      via: "uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
      pattern: "^app\\s*=\\s*FastAPI\\("
---

<objective>
Create `backend/app/main.py` — the FastAPI entrypoint that loads `.env`, builds the
`app` instance with the Plan 01 lifespan, and defines `/api/health` inline. Implements
decisions D-01 (two-file shell location), D-03 (uvicorn invoked via CLI only — no `__main__`
block), and D-04 (`/api/health` defined inline returning `{"status": "ok"}`; SSE router
mounted by lifespan, not here).

Purpose: Delivers APP-01 ("FastAPI application with `lifespan` startup ... exposes
`/api/health`") and the call site for APP-03 (`.env` loading via `load_dotenv()` BEFORE
`FastAPI(...)` so env vars are set when the lifespan reads `MASSIVE_API_KEY`).
Output: `backend/app/main.py` (a thin module — `load_dotenv()` + `app = FastAPI(lifespan=lifespan)`
+ one `@app.get("/api/health")`). Combined with Plan 01, the canonical command
`uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` runs the full shell.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@./CLAUDE.md
@backend/CLAUDE.md
@planning/PLAN.md
@.planning/phases/01-app-shell-config/01-CONTEXT.md
@.planning/phases/01-app-shell-config/01-PATTERNS.md
@.planning/codebase/CONVENTIONS.md
@backend/app/lifespan.py
@backend/app/market/stream.py

<interfaces>
<!-- Contracts main.py consumes. Do not re-derive — use these exactly. -->

From backend/app/lifespan.py (created by Plan 01):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Builds PriceCache, starts market source, mounts SSE router, stops source on exit."""
```
Import path from main.py: `from .lifespan import lifespan`

From python-dotenv (added by Plan 01 Task 1):
```python
from dotenv import load_dotenv
load_dotenv()  # No args -> finds .env walking up from CWD; silent if missing.
```

FastAPI ≥ 0.115 lifespan binding (already in project deps; see backend/pyproject.toml line 8):
```python
from fastapi import FastAPI
app = FastAPI(lifespan=lifespan)  # stdlib lifespan= parameter, NOT @app.on_event
```

Health endpoint shape (D-04, baseline from CONTEXT.md "Claude's Discretion"):
```python
@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```
The optional `"source"` enrichment is NOT included this phase — the lifespan attaches the
source AFTER the app is constructed, so reading it here would require request scope. Keep
the endpoint trivial; ops visibility is a future enhancement (CONTEXT.md "Deferred Ideas").
</interfaces>
</context>

<tasks>

<task type="auto" tdd="false">
  <name>Task 1: Create backend/app/main.py (FastAPI app + /api/health + .env loading)</name>
  <read_first>
    - backend/app/lifespan.py (contract: `from .lifespan import lifespan`)
    - backend/app/market/stream.py (FastAPI import-style and route-decorator pattern)
    - .planning/phases/01-app-shell-config/01-CONTEXT.md (D-01..D-04 — non-negotiable)
    - .planning/phases/01-app-shell-config/01-PATTERNS.md ("backend/app/main.py" section)
    - .planning/codebase/CONVENTIONS.md (`%`-style logging, no f-strings, no emojis,
      `from __future__ import annotations`, public-API imports)
    - backend/pyproject.toml (confirms fastapi >= 0.115 and python-dotenv after Plan 01)
  </read_first>
  <files>backend/app/main.py</files>
  <action>
    Create `backend/app/main.py` exactly as below. The file order is load-bearing:
    `load_dotenv()` MUST execute before `FastAPI(lifespan=lifespan)` is constructed so that
    env vars exist when uvicorn enters the lifespan and `factory.create_market_data_source`
    reads `MASSIVE_API_KEY` (factory reads env at call time — see
    `backend/app/market/factory.py:24`).

    ```python
    """FinAlly FastAPI application entrypoint."""

    from __future__ import annotations

    import logging

    from dotenv import load_dotenv
    from fastapi import FastAPI

    from .lifespan import lifespan

    # Load .env from CWD upward BEFORE the app is built, so MASSIVE_API_KEY,
    # OPENROUTER_API_KEY, and LLM_MOCK are present when the lifespan runs and the
    # factory reads them. Silent no-op if .env is absent (matches CONTEXT.md hard
    # constraint: missing values must not crash startup).
    load_dotenv()

    logger = logging.getLogger(__name__)

    app = FastAPI(lifespan=lifespan)


    @app.get("/api/health")
    async def health() -> dict[str, str]:
        """Liveness probe. Returns {"status": "ok"} with HTTP 200."""
        return {"status": "ok"}
    ```

    Constraints (D-03): There MUST NOT be an `if __name__ == "__main__":` block. The
    canonical run command is:

        cd backend
        uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

    The same command becomes the Docker `CMD` in Phase 9.

    Constraints (D-04): The SSE router is NOT included here — `lifespan` includes it during
    startup. Do NOT call `app.include_router(create_stream_router(...))` from main.py.

    Code-style (CONVENTIONS.md):
      - One-line module docstring.
      - `from __future__ import annotations` immediately after.
      - Stdlib -> third-party -> local import grouping (already shown above).
      - `%`-style logging only — never f-strings in logger calls.
      - No emojis anywhere.
      - No defensive try/except (load_dotenv is silent; FastAPI() failure should crash).
  </action>
  <verify>
    <automated>cd backend &amp;&amp; uv run --extra dev ruff check app/main.py &amp;&amp; uv run python -c "from app.main import app; from fastapi import FastAPI; assert isinstance(app, FastAPI); print(app.title)"</automated>
  </verify>
  <acceptance_criteria>
    - `backend/app/main.py` exists and `wc -l backend/app/main.py` reports >= 18 lines.
    - `grep -F 'from __future__ import annotations' backend/app/main.py` matches.
    - `grep -F 'from dotenv import load_dotenv' backend/app/main.py` matches.
    - `grep -F 'from fastapi import FastAPI' backend/app/main.py` matches.
    - `grep -F 'from .lifespan import lifespan' backend/app/main.py` matches.
    - `grep -nE '^load_dotenv\(\)' backend/app/main.py` matches; the matched line number is
      LESS than the line number reported by `grep -nE '^app\s*=\s*FastAPI\(' backend/app/main.py`
      (load_dotenv must precede app construction).
    - `grep -F 'app = FastAPI(lifespan=lifespan)' backend/app/main.py` matches.
    - `grep -F '@app.get("/api/health")' backend/app/main.py` matches.
    - `grep -E 'return\s*\{"status":\s*"ok"\}' backend/app/main.py` matches.
    - `grep -nE 'if __name__ == .__main__.:' backend/app/main.py` returns NOTHING (D-03).
    - `grep -F 'create_stream_router' backend/app/main.py` returns NOTHING (D-04 — router is
      mounted by lifespan, not here).
    - `cd backend &amp;&amp; uv run --extra dev ruff check app/main.py` exits 0.
    - `cd backend &amp;&amp; uv run python -c "from app.main import app; print(app.title)"` exits 0.
    - `cd backend &amp;&amp; uv run python -c "from app.main import app; routes=[r.path for r in app.routes]; assert '/api/health' in routes, routes"` exits 0.
  </acceptance_criteria>
  <done>
    `app.main:app` is a FastAPI instance with the Plan 01 lifespan attached and `/api/health`
    exposed. `.env` is loaded before app construction. The canonical
    `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` line works (verified end-to-end
    in Plan 03).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client (browser/curl) -> /api/health | Public unauthenticated GET endpoint with no input parameters. |
| filesystem (`.env`) -> process | `load_dotenv()` reads the developer's `.env` from CWD upward. Already gitignored. |

## STRIDE Threat Register (ASVS L1, block on `high`)

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-06 | Information Disclosure | `/api/health` response body | accept | Returns the literal string `{"status": "ok"}` only — no environment values, no version info, no hostname. ASVS L1 V14 only requires the endpoint not leak credentials or stack traces. |
| T-01-07 | Denial of Service | `/api/health` reachable without auth, single user demo | accept | No-auth-by-design (single-user local demo, see CONCERNS.md item 2). Endpoint is constant-time and stateless; no DB call, no I/O. Rate limiting is out of scope for Phase 1. |
| T-01-08 | Spoofing | `load_dotenv()` reads `.env` walking up the directory tree | accept | If an attacker can write `.env` in a parent directory they already control the workstation. `.env` is gitignored, never committed; trust boundary is the local filesystem. |
| T-01-09 | Information Disclosure | FastAPI default `/docs` and `/openapi.json` are auto-mounted by `FastAPI()` | accept | Phase 1 only adds `/api/health` and (via lifespan) `/api/stream/prices`. Both are part of the documented public API in PLAN.md §8. No internal-only routes are exposed. Disabling `/docs` is a Phase 9 packaging concern. |
| T-01-10 | Tampering | A malformed `.env` line could raise during `load_dotenv()` and crash startup | accept | `load_dotenv()` is silent on missing file and tolerant of malformed lines (skips with a warning). Crashing on truly broken local config is correct per project rule "no defensive programming". |

No `high`-severity threats. The endpoint exposes no input surface and the only filesystem
dependency (`.env`) lives inside the developer's local trust boundary.
</threat_model>

<verification>
Run from `backend/`:
- `uv run --extra dev ruff check app/main.py` (lint clean)
- `uv run python -c "from app.main import app; print(app.title)"` (importable)
- `uv run python -c "from app.main import app; assert any(r.path == '/api/health' for r in app.routes)"`
- Manual smoke (optional, covered by Plan 03 tests):
  `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 &amp;` then
  `curl -s http://127.0.0.1:8000/api/health` → `{"status":"ok"}`
</verification>

<success_criteria>
- `backend/app/main.py` exists, imports cleanly, exposes a module-level `app: FastAPI`.
- `load_dotenv()` is called BEFORE `FastAPI(lifespan=lifespan)` (verified by line number).
- `/api/health` returns 200 with body `{"status": "ok"}`.
- Lifespan from Plan 01 is bound via the `lifespan=` constructor parameter (FastAPI ≥ 0.115
  stdlib pattern).
- No `__main__` block; no SSE router mount in main.py (both per D-03/D-04).
- ruff exits 0; module importable via `from app.main import app`.
</success_criteria>

<output>
After completion, create `.planning/phases/01-app-shell-config/01-02-SUMMARY.md`.
</output>
