---
phase: 02
plan: 03
type: execute
wave: 2
depends_on: ["02-01"]
files_modified:
  - backend/market_data_demo.py
  - backend/tests/db/test_demo_refactor.py
autonomous: true
requirements:
  - DB-02
tags:
  - cleanup
  - seed-truth
  - backend
  - demo
must_haves:
  truths:
    - "`backend/market_data_demo.py` no longer declares its own hardcoded `TICKERS = ['AAPL', ..., 'NFLX']` list — the demo uses `SEED_PRICES.keys()` as the single source of truth."
    - "Running `uv run market_data_demo.py` still streams live prices for the same 10 default tickers (behavior unchanged)."
    - "A trivial test asserts `set(market_data_demo.TICKERS) == set(SEED_PRICES)` so the CONCERNS.md #9 drift risk stays closed."
  artifacts:
    - path: backend/market_data_demo.py
      provides: "Demo script using `list(SEED_PRICES.keys())` as its ticker list (D-06)"
      contains: "TICKERS = list(SEED_PRICES.keys())"
    - path: backend/tests/db/test_demo_refactor.py
      provides: "Regression test pinning the demo's ticker list to SEED_PRICES"
      contains: "set(market_data_demo.TICKERS) == set(SEED_PRICES)"
  key_links:
    - from: backend/market_data_demo.py
      to: backend/app/market/seed_prices.py
      via: "`TICKERS = list(SEED_PRICES.keys())`"
      pattern: "TICKERS = list\\(SEED_PRICES\\.keys\\(\\)\\)"
    - from: backend/tests/db/test_demo_refactor.py
      to: backend/market_data_demo.py
      via: "imports `TICKERS` and asserts equivalence to `SEED_PRICES`"
      pattern: "from market_data_demo import TICKERS"
---

<objective>
Close the last remaining copy of the default-watchlist ticker list per decision D-06. The demo script currently hardcodes a parallel `TICKERS = ["AAPL", "GOOGL", ..., "NFLX"]` list on line 30 of `backend/market_data_demo.py`; this plan replaces it with `list(SEED_PRICES.keys())` (which is already imported at line 23) and adds a one-liner test so the drift cannot re-emerge silently.

Purpose: Land the cosmetic cleanup the CONCERNS.md #9 risk called for and that CONTEXT.md D-06 explicitly locks, while we are already editing the area in Phase 2. The demo is not runtime code, but keeping it synchronized means future contributors never see two conflicting "default" lists.

Output:
- One-line edit to `backend/market_data_demo.py` (drops hardcoded list + comment change).
- New test file `backend/tests/db/test_demo_refactor.py` that imports the demo module and asserts equivalence.

Design lock-ins:
- The EXISTING import `from app.market.seed_prices import SEED_PRICES` at `backend/market_data_demo.py:23` is REUSED — no new imports needed.
- `list(SEED_PRICES.keys())` preserves the insertion-ordered 10-ticker list Python 3.7+ guarantees.
- This plan runs in parallel with Plan 02 (Wave 2, no overlap in files_modified).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-database-foundation/02-CONTEXT.md
@.planning/phases/02-database-foundation/02-RESEARCH.md
@.planning/phases/02-database-foundation/02-PATTERNS.md
@.planning/codebase/CONCERNS.md
@backend/market_data_demo.py
@backend/app/market/seed_prices.py
@backend/CLAUDE.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Replace hardcoded TICKERS with list(SEED_PRICES.keys()) + add regression test</name>
  <files>backend/market_data_demo.py, backend/tests/db/test_demo_refactor.py</files>
  <read_first>
    - backend/market_data_demo.py (lines 22-30 — the target; lines 75, 181, 213, 222, 243 for downstream uses of `TICKERS`)
    - backend/app/market/seed_prices.py (source of truth — `SEED_PRICES` dict)
    - .planning/phases/02-database-foundation/02-CONTEXT.md §"D-06"
    - .planning/phases/02-database-foundation/02-PATTERNS.md §"backend/market_data_demo.py (MODIFIED, D-06)"
    - .planning/codebase/CONCERNS.md §"Code-Level Concerns" item 9
  </read_first>
  <behavior>
    - `backend/market_data_demo.py` imports `SEED_PRICES` once (already does) and uses it as the source for `TICKERS`.
    - No other module changes; downstream code iterating `TICKERS` at lines 75/181/213/222/243 continues to operate unchanged because `list[str]` is iteration-compatible.
    - A new test module `backend/tests/db/test_demo_refactor.py` imports `TICKERS` from the demo module and asserts `set(TICKERS) == set(SEED_PRICES)` and `len(TICKERS) == 10`.
  </behavior>
  <action>
### Step 1 — Edit `backend/market_data_demo.py`

Locate the block at lines 29-30:

```python
# Ordered ticker list matching the default watchlist
TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
```

Replace ONLY those two lines with:

```python
# Ordered ticker list matching the default watchlist (source of truth: SEED_PRICES)
TICKERS = list(SEED_PRICES.keys())
```

Do not change ANY other line in the file. The existing import `from app.market.seed_prices import SEED_PRICES` at line 23 already makes `SEED_PRICES` available.

### Step 2 — Create `backend/tests/db/test_demo_refactor.py`

Create this new test file (the `backend/tests/db/__init__.py` package marker was created in Plan 01):

```python
"""Regression: market_data_demo.TICKERS is derived from SEED_PRICES (D-06)."""

from app.market.seed_prices import SEED_PRICES


class TestDemoTickerList:
    """Pin the demo's ticker list to the canonical SEED_PRICES dict."""

    def test_demo_tickers_match_seed_prices(self):
        """market_data_demo.TICKERS must equal list(SEED_PRICES.keys()).

        Closes CONCERNS.md #9 — preventing a future drift where the demo
        has tickers that don't appear in the DB watchlist seed (or vice versa).
        """
        import market_data_demo

        assert set(market_data_demo.TICKERS) == set(SEED_PRICES)
        assert len(market_data_demo.TICKERS) == 10
        # list() of a dict's keys preserves insertion order in Python 3.7+.
        assert market_data_demo.TICKERS == list(SEED_PRICES.keys())
```

Note on import-ability: the existing `backend/pyproject.toml` and the project's pytest rootdir configuration make `market_data_demo` importable from `backend/` (the same way `uv run market_data_demo.py` works). If `import market_data_demo` fails at collection time, verify that `cd backend && uv run --extra dev python -c "import market_data_demo"` works at the shell — that is the reference command. This is not expected to fail; the demo module is already sitting at `backend/market_data_demo.py` next to `pyproject.toml`.

### Step 3 — Run the test

```bash
cd backend && uv run --extra dev pytest tests/db/test_demo_refactor.py -v
```

Expect: 1 test passing.

### Step 4 — Smoke check the demo still imports cleanly

```bash
cd backend && uv run --extra dev python -c "import market_data_demo; print(market_data_demo.TICKERS)"
```

Expect: the same 10 tickers `['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX']`.
  </action>
  <verify>
    <automated>cd backend && uv run --extra dev pytest tests/db/test_demo_refactor.py -v</automated>
    <automated>cd backend && uv run --extra dev python -c "import market_data_demo; assert market_data_demo.TICKERS == ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'], market_data_demo.TICKERS"</automated>
    <automated>cd backend && uv run --extra dev ruff check market_data_demo.py tests/db/</automated>
  </verify>
  <acceptance_criteria>
    - `backend/market_data_demo.py` contains the literal line `TICKERS = list(SEED_PRICES.keys())` (grep-verifiable: `grep -c "TICKERS = list(SEED_PRICES.keys())" backend/market_data_demo.py` returns `1`).
    - `backend/market_data_demo.py` does NOT contain the hardcoded ticker string list — grep-verifiable: `grep -c 'TICKERS = \["AAPL"' backend/market_data_demo.py` returns `0`.
    - `backend/tests/db/test_demo_refactor.py` exists and contains `set(market_data_demo.TICKERS) == set(SEED_PRICES)`.
    - `cd backend && uv run --extra dev pytest tests/db/test_demo_refactor.py -v` exits 0 with 1 passing test.
    - `cd backend && uv run --extra dev python -c "import market_data_demo; assert market_data_demo.TICKERS == list(__import__('app.market.seed_prices', fromlist=['SEED_PRICES']).SEED_PRICES.keys())"` exits 0.
    - `cd backend && uv run --extra dev ruff check market_data_demo.py tests/db/` exits 0.
    - The file diff of `backend/market_data_demo.py` is limited to lines 29-30 (verify with `git diff --stat backend/market_data_demo.py` showing a ~2-line change).
  </acceptance_criteria>
  <done>Demo ticker list is derived from `SEED_PRICES`. Regression test prevents re-drift. Demo still imports cleanly.</done>
</task>

</tasks>

<verification>
## Plan-level verification

After the task completes:

1. `cd backend && uv run --extra dev pytest tests/db/ -v` — `test_demo_refactor.py` passes alongside Plan 01's tests.
2. `cd backend && uv run --extra dev pytest -v` — full suite green (this plan is strictly additive; no pre-existing test is affected).
3. `grep -rn '"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"' backend/` returns ONE remaining place only: none in source/tests — the only hardcoded copy that remains is inside `backend/tests/` (if any) or docs. In `backend/` production/demo/test code, the only ticker-list source should be `SEED_PRICES`. Expect `grep` count `0` across `backend/app/` and `backend/market_data_demo.py`.

## Must-haves cross-check

- ✓ Single source of truth — `TICKERS = list(SEED_PRICES.keys())` in the demo.
- ✓ Pinned by regression test — `test_demo_tickers_match_seed_prices`.
- ✓ Demo still runs — smoke import verifies module loads.
</verification>

<success_criteria>
- `backend/market_data_demo.py` derives its `TICKERS` from `SEED_PRICES.keys()`.
- `backend/tests/db/test_demo_refactor.py` passes and is included in the project's pytest collection.
- CONCERNS.md #9 drift risk is closed.
- Full pytest suite remains green (no regressions).
</success_criteria>

<output>
After completion, create `.planning/phases/02-database-foundation/02-03-SUMMARY.md` using the summary template.
</output>
