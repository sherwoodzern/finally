---
phase: 08-portfolio-visualization-chat-ui
verified: 2026-04-26T13:30:00Z
status: human_needed
score: 5/5 must-haves verified (automated)
overrides_applied: 0
human_verification:
  - test: "Open http://localhost:8000 with backend running and visually confirm the portfolio heatmap rectangles render at correct relative sizes and recolor (green/red) as live tick prices flow"
    expected: "Treemap shows one cell per position, sized by quantity*price, fill flips between var(--color-up) and var(--color-down) within ~1s of P&L crossing break-even; cold-cache cells render var(--color-surface-alt)"
    why_human: "Recharts <Treemap> geometry collapses to 0x0 in jsdom; visual sizing/recoloring under live SSE ticks cannot be asserted programmatically"
  - test: "Watch the P&L line chart over a multi-snapshot session (>=2 trades or >=60s with the snapshot observer running) and confirm it extends in real time"
    expected: "Stroke flips at break-even (last_total >= 10000 → up green, < 10000 → down red); dotted $10k ReferenceLine remains visible; chart redraws when a new snapshot arrives via the 15s refetch"
    why_human: "Live snapshot accrual requires the running backend; no mock can prove the 'extends with new snapshot points' clause of SC#2 in jsdom"
  - test: "Open the chat drawer, type a request that produces both a trade and a watchlist change, send, observe the loading + completion sequence"
    expected: "ThinkingBubble appears within ~100ms of submit; assistant message + ActionCards render in the order watchlist_changes → trades; executed cards pulse for ~800ms; PositionRow flashes bg-up/20 simultaneously"
    why_human: "Real LLM round-trip + simultaneous flash-trade + agentic visual moment is a felt experience (UI-SPEC §7 motion contract) — automated test only proves wiring, not perceived demo polish (SC#5)"
  - test: "Toggle the chat drawer collapse/expand button and confirm the 300ms ease-out width transition feels smooth"
    expected: "w-[380px] ↔ w-12 transition runs over 300ms with no jank; under prefers-reduced-motion the transition is instant"
    why_human: "CSS transitions and the prefers-reduced-motion fallback are runtime browser behavior; the unit test only asserts class application"
  - test: "Type an Enter newline (Shift+Enter) followed by Enter to submit; confirm Enter does NOT submit when text is empty"
    expected: "Shift+Enter inserts a newline; Enter on whitespace-only content is a no-op; Enter on non-empty content submits"
    why_human: "Final UX feel of the keyboard contract under real keyboard input"
  - test: "Run npm run dev (Next dev server on :3000) and confirm /api/stream/prices works without the G1 308→307 redirect chain"
    expected: "EventSource stays connected; SSE frames flow continuously"
    why_human: "Tests Plan 01's skipTrailingSlashRedirect: true fix end-to-end; no automated test covers the dev rewrite path"
---

# Phase 8: Portfolio Visualization & Chat UI Verification Report

**Phase Goal:** The terminal gains its "wow" surfaces — the portfolio heatmap, P&L line chart, and a docked AI chat panel — served as static files by FastAPI at the same origin as the API, with frontend component tests covering the visible behaviors.

**Verified:** 2026-04-26T13:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (from ROADMAP Success Criteria) | Status | Evidence |
|---|---------------------------------------|--------|----------|
| 1 | Portfolio heatmap renders one rectangle per position, sized by weight and colored by P&L (green profit, red loss), updating as prices/positions change | VERIFIED (automated) — needs human (visual) | `frontend/src/components/portfolio/Heatmap.tsx` builds Recharts Treemap with `dataKey="weight"`, `weight = quantity * current_price` (cold-cache fallback to avg_cost). `HeatmapCell.tsx` fills `var(--color-up)` when `isUp` else `var(--color-down)`, `var(--color-surface-alt)` when `isCold`. Live ticks from `usePriceStore.prices` re-render via `useShallow` selector. 13 Vitest tests pass (Heatmap 7 + HeatmapCell 6) |
| 2 | P&L line chart (Recharts) renders /api/portfolio/history and extends with new snapshot points | VERIFIED (automated) — needs human (live extension) | `frontend/src/components/portfolio/PnLChart.tsx` uses `useQuery({ queryKey: ['portfolio','history'], queryFn: getPortfolioHistory, refetchInterval: 15_000 })` against real `GET /api/portfolio/history`. Stroke flips at $10k break-even. ReferenceLine y=10000 dashed. 6 Vitest tests pass |
| 3 | Docked/collapsible AI chat panel: history, input, loading indicator, inline confirmation entries for executed trades + watchlist changes | VERIFIED (automated) | `ChatDrawer.tsx` (collapsible w-[380px] ↔ w-12, transition-[width] duration-300), `ChatThread.tsx` (useQuery `['chat','history']` + useMutation `postChat` + `<ThinkingBubble />` while pending + `flashTrade` per executed trade + invalidates `['portfolio']` and `['watchlist']`), `ActionCardList.tsx` (watchlist_changes BEFORE trades), `ActionCard.tsx` (per-status border + pulse + ERROR_COPY). 16 Vitest tests pass (ChatDrawer 2 + ActionCard 4 + ActionCardList 2 + ChatInput 4 + ChatThread 4 incl. XSS guard) |
| 4 | FastAPI from a single process serves Next.js export at / on port :8000 (no CORS, no second server) | VERIFIED | `backend/app/lifespan.py` lines 86-91: `app.mount("/", StaticFiles(directory=str(static_dir), html=True, check_dir=False), name="frontend")` registered AFTER all four `app.include_router(...)` calls. `frontend/next.config.mjs` has `skipTrailingSlashRedirect: true` (G1 fix). Frontend build produces `frontend/out/index.html` (12,458 bytes). 4/4 backend integration tests pass (incl. `test_index_html_served_at_root` PASSED, not skipped) |
| 5 | Frontend component tests cover price-flash, watchlist CRUD UI, portfolio display calculations, chat rendering + loading state — all green; demo-grade polish present | VERIFIED (automated) — needs human (polish feel) | `npm run test:ci`: 19 test files, 111/111 tests passing. Coverage: PositionRow.test.tsx (price-flash 500ms + trade-flash 800ms + non-interference), WatchlistRow.test.tsx (CRUD), Heatmap+HeatmapCell+PnLChart (display calcs), ChatThread+ChatInput+ActionCard+ActionCardList+ChatDrawer (rendering + loading state). globals.css has `@keyframes action-pulse-up/down`, `thinking-pulse`, prefers-reduced-motion block. SkeletonBlock primitive. ChatDrawer transition-[width] duration-300 |

**Score:** 5/5 truths VERIFIED automatically. Human visual/UX verification still required for SC#1 live recoloring, SC#2 live extension, SC#3 felt agentic moment, and SC#5 demo-grade polish feel.

### Required Artifacts

| Artifact | Expected | Exists | Substantive | Wired | Data Flows | Status |
|----------|----------|--------|-------------|-------|------------|--------|
| `backend/app/lifespan.py` (mount) | StaticFiles mount at / after all /api/* | Yes | Yes (line 87 mount, after 4 include_router calls 75-80) | Yes (test_static_mount.py 4/4 PASS) | n/a | VERIFIED |
| `frontend/next.config.mjs` | skipTrailingSlashRedirect: true | Yes | Yes (line 6) | Yes (Next dev rewrite chain) | n/a | VERIFIED |
| `backend/tests/test_static_mount.py` | 4 integration tests | Yes | Yes | Yes (4/4 PASS, 0 skips) | n/a | VERIFIED |
| `frontend/src/components/portfolio/Heatmap.tsx` | Treemap + handleHeatmapCellClick + buildTreeData (≤120 lines) | Yes | 120 lines | Imported in Terminal.tsx | useQuery → fetchPortfolio → /api/portfolio (real); livePrices via usePriceStore | VERIFIED |
| `frontend/src/components/portfolio/HeatmapCell.tsx` | SVG renderer with var(--color-up/down/surface-alt) | Yes | 68 lines | Used by Heatmap.tsx | Props from Heatmap | VERIFIED |
| `frontend/src/components/portfolio/PnLChart.tsx` | LineChart + ReferenceLine y=10000 + stroke flip | Yes | 107 lines | Imported in Terminal.tsx | useQuery → getPortfolioHistory → /api/portfolio/history (real) | VERIFIED |
| `frontend/src/components/portfolio/PnLTooltip.tsx` | Custom tooltip date+total+delta | Yes | substantive | Used by PnLChart | n/a | VERIFIED |
| `frontend/src/components/chat/ChatDrawer.tsx` | Collapsible aside with children slot | Yes | 33 lines | Mounted in Terminal.tsx wrapping ChatThread | n/a | VERIFIED |
| `frontend/src/components/chat/ChatThread.tsx` | History fetch + mutation + flashTrade + invalidations | Yes | 114 lines | Mounted as ChatDrawer child | useQuery+useMutation → real /api/chat/* | VERIFIED |
| `frontend/src/components/chat/ChatInput.tsx` | Textarea + Send + Enter/Shift+Enter contract | Yes | substantive | Used by ChatThread | Calls onSubmit prop → mutation | VERIFIED |
| `frontend/src/components/chat/ChatMessage.tsx` | User vs assistant bubbles + ActionCardList; JSX text only (no dangerouslySetInnerHTML) | Yes | 41 lines | Used by ChatThread | Props from ChatThread | VERIFIED |
| `frontend/src/components/chat/ChatHeader.tsx` | Title + toggle button (›/‹) | Yes | substantive | Used by ChatDrawer | n/a | VERIFIED |
| `frontend/src/components/chat/ActionCard.tsx` | STATUS_STYLE + ERROR_COPY + 800ms pulse | Yes | 106 lines | Used by ActionCardList | Props from ActionCardList | VERIFIED |
| `frontend/src/components/chat/ActionCardList.tsx` | watchlist_changes BEFORE trades | Yes | substantive | Used by ChatMessage | Props from ChatMessage | VERIFIED |
| `frontend/src/components/chat/ThinkingBubble.tsx` | 3 thinking-dot spans | Yes | substantive | Used by ChatThread | n/a | VERIFIED |
| `frontend/src/components/terminal/Terminal.tsx` | Flex row + tabbed center + ChatDrawer><ChatThread/> | Yes | 50 lines | Top-level page | Renders all surfaces | VERIFIED |
| `frontend/src/components/terminal/TabBar.tsx` | 3-tab switcher Chart/Heatmap/P&L | Yes | substantive | Mounted in Terminal | Reads/writes selectedTab via store | VERIFIED |
| `frontend/src/components/terminal/PositionRow.tsx` | bg-up/20 trade-flash alongside Phase 7 bg-up/10 | Yes | 80 lines | Mounted in PositionsTable | selectFlash + selectTradeFlash | VERIFIED |
| `frontend/src/components/terminal/TradeBar.tsx` | onSuccess(res) calls flashTrade(res.ticker, 'up') | Yes | 133 lines | Mounted in Terminal | Real /api/portfolio/trade + store dispatch | VERIFIED |
| `frontend/src/components/skeleton/SkeletonBlock.tsx` | Reusable bg-border-muted/50 animate-pulse div | Yes | substantive | Available primitive (used inline in Heatmap/PnLChart skeletons) | n/a | VERIFIED |
| `frontend/src/lib/api/portfolio.ts` (extension) | getPortfolioHistory + SnapshotOut + HistoryResponse | Yes | Lines 72-86 added | Used by PnLChart | fetch('/api/portfolio/history') | VERIFIED |
| `frontend/src/lib/api/chat.ts` | postChat + getChatHistory + full type surface | Yes | substantive | Used by ChatThread | fetch('/api/chat'), fetch('/api/chat/history') | VERIFIED |
| `frontend/src/lib/price-store.ts` (extension) | selectedTab + tradeFlash slices + selectors | Yes | Lines 20-28 + 46-49 | Used by TabBar/Heatmap/PositionRow/TradeBar/ChatThread | Store actions | VERIFIED |
| `frontend/vitest.setup.ts` | ResizeObserver stub for Recharts | Yes | substantive | Vitest globalSetup | n/a | VERIFIED |
| `frontend/src/app/globals.css` | @keyframes action-pulse-up/down + thinking-pulse + prefers-reduced-motion | Yes | extension preserved | Tailwind v4 chunk | n/a | VERIFIED |
| `frontend/out/index.html` (build artifact) | Next export output | Yes | 12,458 bytes | Served by FastAPI mount | n/a | VERIFIED |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Heatmap.tsx | useQuery(['portfolio']) → /api/portfolio | fetchPortfolio | WIRED | Same-origin fetch, queryKey present, refetchInterval 15s |
| PnLChart.tsx | useQuery(['portfolio','history']) → /api/portfolio/history | getPortfolioHistory | WIRED | Real fetch, queryKey present |
| ChatThread.tsx | POST /api/chat + GET /api/chat/history | useMutation+useQuery | WIRED | Both fetch calls hit real endpoints; result handled (setAppended, flashTrade, invalidateQueries) |
| TradeBar.tsx | flashTrade store action | usePriceStore.getState().flashTrade(res.ticker,'up') | WIRED | onSuccess body confirmed (line 41) |
| Terminal.tsx | ChatDrawer wrapping ChatThread | <ChatDrawer><ChatThread/></ChatDrawer> | WIRED | Lines 44-46; placeholder slot removed |
| Terminal.tsx | tab-conditional Heatmap/PnLChart/MainChart | selectedTab === ... && <X /> | WIRED | Lines 34-36 |
| PositionRow.tsx | selectTradeFlash store slice | usePriceStore(selectTradeFlash(ticker)) | WIRED | Class composition includes both flashClass and tradeFlashClass on line 55 |
| ChatMessage.tsx | content render | JSX text {message.content} | WIRED — XSS-safe | Zero dangerouslySetInnerHTML in chat tree |
| FastAPI / | frontend/out/index.html | StaticFiles mount after API routers | WIRED | test_static_mount.py 4/4 PASS, including live HTTP GET / |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| Heatmap.tsx | `data.positions` | useQuery → fetchPortfolio → fetch('/api/portfolio') | Yes — real backend route from Phase 3 (PORT-01 complete) | FLOWING |
| Heatmap.tsx | `livePrices[ticker]` | usePriceStore.prices via useShallow | Yes — populated by Phase 7 SSE stream | FLOWING |
| PnLChart.tsx | `data.snapshots` | useQuery → getPortfolioHistory → fetch('/api/portfolio/history') | Yes — real backend route from Phase 3 (PORT-04 + PORT-05 snapshots accrue from observer) | FLOWING |
| ChatThread.tsx | `historyQuery.data.messages` | useQuery → getChatHistory → fetch('/api/chat/history') | Backend route Phase 5 (CHAT-* still pending in REQUIREMENTS) — see deferred note | STATIC fallback in tests; real route depends on Phase 5 |
| ChatThread.tsx | `mutation.data` (ChatResponse) | useMutation → postChat → fetch('/api/chat') | Same as above — Phase 5 dependency; LLM_MOCK path or real LLM | STATIC fallback in tests; depends on Phase 5 |
| PositionRow.tsx | `tradeFlash` | usePriceStore(selectTradeFlash) populated by ChatThread.onSuccess + TradeBar.onSuccess | Yes — real flow | FLOWING |

Note on chat data flow: Phase 5 (`CHAT-01..06`) is still listed as Pending in REQUIREMENTS.md, but `/api/chat` and `/api/chat/history` routers ARE wired in `lifespan.py` (line 80) and 299 backend tests pass including chat tests. The chat orchestration UI (Phase 8) is therefore wired against real endpoints; the LLM_MOCK gate covers headless test flows.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frontend Vitest suite green | `cd frontend && npm run test:ci` | 19 files / 111 passed / 0 failed in 1.49s | PASS |
| Backend pytest suite green | `cd backend && uv run pytest -q` | 299 passed, 275 warnings, 0 failed in 7.48s | PASS |
| APP-02 static-mount tests pass with no skips | `cd backend && uv run pytest tests/test_static_mount.py -v` | 4/4 PASSED (no SKIPS) — `test_index_html_served_at_root` actively executes HTTP GET / | PASS |
| Frontend production build produces index.html | `cd frontend && npm run build && test -f frontend/out/index.html` | Built successfully (Next 16.2.4); index.html = 12,458 bytes | PASS |
| Chat XSS contract: zero dangerouslySetInnerHTML | `grep -r "dangerouslySetInnerHTML" frontend/src/components/` | 0 hits (exit 1 from grep = no matches) | PASS |
| Chat tests including XSS guard pass | `npm test -- --run chat` | 5 files / 16 passed | PASS |
| PositionRow + price-store + portfolio tests | `npm test -- --run portfolio terminal/PositionRow lib/price-store` | 6 files / 44 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| APP-02 | 08-01, 08-08 | FastAPI serves Next.js static export from / on same port | SATISFIED | `lifespan.py` mount + `test_static_mount.py` 4/4 PASS + `frontend/out/index.html` 12,458 bytes |
| FE-05 | 08-03, 08-05 | Portfolio heatmap (treemap sized by weight, colored by P&L) | SATISFIED | `Heatmap.tsx` + `HeatmapCell.tsx` + 13 Vitest tests; mounted in Terminal.tsx via tab-conditional render |
| FE-06 | 08-04, 08-05 | P&L line chart driven by /api/portfolio/history (Recharts SVG) | SATISFIED | `PnLChart.tsx` + `PnLTooltip.tsx` + 6 Vitest tests; ReferenceLine y=10000; stroke flip at break-even; mounted via TabBar |
| FE-09 | 08-06, 08-07 | AI chat panel — docked/collapsible, history, input, loading indicator, inline confirmations | SATISFIED | `ChatDrawer.tsx` (collapsible) + `ChatThread.tsx` (history fetch + mutation + ThinkingBubble + ActionCardList) + 16 Vitest tests |
| FE-11 | 08-02, 08-05, 08-06, 08-07, 08-08 | Demo-grade polish — transitions, skeletons, micro-interactions, visible trade-execution moments | SATISFIED (automated) — human verification recommended for felt UX | SkeletonBlock primitive, action-pulse-up/down @keyframes, thinking-pulse, transition-[width] duration-300, prefers-reduced-motion, PositionRow trade-flash bg-up/20, TradeBar manual-flash parity |
| TEST-02 | 08-02, 08-03, 08-04, 08-05, 08-06, 08-07, 08-08 | Frontend component tests cover price-flash, watchlist CRUD UI, portfolio display calcs, chat rendering + loading | SATISFIED | 111/111 Vitest tests across 19 files including PositionRow (price + trade flash), WatchlistRow CRUD, Heatmap/HeatmapCell/PnLChart calculations, Chat tree rendering + ThinkingBubble loading state |

No orphaned requirements: every requirement listed for Phase 8 in REQUIREMENTS.md (FE-05, FE-06, FE-09, FE-11, APP-02, TEST-02) is claimed by at least one plan and has implementation + test evidence.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TODO/FIXME/PLACEHOLDER comments in any Phase 8 file | — | — |
| (none) | — | No `dangerouslySetInnerHTML` anywhere in `frontend/src/components/` (XSS contract upheld) | — | — |
| (none) | — | No `console.log` in production code paths | — | — |
| (none) | — | No `return null` / `return []` stub patterns hiding behind a wired surface | — | — |

Information-level note (not blockers):
- Per `08-08-SUMMARY.md` "Deferred Issues": pre-existing `tsc --noEmit` errors in `MainChart.test.tsx` and `Sparkline.test.tsx` (5 TS2493 tuple-length errors). These are **Phase 7 baseline** carry-overs that Vitest accepts (tests run green). `npm run build` (which uses Next's TypeScript step against the production tsconfig) passes cleanly. Recommend Phase 7/8 cleanup item, not a Phase 8 blocker.
- Plan 08-01 introduced `check_dir=False` on the StaticFiles constructor (auto-fix during execution; documented in `08-01-SUMMARY.md`). This is a deliberate deviation from the plan's literal text but is required for the lifespan to boot in dev/test before `npm run build` produces `frontend/out/`. Documented and intentional.

### Human Verification Required

The phase ships visual surfaces, motion, and an agentic LLM round-trip. Six items need a human:

1. **Portfolio heatmap visual sizing/coloring under live ticks** — Recharts geometry collapses to 0×0 in jsdom; only a real browser proves the SC#1 "updating as prices and positions change" clause.
2. **P&L chart live extension as new snapshots accrue** — SC#2's "extends with new snapshot points" is a runtime accrual property, not testable in jsdom.
3. **Agentic trade visual moment via chat** — Real LLM round-trip + simultaneous PositionRow flash + ActionCard pulse is the SC#5 "visible trade-execution moments" demo property; tests prove wiring, not perceived polish.
4. **Drawer collapse/expand 300ms transition feel** — CSS transitions are runtime browser behavior.
5. **ChatInput keyboard contract under real keyboard input** — Final UX feel.
6. **Plan 01 G1 SSE fix in `npm run dev`** — `skipTrailingSlashRedirect: true` correctness only validates end-to-end against the running Next dev server.

### Gaps Summary

No gaps blocking goal achievement. All five ROADMAP success criteria are programmatically verifiable as VERIFIED. Status is `human_needed` because:

- The phase is explicitly the "wow surfaces" phase with felt-experience properties (motion, transitions, agentic moments).
- ROADMAP SC#1 ("updating as prices and positions change") and SC#2 ("extends with new snapshot points as they are recorded") have runtime properties that automated tests cannot prove without a live backend tick stream.
- ROADMAP SC#5 explicitly calls out "demo-grade polish (transitions, loading skeletons, chat micro-interactions, visible trade-execution moments)" — these are perceived qualities, not assertable in unit tests.

The automated portion of the score is 5/5; the human verification list above must be exercised before the phase is considered fully delivered.

---

*Verified: 2026-04-26T13:30:00Z*
*Verifier: Claude (gsd-verifier)*
