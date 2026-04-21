---
phase: 03-portfolio-trading-api
depth: standard
files_reviewed: 20
files_reviewed_list:
  - backend/app/lifespan.py
  - backend/app/market/interface.py
  - backend/app/market/massive_client.py
  - backend/app/market/simulator.py
  - backend/app/portfolio/__init__.py
  - backend/app/portfolio/models.py
  - backend/app/portfolio/routes.py
  - backend/app/portfolio/service.py
  - backend/tests/market/test_observer.py
  - backend/tests/portfolio/conftest.py
  - backend/tests/portfolio/test_routes_history.py
  - backend/tests/portfolio/test_routes_portfolio.py
  - backend/tests/portfolio/test_routes_trade.py
  - backend/tests/portfolio/test_service_buy.py
  - backend/tests/portfolio/test_service_history.py
  - backend/tests/portfolio/test_service_portfolio.py
  - backend/tests/portfolio/test_service_sell.py
  - backend/tests/portfolio/test_service_validation.py
  - backend/tests/portfolio/test_snapshot_observer.py
  - backend/tests/test_lifespan.py
status: issues_found
critical_count: 0
high_count: 0
medium_count: 2
low_count: 5
created: 2026-04-21T13:46:35Z
---

# Phase 03 Code Review

## Summary

Phase 03 (PORT-01..PORT-05) delivers a clean, well-tested portfolio + trading API: a pure-function service, strict Pydantic v2 schemas, a factory-closure router, a 60s snapshot observer wired through the existing market-data tick loop, and 158 passing tests. No critical or high-severity issues found. SQL is fully parameterised (no injection surface), cash/quantity math is correct including IEEE 754 residual handling, trade validation is pre-write (validate-then-write atomicity), and observer exception isolation is proven by tests. Project conventions are respected throughout: no emojis, PEP-604 types, `%`-style log formatting, `from __future__ import annotations`, short modules, narrow `except` blocks.

Two MEDIUM findings cover narrow concurrency / liveness concerns that are latent rather than demonstrated bugs (post-trade clock-reset ordering and observer loop blocking on DB work). Five LOW findings cover minor test-quality and style nits.

## Findings

### CRITICAL
None

### HIGH
None

### MEDIUM

#### MED-01: Post-trade snapshot clock reset happens AFTER the inline snapshot write, not before

**File:** `backend/app/portfolio/routes.py:40-52`, `backend/app/portfolio/service.py:183-189`
**Issue:** In `post_trade`, the flow is:

1. `service.execute_trade(...)` — writes the post-trade snapshot inside the transaction and commits.
2. Route handler sets `request.app.state.last_snapshot_at = time.monotonic()`.

Between steps 1 and 2 there is no `await`, so in single-threaded asyncio this is race-free *today*. But the invariant "inline post-trade snapshot resets the 60s clock" is encoded in two separate places (the INSERT at `service.py:183-189` and the assignment at `routes.py:52`). If a future change introduces an `await` between them (e.g. an audit-log write, a metrics publish), the tick observer can fire during the gap and emit a *second* snapshot for the same trade — duplicating a row and half-breaking the "at most one snapshot per 60s" contract.

**Fix:** Move the clock reset inside `execute_trade` at the same site as the snapshot INSERT so the snapshot write and clock reset are atomic with respect to the event loop. This also removes the FastAPI-specific reset from the route handler and centralises the invariant. Suggested shape — pass the state (or a `snapshot_writer` callback) into `execute_trade`, or return the snapshot timestamp and let a single helper in `service.py` own both the INSERT and the `state.last_snapshot_at =` assignment. If the goal of keeping `service.py` FastAPI-agnostic (D-02) must be preserved, then reset *before* calling `execute_trade` as well as after, and document the invariant inline.

Severity is MEDIUM rather than LOW because the post-trade snapshot is the only business-critical reason the clock needs to be reset and the current coupling is subtle.

---

#### MED-02: Snapshot observer runs a synchronous DB INSERT + commit on the event-loop thread every simulator tick

**File:** `backend/app/portfolio/service.py:300-333`, `backend/app/market/simulator.py:262-278`
**Issue:** `make_snapshot_observer` returns a sync closure that `state.db.execute(...)` + `state.db.commit()` on every tick where the 60s threshold passes (or on the boot-tick). The observer fires on the event-loop thread (per the D-04 contract and the comment at `simulator.py:270`). When the snapshot actually writes, it does a synchronous SQLite INSERT + `commit()` inline in the simulator loop — blocking the event loop for the duration of that disk write. On a healthy SQLite file this is sub-millisecond, but:

- On a slow filesystem (network-mounted volume, fsync contention), a single `commit()` can spike to tens of ms.
- The simulator ticks every 500 ms and the observer runs AFTER the cache write, so a slow commit delays the *next* tick and thus the SSE push cadence.
- The observer's read side (`compute_total_value`) runs a `SELECT ... FROM positions WHERE user_id = ?` — fine today with 0-10 rows, but it's on the hot path.

There is no test that exercises a slow commit; the tests all use `:memory:` SQLite.

**Fix:** Two options:

1. Offload the observer write with `asyncio.to_thread(...)` — but the current observer is a sync `Callable[[], None]`, so the source would need to support async observers, which is a larger contract change.
2. Accept the current behavior and add a docstring note on `make_snapshot_observer` stating "runs synchronous sqlite3 writes on the event loop; expected to complete in <1ms on local disk; do not run this observer against a remote or fsync-heavy volume."

Option 2 is the simpler v1 fix and matches the project's "no over-engineering" rule — log the caveat and move on.

Severity is MEDIUM because performance issues are explicitly out of v1 scope per the review rubric, but the event-loop-blocking characteristic is a *correctness-adjacent* concern (it affects SSE tick cadence, which is a user-visible contract).

---

### LOW

#### LOW-01: `test_insufficient_shares_message_contains_numbers` assertion is vacuously true

**File:** `backend/tests/portfolio/test_service_validation.py:75-81`
**Issue:** The test asserts `"10" in msg` and `"0" in msg`. The substring `"10"` already contains `"0"`, so the second assertion can never independently fail — and indeed the current message `f"Requested {quantity}, held {old_qty}"` produces `"Requested 10.0, held 0.0"`, which happens to satisfy both, but the test doesn't prove the `held` field is surfaced. If a future refactor drops `held` entirely the test still passes as long as `10` appears anywhere.
**Fix:** Tighten the assertion:

```python
assert "10" in msg
assert "held 0" in msg  # or: assert "held" in msg
```

---

#### LOW-02: `execute_trade` re-reads position row then derives `pos_row is None` to choose INSERT vs UPDATE, but this branch overlaps with the epsilon-delete branch

**File:** `backend/app/portfolio/service.py:151-174`
**Issue:** The `if abs(new_qty) < _ZERO_QTY_EPSILON` branch runs a `DELETE ... WHERE user_id = ? AND ticker = ?`. If `pos_row is None` (no row existed) *and* `new_qty` rounds to zero (which can only happen when `quantity == 0` — but Pydantic enforces `Field(gt=0)`, so this is unreachable), the DELETE would be a no-op. So the branch is well-behaved, but the overlap is non-obvious. Adding a short comment would help future readers, or collapse to: `if pos_row is not None and abs(new_qty) < _EPSILON: DELETE` — the `pos_row is not None` guard is defensively identical because an INSERT branch can never reach an epsilon-delete-worthy quantity.
**Fix:** Add a one-line comment above the DELETE:

```python
# DELETE is a no-op when pos_row is None (can't happen given Field(gt=0), but kept for clarity).
```

---

#### LOW-03: Observer sentinel `last_snapshot_at == 0.0` is fragile against `time.monotonic() -> 0.0`

**File:** `backend/app/portfolio/service.py:314-318`
**Issue:** The boot-time special case uses `state.last_snapshot_at != 0.0` as a "has-it-run-once" sentinel. If, in a test environment, `time.monotonic()` is patched to return `0.0` (unlikely but legal), the first tick writes a snapshot and sets `state.last_snapshot_at = 0.0` — the *next* tick then re-enters the boot branch and writes a second snapshot. Repeats forever.

In production `time.monotonic()` is never 0 after boot, so this is a latent test-only issue, but a cleaner pattern is a `bool` flag:

```python
state.snapshot_observer_ever_fired = False  # set in lifespan
...
if not state.snapshot_observer_ever_fired or now - state.last_snapshot_at >= 60.0:
    # write snapshot
    state.snapshot_observer_ever_fired = True
    state.last_snapshot_at = now
```

Or keep the float but use a distinguishable sentinel like `float("-inf")` instead of `0.0`.
**Fix:** Either switch the sentinel to `-inf` (one-line change) or add a dedicated boolean flag.

---

#### LOW-04: `TradeRequest.ticker` has a `max_length=10` bound but no character-class validation

**File:** `backend/app/portfolio/models.py:19`
**Issue:** `ticker: str = Field(min_length=1, max_length=10)` accepts any characters including whitespace, digits only, or Unicode symbols. `execute_trade` does `ticker.strip().upper()` then does a watchlist lookup — any non-uppercase-ASCII input would simply miss the watchlist and raise `UnknownTicker`, so there is no injection or crash risk. But a `pattern=r"^[A-Za-z]{1,10}$"` would reject the garbage earlier with a 422 and a more useful error, and matches the spirit of the spec (US-equities watchlist).
**Fix:** Add a pattern constraint:

```python
ticker: str = Field(min_length=1, max_length=10, pattern=r"^[A-Za-z]{1,10}$")
```

Not required for correctness, but improves the 422 error surface for frontend/LLM callers.

---

#### LOW-05: Test fixture `db_path` is referenced but not imported/defined within `tests/portfolio/`

**File:** `backend/tests/portfolio/test_routes_history.py`, `test_routes_portfolio.py`, `test_routes_trade.py`, `test_snapshot_observer.py` (parameter `db_path` across many tests)
**Issue:** The `db_path` fixture is defined in `backend/tests/conftest.py` at the top level. This works because pytest auto-discovers conftest up the directory tree. No actual bug — but anyone reading a single test file in isolation sees a fixture parameter with no visible source. A short docstring or import-only-for-doc reference in `tests/portfolio/conftest.py` would help. Acceptable as-is per pytest idiom; flagging only for grep-ability.
**Fix:** None required. Optionally add a comment in `tests/portfolio/conftest.py`:

```python
# db_path fixture is inherited from backend/tests/conftest.py (pytest auto-discovery).
```

---

## Positive Observations

- **SQL is fully parameterised.** Every `conn.execute(...)` passes user-controllable inputs as a parameter tuple. Ticker values that reach SQL (e.g. `execute_trade`, watchlist lookup) are uppercased/stripped before binding, further narrowing the surface. Zero injection risk.
- **Validate-then-write with single-commit atomicity.** `execute_trade` raises on every failure path *before* any write, and the four writes (cash, position, trade, snapshot) all live inside sqlite3's implicit transaction with exactly one `conn.commit()`. Proven by `test_service_validation.py` snapshot-before/after counts.
- **Epsilon-delete for IEEE 754 residuals.** `abs(new_qty) < 1e-9` correctly handles the classic `0.1 + 0.2 - 0.3` case without leaving ghost zero-quantity rows. Proven by `test_full_sell_epsilon_handles_float_residual`.
- **Observer exception isolation is tested end-to-end.** `test_raising_observer_does_not_kill_tick_loop` in `test_snapshot_observer.py` spins up a real FastAPI lifespan, registers a raising observer alongside a flag-setter, waits for a real simulator tick, and asserts both that the flag fires and that the simulator task is still running. Combined with the per-callback `try/except` in both `simulator.py:271-275` and `massive_client.py:120-124`, the D-08 contract is solid.
- **Pydantic v2 idioms are correct throughout.** `ConfigDict(extra="forbid")` on `TradeRequest` only (requests strict, responses lenient for additive evolution), `Literal["buy","sell"]`, `Field(gt=0)`, PEP-604 types, no `Optional`, no `class Config`.
- **FastAPI idioms are on-pattern.** `create_portfolio_router(db, cache)` is a factory closure mirroring `create_stream_router` — no module-level router state, no globals. Domain exception → HTTP 400 translation lives in exactly one place (`routes.py:44-48`). `Query(default=1000, ge=1, le=1000)` bounds the limit param with server-side 422 rejection.
- **Project conventions honoured.** No emojis anywhere. All logs use `%`-style placeholders (e.g. `logger.info("Trade executed: %s %s x %.4f @ %.2f (cash=%.2f)", ...)`). Every module has `from __future__ import annotations` and a one-line docstring. `Callable` imported from `collections.abc`, not `typing`. Short modules (service.py is ~330 lines; routes.py is 62). No `try/except` outside the narrow, documented sites (massive poll, simulator loop, observer firing, domain-exception → HTTP).
- **Tests are comprehensive and well-structured.** 27 service unit tests + 15 route integration tests + 6 observer tests + 3 lifespan tests + 6 market observer tests. Uses the `fresh_db` + `warmed_cache` fixtures from `conftest.py`, avoids test-pollution by building a fresh FastAPI app per test, and asserts the validate-then-write invariant with before/after snapshots (e.g. `test_insufficient_cash` at `test_routes_trade.py:128-141`).
- **Ruff clean, 100% coverage on `app/portfolio/`.** Documented in `03-03-SUMMARY.md`.

---

_Reviewed: 2026-04-21T13:46:35Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
