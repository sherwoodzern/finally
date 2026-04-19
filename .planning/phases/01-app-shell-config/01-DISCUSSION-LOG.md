# Phase 1: App Shell & Config - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution
> agents. Decisions are captured in `01-CONTEXT.md` — this log preserves the
> alternatives considered.

**Date:** 2026-04-19
**Phase:** 01-app-shell-config
**Areas discussed:** Module & entrypoint layout

---

## Gray Area Selection

| Area | Description | Selected |
|------|-------------|----------|
| Module & entrypoint layout | Where `app.main:app` lives; file split; uvicorn invocation | ✓ |
| Config / .env loading | python-dotenv vs pydantic-settings vs manual os.environ; .env location; missing-value behavior | |
| Startup ticker source | What `source.start(tickers)` receives before the DB exists | |
| SSE end-to-end verification | How APP-04 "real browser receives ticks" is proven in Phase 1 | |

**User's choice:** Only "Module & entrypoint layout" selected. The remaining
three areas fall to Claude's Discretion under standard practice during
planning.

---

## Module & Entrypoint Layout

### Q1: How should the shell be laid out inside `backend/app/`?

| Option | Description | Selected |
|--------|-------------|----------|
| Single `main.py` (Recommended) | One file holds app, lifespan, routes, startup glue | |
| Split: main.py + lifespan.py | main.py builds app and mounts routers; lifespan.py owns PriceCache + data source lifecycle | ✓ |
| Split: main.py + lifespan.py + config.py | As above, plus a dedicated Settings module | |

**User's choice:** Split into `main.py` + `lifespan.py`.
**Notes:** Rejected the single-file recommendation as too cramped for later
phases, and the three-file split as premature for a 3-requirement phase.

### Q2: Where is the shared `PriceCache` instantiated?

| Option | Description | Selected |
|--------|-------------|----------|
| Inside lifespan, stored on `app.state` (Recommended) | Built on startup, attached as `app.state.price_cache`, stopped on shutdown | ✓ |
| Module-level singleton in main.py | `price_cache = PriceCache()` at import time | |

**User's choice:** Inside lifespan, attached to `app.state.price_cache`.
**Notes:** Recommended default accepted.

### Q3: How is uvicorn invoked?

| Option | Description | Selected |
|--------|-------------|----------|
| CLI only (Recommended) | `uv run uvicorn app.main:app ...`; no `__main__` block | ✓ |
| CLI + `__main__` convenience block | CLI canonical, but `if __name__ == "__main__"` also works | |
| You decide | Delegate to Claude | |

**User's choice:** CLI only.
**Notes:** Recommended default accepted; keeps one canonical invocation shared
with Phase 9's Docker `CMD`.

### Q4: How are routers wired into the app?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline in lifespan-aware main.py (Recommended) | `app.include_router(create_stream_router(cache))`; `/api/health` inline | ✓ |
| Dedicated health router file | `backend/app/health.py` as an APIRouter | |

**User's choice:** Inline in `main.py`.
**Notes:** Recommended default accepted.

---

## Claude's Discretion

The user selected only one gray area, deferring the following to standard
practice during planning:

- Config / `.env` loading (loader choice, file location, missing-value policy)
- Startup ticker source (likely `SEED_PRICES.keys()` from
  `backend/app/market/seed_prices.py`)
- SSE end-to-end verification strategy (likely httpx smoke fixture + manual
  curl; full Playwright deferred to Phase 10)
- Health endpoint shape (baseline `{"status": "ok"}`; optional source-type
  field)
- Missing `OPENROUTER_API_KEY` policy (warn and continue; Phase 5 fails fast)

## Deferred Ideas

- `.env.example` at repo root (formally Phase 9 / OPS-04; README already
  references it)
- SSE heartbeat / keepalive (architectural risk noted in CONCERNS.md; not a
  localhost-demo blocker)
- Enriched `/api/health` with source-type (tangential to phase goal)
