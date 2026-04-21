---
phase: 03-portfolio-trading-api
plan: 01
subsystem: api
tags: [market-data, observer-pattern, asyncio, abc, pytest-asyncio]

# Dependency graph
requires:
  - phase: 01-app-shell
    provides: SimulatorDataSource/MassiveDataSource wired into lifespan with PriceCache
  - phase: 02-database
    provides: nothing needed directly (this plan is interface-only)
provides:
  - MarketDataSource.register_tick_observer(callback) abstract method
  - SimulatorDataSource observer list + _run_loop firing site with exception isolation
  - MassiveDataSource observer list + _poll_once firing site with exception isolation
  - Observer callback contract (zero-arg, event-loop thread, non-fatal exceptions)
affects: [03-02, 03-03, portfolio, snapshots]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tick-observer callback list on the producer; zero-arg, synchronous"
    - "Per-callback nested try/except at the loop boundary (D-08 isolation)"

key-files:
  created:
    - backend/tests/market/test_observer.py
  modified:
    - backend/app/market/interface.py
    - backend/app/market/simulator.py
    - backend/app/market/massive_client.py

key-decisions:
  - "D-04 implementation: register_tick_observer is synchronous, zero-arg, fires on event-loop thread"
  - "D-08 implementation: per-callback nested try/except + logger.exception; observer exceptions never kill the loop"
  - "Observer firing placed AFTER cache writes and BEFORE the outer try/except boundary so it benefits from both inner isolation (per-callback) and outer loop resilience"
  - "Massive observer fires only on successful poll (inside the try, after the debug log) — a failed poll does NOT fire observers"

patterns-established:
  - "Observer registration: `source.register_tick_observer(cb)` appends to `self._observers: list[Callable[[], None]]`"
  - "Observer firing loop: `for cb in self._observers: try: cb() except Exception: logger.exception('Tick observer raised')`"
  - "Concurrency contract documented in ABC docstring (event loop thread, NOT Polygon worker thread)"

requirements-completed:
  - PORT-05

# Metrics
duration: 4m 9s
completed: 2026-04-21
---

# Phase 03 Plan 01: MarketDataSource Tick-Observer Extension Summary

**Added a zero-arg register_tick_observer hook to MarketDataSource with concrete implementations in SimulatorDataSource and MassiveDataSource, wired with per-callback exception isolation so a broken observer cannot kill the tick/poll loop.**

## Performance

- **Duration:** 4m 9s
- **Started:** 2026-04-21T12:58:53Z
- **Completed:** 2026-04-21T13:03:02Z
- **Tasks:** 4
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `MarketDataSource` ABC now declares `register_tick_observer(callback: Callable[[], None]) -> None` as the 6th abstract method, with a docstring that locks in the event-loop-thread concurrency contract (D-04) and the non-fatal-observer guarantee (D-08).
- `SimulatorDataSource._run_loop` fires registered observers after each tick's cache writes, with a nested per-callback try/except that logs via `logger.exception("Tick observer raised")`.
- `MassiveDataSource._poll_once` fires observers after a successful poll (inside the outer try, after the debug log), with the same per-callback isolation. A failed fetch does NOT fire observers.
- 6 new observer tests cover: ABC abstractness, simulator single-observer firing, simulator multi-observer firing, simulator exception isolation, Massive successful-poll firing, Massive exception isolation.
- Zero regressions: full backend test suite stays green (107 passed).

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 observer test stubs** - `a984d41` (test)
2. **Task 2: ABC register_tick_observer abstract method** - `193cce9` (feat)
3. **Task 3: SimulatorDataSource observer implementation** - `b76e4ec` (feat)
4. **Task 4: MassiveDataSource observer implementation** - `1d7c1d0` (feat)

_All four tasks used TDD (RED stubs → GREEN impl + tests). Task 1 created the RED stubs for all three test classes up front; Tasks 2/3/4 each filled in their class while simultaneously landing the implementation._

## Files Created/Modified

- `backend/app/market/interface.py` — added `from collections.abc import Callable` and a 6th `@abstractmethod` `register_tick_observer(self, callback: Callable[[], None]) -> None` with a docstring that documents the event-loop-thread contract and the non-raising invariant.
- `backend/app/market/simulator.py` — added `from collections.abc import Callable`, initialized `self._observers: list[Callable[[], None]] = []` in `__init__`, appended a per-callback observer-firing block inside `_run_loop` after the cache-write inner loop, and added `def register_tick_observer(self, callback)` appending to `self._observers`.
- `backend/app/market/massive_client.py` — added `from collections.abc import Callable`, initialized `self._observers: list[Callable[[], None]] = []` in `__init__`, appended observer firing in `_poll_once` after the debug log (still inside the outer try so it runs only on successful polls), and added `def register_tick_observer(self, callback)` appending to `self._observers`.
- `backend/tests/market/test_observer.py` (new) — `TestABC` (synchronous, asserts incomplete subclasses cannot instantiate), `TestSimulator` (three async tests: fires on tick, multiple observers, exception isolation), `TestMassive` (two async tests: fires after successful poll, exception isolation).

## Decisions Made

- **D-04 realized as `Callable[[], None]`** from `collections.abc` (Python 3.9+ stdlib) — NOT `typing.Callable`, matching the project convention and PATTERNS.md guidance.
- **D-08 realized as nested try/except** — each callback invocation is wrapped individually so a raising callback does not short-circuit subsequent observers. This is proved by `test_observer_exception_does_not_kill_loop` (Simulator) and `test_observer_exception_isolation` (Massive): both assert that the non-raising sibling still fires.
- **Observer firing placement**:
  - Simulator: after the `for ticker, price in prices.items(): self._cache.update(...)` block, still inside the outer `try` (so the outer "Simulator step failed" catch is a second line of defense).
  - Massive: after the `logger.debug("Massive poll: updated ...")` line, still inside the outer `try` — meaning observers do NOT fire on a failed poll (deliberate; a failed fetch should not trigger a snapshot write).
- **Concurrency proof documented inline**: both observer loops have the comment `# Fires on event loop thread, NOT Polygon worker - see D-04` so a future reader doesn't accidentally move observer invocation inside `asyncio.to_thread`.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — this plan is a pure in-process interface extension with no external dependencies or service configuration.

## Next Phase Readiness

- **03-02 (portfolio service + models + router)** is unblocked: its files do not depend on this plan's output, so 03-02 can proceed independently.
- **03-03 (lifespan wiring + integration tests)** is directly unblocked: it calls `source.register_tick_observer(make_snapshot_observer(app.state))` in `lifespan.py` to wire the 60-second snapshot observer onto the existing price-update loop (PLAN.md §7, PORT-05). The interface exists and both implementations honor it; 03-03 can now register its observer and rely on the per-callback exception isolation.
- No blockers. No concerns.

## Self-Check: PASSED

Verification of all claims:

- `backend/app/market/interface.py` — FOUND (contains `register_tick_observer`, 6 `@abstractmethod` markers)
- `backend/app/market/simulator.py` — FOUND (contains `self._observers`, `for cb in self._observers`, `Tick observer raised`, `register_tick_observer`)
- `backend/app/market/massive_client.py` — FOUND (contains `self._observers`, `for cb in self._observers`, `Tick observer raised`, `register_tick_observer`)
- `backend/tests/market/test_observer.py` — FOUND (contains TestABC, TestSimulator, TestMassive classes; 6 tests pass)
- Commit `a984d41` (test stubs) — FOUND in git log
- Commit `193cce9` (ABC method) — FOUND in git log
- Commit `b76e4ec` (simulator impl) — FOUND in git log
- Commit `1d7c1d0` (massive impl) — FOUND in git log
- `cd backend && uv run --extra dev pytest tests/market/test_observer.py -q` → 6 passed
- `cd backend && uv run --extra dev pytest tests/market -q` → 79 passed (73 existing + 6 new)
- `cd backend && uv run --extra dev pytest -q` → 107 passed (no regressions)

---
*Phase: 03-portfolio-trading-api*
*Completed: 2026-04-21*
