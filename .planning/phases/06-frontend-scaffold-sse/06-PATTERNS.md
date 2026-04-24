# Phase 06: Frontend Scaffold & SSE — Pattern Map

**Mapped:** 2026-04-23
**Files analyzed:** 17 new, 0 modified
**Analogs found:** 7 conceptual (backend cross-language) / 17
**Note:** `frontend/` does not yet exist. Most files are net-new TypeScript/Next.js artifacts with no in-repo analog. The planner should lift templates **verbatim from RESEARCH.md §Implementation Templates 1-14**. Where the backend offers a **conceptual analog** (same responsibility in Python), the pattern + translation is given below.

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `frontend/package.json` | config | build-time | — | RESEARCH §1 |
| `frontend/next.config.mjs` | config | build-time + dev proxy | — | RESEARCH §2 |
| `frontend/postcss.config.mjs` | config | build-time | — | RESEARCH §3 |
| `frontend/tsconfig.json` | config | build-time | — | create-next-app default |
| `frontend/.eslintrc.json` | config | lint-time | — | create-next-app default |
| `frontend/.gitignore` | config | VCS | — | create-next-app default |
| `frontend/README.md` | docs | — | `backend/README.md` (concise, dev quick-start) | style-match |
| `frontend/vitest.config.mts` | config | test-time | `backend/pyproject.toml` `[tool.pytest.ini_options]` | role-match |
| `frontend/vitest.setup.ts` | config | test-time | `backend/tests/conftest.py` | role-match |
| `frontend/src/app/layout.tsx` | component (root) | request-response (SSR build) | — | RESEARCH §8 |
| `frontend/src/app/page.tsx` | component (page) | static render | — | UI-SPEC §5.1 |
| `frontend/src/app/globals.css` | style tokens | build-time | — | UI-SPEC §4.1 + RESEARCH §4 |
| `frontend/src/app/debug/page.tsx` | component (page) | subscribe-render | `backend/market_data_demo.py` (terminal live view of same store) | role-match (cross-lang) |
| `frontend/src/lib/sse-types.ts` | model | data contract | `backend/app/market/models.py` (`PriceUpdate` + `to_dict`) | **exact conceptual match** |
| `frontend/src/lib/price-store.ts` | service (state shell) | streaming ingest | `backend/app/market/cache.py` (`PriceCache`) | **exact conceptual match** |
| `frontend/src/lib/price-stream-provider.tsx` | provider (lifecycle) | mount/unmount | `backend/app/market/stream.py` (`create_stream_router` factory-closure) + `SimulatorDataSource.start/stop` lifecycle | role-match (cross-lang) |
| `frontend/src/lib/price-stream.test.ts` | test | unit | `backend/tests/market/test_cache.py` (class-grouped behaviors against the analog module) | style-match |

---

## Pattern Assignments

### `frontend/src/lib/sse-types.ts` (model, data contract)

**Analog:** `backend/app/market/models.py:9-49` (`PriceUpdate` frozen dataclass + `to_dict()`)

**Why it matches:** The backend's `PriceUpdate.to_dict()` is the exact JSON shape that ends up inside `event.data` on the frontend. The TypeScript interface must reproduce those keys verbatim. This is the single pair in the codebase where the type contract is load-bearing across the wire.

**Pattern excerpt (`backend/app/market/models.py:39-49`):**
```python
def to_dict(self) -> dict:
    """Serialize for JSON / SSE transmission."""
    return {
        "ticker": self.ticker,
        "price": self.price,
        "previous_price": self.previous_price,
        "timestamp": self.timestamp,
        "change": self.change,
        "change_percent": self.change_percent,
        "direction": self.direction,
    }
```

**Adaptation notes:**
- Mirror these 7 keys in `RawPayload` interface — no extras, no omissions.
- Backend emits `timestamp` as Unix seconds (`float`, not ms) — `Tick.timestamp: number` in seconds.
- Backend `direction` is `"up" | "down" | "flat"` (see `models.py:30-37`) — reproduce as a union type `Direction`.
- Phase 6 extends this with one **frontend-only** field `session_start_price: number` (computed client-side per D-14). Do **not** add this key to `RawPayload` — only to `Tick`.
- Lift the full template from **RESEARCH.md §5** verbatim.

---

### `frontend/src/lib/price-store.ts` (service, streaming ingest + lifecycle)

**Analog:** `backend/app/market/cache.py` (`PriceCache` class, full file)

**Why it matches:** Both are the single source of truth for ticker-keyed state, both expose a narrow mutation API (`update`/`ingest`), both protect against concurrent producers (backend uses `threading.Lock`; frontend uses React's single-threaded event loop + Zustand's atomic `set`), and both expose a monotonic change signal (backend `version` counter; frontend `lastEventAt` timestamp + Zustand's built-in subscription).

**Pattern excerpt 1 — narrow mutation API with first-write-handling (`backend/app/market/cache.py:23-42`):**
```python
def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
    """Record a new price for a ticker. Returns the created PriceUpdate.

    Automatically computes direction and change from the previous price.
    If this is the first update for the ticker, previous_price == price (direction='flat').
    """
    with self._lock:
        ts = timestamp or time.time()
        prev = self._prices.get(ticker)
        previous_price = prev.price if prev else price  # ← first-seen fallback
        update = PriceUpdate(ticker=ticker, price=round(price, 2),
                             previous_price=round(previous_price, 2), timestamp=ts)
        self._prices[ticker] = update
        self._version += 1
        return update
```

**Translation for `ingest()`:** The `prev.price if prev else price` pattern maps directly to D-14's `session_start_price` freeze:
```ts
const prior = next[ticker];
next[ticker] = {
  ...raw,
  session_start_price: prior?.session_start_price ?? raw.price,  // ← first-seen freeze
};
```
Read `backend/app/market/cache.py:31-32` to see the idiom; it is the single clearest line in the repo for "first-seen value, never overwritten."

**Pattern excerpt 2 — idempotent remove / no-defensive-raise (`backend/app/market/cache.py:59-62`):**
```python
def remove(self, ticker: str) -> None:
    """Remove a ticker from the cache (e.g., when removed from watchlist)."""
    with self._lock:
        self._prices.pop(ticker, None)  # Idempotent, no raise if missing
```

**Translation:** `reset()` and `disconnect()` are the same spirit — idempotent, no raise if already in that state. Matches D-15 (idempotent `connect`).

**Pattern excerpt 3 — narrow try/except at the wire boundary (`backend/app/market/massive_client.py:96-128`):**
```python
try:
    snapshots = await asyncio.to_thread(self._fetch_snapshots)
    processed = 0
    for snap in snapshots:
        try:
            price = snap.last_trade.price
            # ... update cache
        except (AttributeError, TypeError) as e:
            logger.warning("Skipping snapshot for %s: %s",
                           getattr(snap, "ticker", "???"), e)
    # ...
except Exception as e:
    logger.error("Massive poll failed: %s", e)
    # Don't re-raise — the loop will retry on the next interval.
```

**Translation for D-19 (malformed SSE frame):** Two-level narrow catch in `onmessage`. Outer `try` around `JSON.parse` logs and drops the whole frame; inner `isValidPayload` guard drops per-ticker entries silently (equivalent to the `(AttributeError, TypeError)` narrow catch). `console.warn` is the frontend analog of `logger.warning` — pass structured args, never template-literal the raw data into a string:
```ts
try {
  const parsed = JSON.parse(event.data) as Record<string, RawPayload>;
  get().ingest(parsed);
} catch (err) {
  console.warn('sse parse failed', err, event.data);  // narrow, log-and-continue
}
```

**Adaptation notes:**
- Lift the full store template from **RESEARCH.md §6** verbatim (Zustand 5 double-parens TS syntax, `__setEventSource` DI export, idempotent `connect`, state machine in `onerror`).
- Keep the module ≤120 lines (CONVENTIONS.md: short modules).
- One module-level `es: EventSource | null` + one module-level `EventSourceCtor` — these are the analog of `backend/app/market/cache.py`'s `self._prices` and `self._lock`. The backend uses instance state; the frontend uses module state because the store IS the singleton.
- **Do not** add outer try/except around the whole `connect` body. Only the `JSON.parse`+`ingest` boundary gets a `try/catch`. Matches `backend/app/market/massive_client.py:96`'s boundary rule.

---

### `frontend/src/lib/price-stream-provider.tsx` (provider, lifecycle)

**Analog:** `backend/app/market/stream.py:18-53` (`create_stream_router` factory closure) and `backend/app/market/simulator.py:221-242` (`SimulatorDataSource.start()`/`stop()` — the async-task lifecycle)

**Why it matches:**
1. `create_stream_router(price_cache)` is a factory that closes over a dependency instead of using globals. `PriceStreamProvider` is the React analog: a component that owns one `EventSource` instance over the app lifetime, instead of a module-level `new EventSource(...)` at import time.
2. `SimulatorDataSource.start/stop` is the closest lifecycle pattern in the repo: `start()` creates a single long-running task, `stop()` cancels it. `useEffect(() => { connect(); return () => disconnect(); }, [])` is the React idiom for the same shape.

**Pattern excerpt 1 — factory closure over dependency (`backend/app/market/stream.py:18-29`):**
```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    This factory pattern lets us inject the PriceCache without globals.
    A fresh APIRouter is constructed per call so repeated calls (e.g. one per
    test-spawned FastAPI app) do not accumulate duplicate /prices routes on a
    shared module-level router.
    """
    router = APIRouter(prefix="/api/stream", tags=["streaming"])
```

**Pattern excerpt 2 — symmetric start/stop with single background task (`backend/app/market/simulator.py:231-242`):**
```python
async def start(self, tickers: list[str]) -> None:
    # ... seed cache immediately so SSE has data on first connect
    self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
    logger.info("Simulator started with %d tickers", len(tickers))

async def stop(self) -> None:
    if self._task and not self._task.done():
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
    self._task = None
```

**Adaptation notes:**
- The `if self._task and not self._task.done()` guard in `stop()` is the analog of D-15's idempotent `connect()`: "no-op if already in target state."
- React StrictMode (Next dev) double-invokes `useEffect`. The store's idempotent `connect()` (module-level `if (es && es.readyState !== 2) return`) handles this the same way the `_task.done()` check does.
- Lift the full provider template from **RESEARCH.md §7** verbatim (≤20 lines). Match the backend's pattern of "start() seeds immediately" by relying on Zustand's synchronous `set` — the provider is not responsible for priming state, only for lifecycle.
- Target module length: ≤40 lines (CONVENTIONS.md short-module rule).

---

### `frontend/src/app/debug/page.tsx` (component, subscribe-render)

**Analog:** `backend/market_data_demo.py:54-101` (`build_table`) and `backend/market_data_demo.py:120-164` (`build_dashboard`)

**Why it matches:** Both are developer-facing live views of the same ticker-keyed store. The demo builds a Rich `Table` over rows of `cache.get(ticker)`; the debug page builds an HTML `<table>` over `Object.values(prices)`. Both show Ticker, Price, Change, Change %, Direction in that order — intentional parity across the two surfaces.

**Pattern excerpt (`backend/market_data_demo.py:59-101`):**
```python
def build_table(cache: PriceCache, history: dict[str, deque]) -> Table:
    """Build the price table."""
    table = Table(title=None, expand=True, border_style="bright_black",
                  header_style="bold bright_white", pad_edge=True, padding=(0, 1))
    table.add_column("Ticker", style="bold bright_white", width=8)
    table.add_column("Price", justify="right", width=10)
    table.add_column("Change", justify="right", width=9)
    table.add_column("Chg %", justify="right", width=8)
    # ...
    for ticker in TICKERS:
        update = cache.get(ticker)
        if update is None:
            table.add_row(ticker, "---", "---", "---", "", "")
            continue
        # ... render row from update.price, update.change, update.direction
```

**Adaptation notes:**
- **Column order and semantics port directly.** Both show Ticker, Price, (Prev), Change, Chg%, Direction. UI-SPEC §5.2 adds `Session Start` and `Last Tick` — these are frontend-specific (see D-14) and don't exist in the demo.
- **Right-align numeric columns** — the demo uses `justify="right"` on every numeric column; UI-SPEC §5.2 mandates `text-right` on the same set. Matches the trading-terminal-aesthetic goal.
- **Monospace for numbers** — `font-mono` on the `<table>` matches the demo's bright_white monospace Rich font (implicit in the terminal output). UI-SPEC §3 makes this explicit.
- **Empty-row handling** — demo renders `"---"` when `cache.get(ticker) is None`. Frontend equivalent per UI-SPEC §5.2 is a single spanning `<tr>` with `Awaiting first price tick...`. Different presentation, same "graceful empty state" principle.
- **Do not** port the sparkline, event log, or colored direction arrows — those are demo-only. Phase 6's debug page is text-only (UI-SPEC §5.2: "no color coding, no icons"). Colored direction arrives in Phase 7.
- Lift the full page template from **RESEARCH.md §10** + **UI-SPEC §5.2** verbatim for structure; apply UI-SPEC §8 strings exactly.

---

### `frontend/src/lib/price-stream.test.ts` (test, unit)

**Analog:** `backend/tests/market/test_cache.py` (entire file — 13 tests against `PriceCache`, the direct analog of `price-store.ts`)

**Why it matches:** Both are unit tests against the "single source of truth for ticker state" module, with one behavior per test method, grouped under a single class/describe, using a minimal in-file mock where external I/O would be. CONVENTIONS.md calls this pattern out as the repo's test style.

**Pattern excerpt (CONVENTIONS.md "Testing style" — matches what's in `backend/tests/market/`):**
```
- Tests are class-grouped (class TestPriceCache, class TestMassiveDataSource)
  with one behavior per test_* method.
- @pytest.mark.asyncio applied at the class level for async suites.
- Private attributes are sometimes set directly in tests to bypass setup
  (source._tickers = [...], source._client = MagicMock())
```

**Adaptation notes:**
- **One `describe('price-store SSE lifecycle', () => { ... })`** block is the TypeScript analog of `class TestPriceCache` — single grouping, one `it()` per behavior.
- **Dependency injection via `__setEventSource(MockEventSource)`** is the frontend analog of the backend's "set private attributes directly to bypass setup" pattern. The backend writes `source._client = MagicMock()`; the frontend writes `__setEventSource(MockEventSource)`. Both acknowledge the test contract explicitly rather than global-stubbing.
- **`beforeEach` resets state + mock; `afterEach` disconnects** — mirrors `conftest.py` + test-method-level fixtures in pytest.
- **Test one behavior at a time.** RESEARCH.md §13 enumerates 8 tests (onopen, first-event session-start, subsequent-event freeze, onerror CONNECTING, onerror CLOSED, idempotent connect, malformed payload, selector subscription). Each test asserts between every synthetic emit (Nyquist rule from RESEARCH.md §Sampling Rate) — equivalent to the backend's per-behavior test methods.
- Lift the full test template from **RESEARCH.md §13** verbatim.
- **Do not** share state across `it()` blocks — `usePriceStore.getState().reset()` in `beforeEach` is non-negotiable (matches backend tests' fresh-`PriceCache()`-per-test discipline).

---

### `frontend/src/app/layout.tsx` (component, root)

**Analog:** None in-repo (no Python equivalent of a React root layout). Structurally most similar to **`create_stream_router` mounting pattern** — the layout is the one place the provider is wired.

**Adaptation notes:**
- Lift the full template from **RESEARCH.md §8** verbatim.
- Hardcode `<html lang="en" className="dark">` per D-10.
- Mount `<PriceStreamProvider>` outermost (wrapping `{children}`) so `/debug` sees it — D-11 + Claude's Discretion in CONTEXT.md.
- Apply `bg-surface text-foreground` on `<body>` per UI-SPEC §4.3 so every page defaults to dark.
- Import `./globals.css` — this is the only file that imports it.

---

### `frontend/src/app/page.tsx` (component, page)

**Analog:** None in-repo. UI-SPEC §5.1 is the authoritative spec.

**Adaptation notes:**
- Lift template from **RESEARCH.md §9**; use exact strings from **UI-SPEC §8**:
  - H1: `FinAlly`
  - Subtitle: `AI Trading Workstation`
  - Dev note: `Dev note: see /debug for the live price stream.`
- Tailwind utilities only: `min-h-screen p-6`, `text-accent-yellow` on H1, `text-foreground-muted` on subtitle, `text-accent-blue underline underline-offset-2` on the `/debug` link.
- No emojis (CLAUDE.md rule, UI-SPEC §5.1).

---

### `frontend/src/app/globals.css` (style tokens)

**Analog:** `backend/app/market/seed_prices.py` (module-level constants pattern — one file, all tuning values, easy to audit). CSS `@theme` block is the CSS-first equivalent of "tune constants in one place."

**Pattern parallel:** The backend keeps per-ticker GBM params in `seed_prices.py` as top-level module constants. The frontend keeps color tokens in `globals.css` `@theme`. Both give one edit point.

**Adaptation notes:**
- Lift the full `@theme` block from **UI-SPEC §4.1** verbatim (10 CSS custom properties: 5 neutrals, 3 brand accents, 2 semantic up/down).
- Use Tailwind v4 CSS-first (`@import "tailwindcss"` + `@theme { ... }`). **Do not** write v3 `@tailwind base/components/utilities` directives — Tailwind v4 rejects them (RESEARCH.md Gotcha G1).
- **Do not** create a `tailwind.config.ts` — not needed for Phase 6 (RESEARCH.md §4, §Latest API Verification).

---

### `frontend/next.config.mjs`, `postcss.config.mjs`, `vitest.config.mts`, `vitest.setup.ts`, `package.json`, `README.md`, `tsconfig.json`, `.eslintrc.json`, `.gitignore`

**Analog:** None in-repo for any of these. All are framework-idiomatic files.

**Adaptation notes — lift verbatim:**
| File | Source |
|------|--------|
| `package.json` (scripts + engines + deps) | **RESEARCH.md §1** (including Node pin + `test`/`test:ci` scripts) |
| `next.config.mjs` | **RESEARCH.md §2** (output: export, images.unoptimized, trailingSlash, dev-only rewrites with stream route listed first) |
| `postcss.config.mjs` | **RESEARCH.md §3** (`@tailwindcss/postcss` — **not** `tailwindcss`, see G1) |
| `vitest.config.mts` | **RESEARCH.md §11** (jsdom env + `@vitejs/plugin-react` + `vite-tsconfig-paths`) |
| `vitest.setup.ts` | **RESEARCH.md §12** (one-line import of `@testing-library/jest-dom/vitest`) |
| `README.md` | **RESEARCH.md §14** (10–20 lines, `backend/README.md` concision style) |
| `tsconfig.json`, `.eslintrc.json`, `.gitignore` | `create-next-app` defaults — do not edit |

---

## Shared Patterns

### Narrow try/catch at boundaries only

**Source:** CONVENTIONS.md "Error handling — narrow and intentional" + `backend/app/market/massive_client.py:96-128`
**Apply to:** `price-store.ts` `onmessage` (JSON.parse boundary) — nowhere else

```python
# backend pattern — one boundary, log-and-continue
try:
    snapshots = await asyncio.to_thread(self._fetch_snapshots)
    # ...
except Exception as e:
    logger.error("Massive poll failed: %s", e)
    # Don't re-raise — the loop will retry on the next interval.
```

```ts
// frontend analog — one boundary at the wire
try {
  const parsed = JSON.parse(event.data) as Record<string, RawPayload>;
  get().ingest(parsed);
} catch (err) {
  console.warn('sse parse failed', err, event.data);
  // Don't rethrow — EventSource will auto-reconnect on the next emit.
}
```

### Factory closure over dependency — no module-level globals

**Source:** `backend/app/market/stream.py:18` (`create_stream_router(price_cache)`) + CONVENTIONS.md "FastAPI idioms"
**Apply to:** `PriceStreamProvider` (React component closing over the store) — not a module-level `new EventSource()` at import time (anti-pattern, CONTEXT.md "Anti-Patterns to Avoid")

### Idempotent lifecycle operations

**Source:** `backend/app/market/cache.py:59-62` (`remove` → `pop(..., None)`), `backend/app/market/simulator.py:234-242` (`stop` → `if task and not task.done()`), `backend/app/market/massive_client.py:68-72` (`add_ticker` → `if ticker not in self._tickers`)
**Apply to:** `connect()` (no-op if `es && es.readyState !== 2`), `disconnect()` (no-op if `es === null`), `reset()` (overwrite to empty regardless of current state). Matches D-15.

### Module-level constants over magic numbers

**Source:** `backend/app/market/seed_prices.py` (all tuning in one file)
**Apply to:** `globals.css` `@theme` block (all color tokens in one place), `sse-types.ts` `Direction` / `ConnectionStatus` union types (not string literals scattered through the store)

### Narrow, explicit public API via `__all__` / named exports

**Source:** `backend/app/market/__init__.py:17-23` (explicit `__all__`)
```python
__all__ = ["PriceUpdate", "PriceCache", "MarketDataSource",
           "create_market_data_source", "create_stream_router"]
```
**Apply to:** `price-store.ts` named exports — `usePriceStore`, `selectTick`, `selectConnectionStatus`, `__setEventSource`. No default export, no wildcard re-exports. Phase 7/8 import these by name.

### No emojis, no f-string logging (→ no template-literal-only `console.warn` args)

**Source:** CONVENTIONS.md + global CLAUDE.md. Backend uses `%`-placeholders (`logger.info("Simulator started with %d tickers", n)`) precisely because args format lazily.
**Apply to:** Frontend analog — pass structured args to `console.warn('sse parse failed', err, event.data)`, not `console.warn(\`sse parse failed: ${err}: ${event.data}\`)`. Same laziness benefit (devtools inspector shows structured values).

### Short modules, short functions

**Source:** CONVENTIONS.md + PROJECT.md. Backend's largest market module is ~270 lines (`simulator.py`); most are <120.
**Apply to:** Target budgets per RESEARCH.md: `price-store.ts` ≤120, `price-stream-provider.tsx` ≤40, `sse-types.ts` ≤40. Hard cap at these — if a file is pushing the limit, decompose.

### Docstring / JSDoc on public functions; sparing inline comments

**Source:** CONVENTIONS.md. Backend uses one-line module docstrings + per-method docstrings stating behavior, not restating signatures.
**Apply to:** JSDoc (`/** ... */`) on `connect`, `disconnect`, `ingest`, `__setEventSource`, `PriceStreamProvider`. Inline `//` only where non-obvious (e.g., `// D-14: freeze first-seen`, `// D-15: idempotent`). Every comment should reference the decision ID it implements.

---

## No Analog Found

All 17 files are net-new TypeScript/Next.js artifacts. The following have **zero conceptual parallel** in the backend and must be lifted from RESEARCH.md templates directly:

| File | Lift from |
|------|-----------|
| `frontend/next.config.mjs` | RESEARCH.md §2 |
| `frontend/postcss.config.mjs` | RESEARCH.md §3 |
| `frontend/src/app/layout.tsx` | RESEARCH.md §8 |
| `frontend/src/app/page.tsx` | RESEARCH.md §9 + UI-SPEC §5.1 + §8 |
| `frontend/vitest.config.mts` | RESEARCH.md §11 |
| `frontend/vitest.setup.ts` | RESEARCH.md §12 |
| `frontend/package.json` (scripts/engines/deps) | RESEARCH.md §1 |
| `frontend/README.md` | RESEARCH.md §14 (style-match `backend/README.md` concision) |
| `frontend/tsconfig.json`, `.eslintrc.json`, `.gitignore` | `create-next-app` defaults — do not edit |

The files that **do** have strong backend conceptual analogs (`sse-types.ts`, `price-store.ts`, `price-stream-provider.tsx`, `debug/page.tsx`, `price-stream.test.ts`) are where the planner gets leverage — the translation patterns above make the frontend feel native to this repo's discipline rather than a bolted-on Next.js project.

---

## Metadata

**Analog search scope:** `backend/app/market/` (8 files, ~500 LOC), `backend/tests/market/` (6 files via CONVENTIONS.md summary), `backend/market_data_demo.py`, `backend/CLAUDE.md`, all `.planning/codebase/*.md`
**Files scanned:** 11 backend source files + 5 planning docs = 16
**Analogs ranked and read in full:** 5 (`models.py`, `cache.py`, `stream.py`, `massive_client.py`, `market_data_demo.py`) + 1 partial (`simulator.py:200-270`) + 1 index (`__init__.py`)
**Stopping criterion met:** 5 strong matches identified; further search would be dilutive.
**Pattern extraction date:** 2026-04-23

## PATTERN MAPPING COMPLETE
