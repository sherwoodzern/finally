---
phase: 8
slug: portfolio-visualization-chat-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-25
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `08-RESEARCH.md` §Validation Architecture and `08-UI-SPEC.md` §13.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest 4.1 + React Testing Library 16.3 + jsdom 29.0 |
| **Config file** | `frontend/vitest.config.mts` |
| **Setup file** | `frontend/vitest.setup.ts` (extend with `ResizeObserver` stub for Recharts) |
| **Quick run command** | `cd frontend && npm test -- <pattern>` (vitest watch) |
| **Full suite command** | `cd frontend && npm run test:ci` |
| **Backend smoke** | `cd backend && uv run --extra dev pytest -v` (only the new APP-02 mount integration test) |
| **Build gate** | `cd frontend && npm run build` (Next.js export must produce `frontend/out/`) |
| **Estimated runtime** | ~12 seconds frontend full suite, ~3 seconds backend pytest, ~25 seconds frontend build |

---

## Sampling Rate

- **After every task commit:** `npm test -- <relevant pattern>` (watch on the changed test file or component)
- **After every plan wave:** `npm run test:ci && npm run build` (full Vitest suite + Next export build gate)
- **Before `/gsd-verify-work`:** Full suite must be green AND `npm run build` succeeds AND `uv run pytest` (backend) green
- **Max feedback latency:** 30 seconds (single test file ≤ 5s, full Vitest suite ≤ 12s, build ≤ 25s)

---

## Per-Task Verification Map

| Req | Behavior | Test Type | Automated Command | File Exists | Status |
|-----|----------|-----------|-------------------|-------------|--------|
| FE-05 | Heatmap renders one rect per position with binary up/down coloring | unit (RTL props) | `npm test Heatmap.test.tsx` | Wave 0 | pending |
| FE-05 | Heatmap click on rect dispatches `setSelectedTicker` | unit | `npm test Heatmap.test.tsx` | Wave 0 | pending |
| FE-05 | Heatmap empty state copy when `positions.length === 0` | unit | `npm test Heatmap.test.tsx` | Wave 0 | pending |
| FE-05 | Heatmap cell renders cold-cache neutral when `current_price` null | unit | `npm test HeatmapCell.test.tsx` | Wave 0 | pending |
| FE-05 | Heatmap weight calc `quantity * current_price` over total | unit (pure-fn) | `npm test Heatmap.test.tsx` | Wave 0 | pending |
| FE-05 | HeatmapCell P&L %: `(current_price - avg_cost) / avg_cost * 100`, signed, 2dp | unit | `npm test HeatmapCell.test.tsx` | Wave 0 | pending |
| FE-06 | PnLChart line stroke is `--color-up` when `latest >= 10000` | unit (props) | `npm test PnLChart.test.tsx` | Wave 0 | pending |
| FE-06 | PnLChart line stroke is `--color-down` when `latest < 10000` | unit | `npm test PnLChart.test.tsx` | Wave 0 | pending |
| FE-06 | PnLChart 1-snapshot empty state copy | unit | `npm test PnLChart.test.tsx` | Wave 0 | pending |
| FE-06 | PnLChart includes `<ReferenceLine y={10000}>` dashed | unit | `npm test PnLChart.test.tsx` | Wave 0 | pending |
| FE-09 | ChatDrawer default-open and toggles to ~48px collapsed strip | unit | `npm test ChatDrawer.test.tsx` | Wave 0 | pending |
| FE-09 | ChatThread renders messages from `/api/chat/history` on mount | unit (fetch stub) | `npm test ChatThread.test.tsx` | Wave 0 | pending |
| FE-09 | ChatThread shows 3-dot ThinkingBubble while `postChat` in flight | unit | `npm test ChatThread.test.tsx` | Wave 0 | pending |
| FE-09 | ChatInput: Enter submits, Shift+Enter inserts newline | unit (keyboard) | `npm test ChatInput.test.tsx` | Wave 0 | pending |
| FE-09 | ActionCard renders `executed/added/removed` with green border | unit | `npm test ActionCard.test.tsx` | Wave 0 | pending |
| FE-09 | ActionCard renders `failed` with red border + mapped error string | unit | `npm test ActionCard.test.tsx` | Wave 0 | pending |
| FE-09 | ActionCard renders `exists/not_present` muted gray border | unit | `npm test ActionCard.test.tsx` | Wave 0 | pending |
| FE-09 | ActionCardList renders watchlist_changes BEFORE trades | unit | `npm test ActionCardList.test.tsx` | Wave 0 | pending |
| FE-11 | Position-row trade-flash `bg-up/20` (or `bg-down/20`) for ~800ms after executed trade | unit (fake timers) | `npm test PositionRow.test.tsx` | extend | pending |
| FE-11 | 500ms price-flash and 800ms trade-flash do not visually collide on the same row | unit | `npm test PositionRow.test.tsx` | extend | pending |
| FE-11 | SkeletonBlock pulses while TanStack Query `isPending`; unmounts after resolve | unit | `npm test Heatmap.test.tsx` | Wave 0 | pending |
| TEST-02 | Phase 7 price-flash test stays green (regression guard) | unit | `npm run test:ci` | existing | pending |
| APP-02 | FastAPI returns `frontend/out/index.html` at `GET /` AND `GET /api/health` returns JSON | integration | `uv run pytest backend/tests/test_static_mount.py` | Wave 0 | pending |
| APP-02 | `next.config.mjs` `skipTrailingSlashRedirect: true` (G1 fix) | grep assert | `grep -q skipTrailingSlashRedirect frontend/next.config.mjs` | inline | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

New test files (created alongside the components in their plans):

- [ ] `frontend/src/components/portfolio/Heatmap.test.tsx` — FE-05 (5 tests)
- [ ] `frontend/src/components/portfolio/HeatmapCell.test.tsx` — FE-05 cell rendering
- [ ] `frontend/src/components/portfolio/PnLChart.test.tsx` — FE-06 (4 tests)
- [ ] `frontend/src/components/chat/ChatDrawer.test.tsx` — FE-09 drawer behavior
- [ ] `frontend/src/components/chat/ChatThread.test.tsx` — FE-09 thread + history + thinking-bubble
- [ ] `frontend/src/components/chat/ChatInput.test.tsx` — FE-09 keyboard
- [ ] `frontend/src/components/chat/ActionCard.test.tsx` — FE-09 status styling
- [ ] `frontend/src/components/chat/ActionCardList.test.tsx` — FE-09 ordering (watchlist before trades)
- [ ] `frontend/src/components/terminal/PositionRow.test.tsx` — extend Phase 7 file with trade-flash + interference tests
- [ ] `frontend/src/lib/fixtures/portfolio.ts` — sample `PortfolioResponse` (1 positive, 1 negative, 1 cold-cache)
- [ ] `frontend/src/lib/fixtures/history.ts` — sample 5-snapshot history crossing $10k
- [ ] `frontend/src/lib/fixtures/chat.ts` — sample `/api/chat/history` covering all 6 statuses
- [ ] `frontend/vitest.setup.ts` — add `vi.stubGlobal('ResizeObserver', ResizeObserverStub)` (Recharts requires it in jsdom)
- [ ] `backend/tests/test_static_mount.py` — APP-02 integration test (FastAPI `TestClient` asserts `GET /` returns 200 with index html, `GET /api/health` still works after mount registration)

*Existing infrastructure:* Vitest, RTL, jsdom, MockEventSource, fake timers — all installed in Phase 6 + Phase 7.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Demo polish "feels right" — drawer slide, action-card pulse, position-row flash visually distinct from price-flash | FE-11 | Subjective motion-quality judgment; automated tests cover existence and timing of class application but not human-perceived smoothness | Open `http://localhost:8000`, start with default-open chat, ask "Buy 1 AAPL", observe (1) chat 3-dot bubble, (2) action card pulse + (3) AAPL position-row 800ms flash + (4) cash header decrement. Repeat for "Sell" and "Add PYPL to watchlist". |
| Skeleton-to-content transition is jank-free | FE-11 | Visual quality of swap | Cold-load `http://localhost:8000`, watch each panel transition from skeleton to live data; no FOUC, no layout shift |
| `/api/stream/prices` SSE works through dev (`npm run dev`) and prod (`uv run main`) post-G1 fix | APP-02 (G1 carry-over from Phase 7) | Cross-process verification | Start backend (`uv run main` from `backend/`); start frontend (`npm run dev` from `frontend/`); open browser to dev URL; verify prices stream. Stop dev, run `npm run build`; restart backend serving `frontend/out/`; verify same. |
| Cmd+K shortcut deferred — not implemented | FE-09 (Claude's discretion) | Out of scope for v1 | N/A — defer to v2 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (test files + fixtures + setup stub + backend integration test)
- [ ] No watch-mode flags in CI commands
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner has produced PLAN.md files and a final pass over this map)

**Approval:** pending
