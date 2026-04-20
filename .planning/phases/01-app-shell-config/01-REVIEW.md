---
phase: 01-app-shell-config
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/app/lifespan.py
  - backend/app/main.py
  - backend/app/market/stream.py
  - backend/tests/test_lifespan.py
  - backend/tests/test_main.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 1: Code Review Report

**Reviewed:** 2026-04-19T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Phase 1 delivers the FastAPI app shell: `lifespan.py` wires `PriceCache` + market
data source + SSE router; `main.py` is a thin entry with `/api/health`;
`stream.py` is factored to return a fresh router per call; two test modules
exercise lifecycle and end-to-end SSE over a real uvicorn socket.

Code quality is high overall and adheres to project conventions (relative
imports, `%`-style log formatting, no emojis, no defensive try/except, short
modules). No security issues found — the single-user, no-auth design is
consistent with `PLAN.md §2`, and there is no injection, SSRF, or eval-class
surface.

Two warnings concern router lifecycle and test hygiene around an
already-mitigated shared-state hazard. Four info items flag minor convention
drift and an async-cancellation anti-pattern that is currently benign but
worth correcting before Phase 2 adds more SSE consumers.

## Warnings

### WR-01: Router added in lifespan startup is never removed on shutdown

**File:** `backend/app/lifespan.py:44`
**Issue:** `app.include_router(create_stream_router(cache))` runs during
lifespan startup and mutates `app.router.routes`, but the matching `finally`
block only calls `await source.stop()` — it does not remove the route. If the
same `FastAPI` instance ever re-enters its lifespan (e.g. a test reusing
`app.main.app`, or any future framework hook that restarts lifespan),
`/api/stream/prices` will be appended again, stacking duplicate routes. The
earliest-registered route always wins dispatch and closes over a
`PriceCache` from a prior, stopped source — serving requests against a dead
cache whose `version` never advances (this is precisely the failure mode
`test_main.py` documents at lines 14-20 and works around by building a fresh
app per test).

The normal FastAPI idiom is to include routers at app construction time, not
inside `lifespan`. Moving router inclusion to `main.py` (where the app is
built) removes the re-entry risk and aligns with the factory pattern already
used by `create_stream_router`.

**Fix:** Include the router at app-build time and pass the cache in via
`app.state` after startup. Either (a) construct the cache eagerly at module
scope before `FastAPI(lifespan=...)`, or (b) keep the router factory but have
it look up the cache from the request:

```python
# backend/app/main.py
from .lifespan import lifespan
from .market import create_stream_router

app = FastAPI(lifespan=lifespan)

@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

# Router added once at import time, reads cache from request.app.state
# inside the handler (requires a small refactor in create_stream_router to
# accept `Request` and pull cache = request.app.state.price_cache).
app.include_router(create_stream_router_from_state())
```

Then drop the `app.include_router(...)` line from `lifespan.py`. This also
lets `test_main.py` go back to using `app.main.app` and removes the `_build_app`
duplication.

---

### WR-02: `test_main.py` module docstring misattributes the shared-state bug

**File:** `backend/tests/test_main.py:14-20`
**Issue:** The docstring states that "`app/market/stream.py` holds a
module-level APIRouter that accumulates `/prices` routes across
`create_stream_router` calls." Reading the current `stream.py`, that is not
true — `create_stream_router` constructs a fresh `APIRouter` per call (lines
29, plus the explicit docstring at 22-28 calling out the fix). The real cause
of the shared-state failure is `lifespan.py:44` calling `app.include_router`
on the shared `app.main.app`, which mutates `app.router.routes`
(see WR-01).

This is load-bearing comment drift: a future reader will grep `stream.py` for
a module-level router, fail to find one, assume the comment is stale in a
different way, and potentially revert the `_build_app` workaround — then hit
the real bug (router accumulation on `app.router.routes`) with a misleading
mental model.

**Fix:** Update the docstring to name the correct location:

```python
"""...
Each test builds a fresh FastAPI(lifespan=lifespan) via _build_app() instead of
importing the module-level app.main.app. Reason: app/lifespan.py calls
app.include_router(create_stream_router(cache)) during startup and does not
remove the route on shutdown, so a shared app accumulates /api/stream/prices
routes across lifespans. Each stacked route closes over a PriceCache from a
torn-down source whose version never advances; Starlette dispatches the
earliest match, so the second streaming request gets served by the stale
route and the read times out. Fresh app per test sidesteps that shared-state
bug until WR-01 is fixed.
"""
```

Once WR-01 is fixed this workaround (and its docstring) should be removed
entirely.

## Info

### IN-01: `SEED_PRICES` imported from deep module path, not the public API

**File:** `backend/app/lifespan.py:12`
**Issue:** `from .market.seed_prices import SEED_PRICES` reaches into a
non-exported submodule. `app/market/__init__.py` defines an explicit `__all__`
that does not include `SEED_PRICES`, and the project convention (CLAUDE.md
"Market-data public API is re-exported from app.market — import from there,
not deep paths") says to use the package's surface. `lifespan.py` already
follows that rule for `PriceCache`, `create_market_data_source`, and
`create_stream_router` on line 11 — the seed-prices import is the odd one out.

This is also flagged in `01-CONTEXT.md` as the single source of truth that
Phase 2's DB-backed watchlist will replace. Either re-export it or leave a
TODO referencing the Phase 2 swap.

**Fix:** Re-export `SEED_PRICES` (or better, a `get_default_tickers()` helper
to hide the dict) through `app/market/__init__.py`:

```python
# app/market/__init__.py
from .seed_prices import SEED_PRICES
__all__ = [..., "SEED_PRICES"]
```

Then `from .market import SEED_PRICES` in `lifespan.py`.

---

### IN-02: `stream.py` swallows `asyncio.CancelledError` instead of re-raising

**File:** `backend/app/market/stream.py:91-93`
**Issue:** The async generator catches `CancelledError`, logs, and returns
normally. Per Python 3.8+ asyncio guidance (and PEP 479 interactions with
generators), `CancelledError` should be re-raised after cleanup so the
framework sees the cancellation. Silent swallowing is currently benign for a
StreamingResponse (Starlette will close the stream either way), but it is an
anti-pattern that can mask bugs if this generator is ever composed with
`asyncio.wait_for`, `asyncio.TaskGroup`, or moved behind a middleware that
relies on cancellation propagation.

**Fix:**

```python
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
        raise
```

---

### IN-03: `test_lifespan.py` missing `from __future__ import annotations`

**File:** `backend/tests/test_lifespan.py:1`
**Issue:** Project convention (CLAUDE.md "Every module uses
`from __future__ import annotations`") is applied consistently in
`app/` modules and in `tests/test_main.py:23`, but not here. Minor stylistic
drift, no functional impact on Python 3.12.

**Fix:** Add `from __future__ import annotations` immediately after the
module docstring:

```python
"""Async lifecycle tests for the FastAPI app shell lifespan."""

from __future__ import annotations

import logging
import os
...
```

---

### IN-04: `source.start()` happens before `app.state` is populated

**File:** `backend/app/lifespan.py:40-43`
**Issue:** The startup sequence awaits `source.start(tickers)` on line 40,
then assigns `app.state.price_cache` / `app.state.market_source` on
lines 42-43. If `source.start` raises (e.g. Massive API rejects the key), the
source is constructed and potentially partially-started but never reachable
via `app.state`, and the `finally` block on line 54 still calls
`source.stop()` — which is safe today because `SimulatorDataSource.stop`
guards on `self._task` (simulator.py:233), but relies on every future source
implementation honoring the same "stop is safe before successful start"
contract.

Current behavior is correct; this is a robustness note for future source
implementations and Phase 2 changes.

**Fix:** Attach to `app.state` immediately after construction, before
starting, so a partially-started source is still introspectable on failure:

```python
cache = PriceCache()
source = create_market_data_source(cache)
app.state.price_cache = cache
app.state.market_source = source

tickers = list(SEED_PRICES.keys())
await source.start(tickers)
app.include_router(create_stream_router(cache))
```

---

_Reviewed: 2026-04-19T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
