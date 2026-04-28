# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP (AI Trading Workstation)

**Shipped:** 2026-04-28
**Phases:** 11 | **Plans:** 51 | **Commits:** 364 (63 `feat`)
**Timeline:** 9 days (2026-04-19 → 2026-04-28)
**Lines of code:** Python 7,721 · TypeScript/TSX 4,292 · Tests 2,352 · Total source ~14,365 LOC across 418 changed files

### What Was Built

- **Single-Docker-command Bloomberg-style trading terminal at `localhost:8000`** — multi-stage Dockerfile (Node 20 → Python 3.12 slim), FastAPI serves Next.js static export from `/`, SQLite persists in volume.
- **Live SSE price streaming** — `MarketDataSource` ABC with `SimulatorDataSource` (correlated GBM + random events) default and `MassiveDataSource` (Polygon REST poller) opt-in via `MASSIVE_API_KEY`.
- **Simulated $10k portfolio with instant-fill market orders** — `/api/portfolio/trade` validates and executes; 60s P&L snapshots piggyback on the price-update loop.
- **AI copilot via LiteLLM/OpenRouter/Cerebras `gpt-oss-120b`** — synchronous structured-output flow auto-executes trades and watchlist changes through the same validation path as manual operations; `LLM_MOCK=true` for deterministic E2E.
- **Three-column terminal layout + collapsible chat drawer** — Watchlist (sparklines via Lightweight Charts) · workspace (Chart / Heatmap / P&L tabs via Recharts) · positions table; chat with action cards + XSS guard + prefers-reduced-motion.
- **Canonical Playwright harness** — 7 specs × 3 browsers = 21 test pairs; `21 passed / 0 failed / 0 flaky` reproducibly across two consecutive runs at viewport 1440×900.

### What Worked

- **Adopting `planning/PLAN.md` wholesale as v1 scope.** No scope churn across 9 days — every requirement landed where the spec said it would. Pre-existing detailed spec eliminated discovery-phase rework.
- **Phase 1 → Phase 11 strict numeric ordering.** No decimal phases inserted; the dependency graph held cleanly through all 51 plans.
- **Treating market-data subsystem as Validated.** 73 inherited tests + ABC + `PriceCache` already worked; only browser-level SSE integration needed (APP-04 in Phase 1). Saved ~2 phases of re-planning.
- **Two-tier test strategy: Vitest at component + Playwright at integration.** 111/111 Vitest across 19 files caught component regressions cheaply; canonical Playwright harness caught cross-component drift only it could catch.
- **Auto-execution of LLM trades through the manual-trade validation path.** Single source of truth for trade rules; agentic chat trades and manual TradeBar trades visually identical (shared 800ms flash, same error map).
- **Phase 11 doc-sweep closure pattern.** When the milestone audit returned `tech_debt`, a dedicated phase closed the 5 process gaps (G1-G5) without touching production source. Verdict shifted to `passed`. Pattern: separate the runtime green from the paper trail.
- **Option B for `human_needed` closure.** Preserve the `status: human_needed` enum (don't lie) and add a `human_acceptance: indefinite` sibling key with dated rationale. Honest paper trail; audit re-run accepts policy debt explicitly.

### What Was Inefficient

- **Phase 7 visual-feel UAT not closed within Phase 7.** Required Phase 11 plan 11-03 (G3 closure) to record indefinite acceptance. Cost: one extra plan.
- **REQUIREMENTS.md drift accumulated through Phases 5-10.** 19 rows stuck at Pending/In progress while their plans had landed. Plan 11-02 (G2 closure) swept all 19 in one pass. Going forward: each phase verifier should flip the traceability rows on the same atomic commit as the verification doc.
- **Phase 5 missing VERIFICATION.md until Phase 11 backfilled it.** Plan 11-01 (G1 closure) ran `gsd-verifier` retroactively. Going forward: don't move on from a phase without a verifier-produced VERIFICATION.md.
- **Plans 10-07 + 10-08 misdiagnosed Mode A failure as a Recharts tooltip issue.** Actual cause was viewport-driven layout overlap (1280×720 device default vs the spec's wide-screen contract) plus cross-run SQLite carry-over via persistent docker volume. Plan 10-09 corrected via `viewport: 1440×900` per-project + `tmpfs:/app/db` on test compose. Lesson: when the production design contract specifies a viewport, the test environment must match it.
- **Two post-milestone source commits (`73abc58` + `e79ad18`) landed outside any phase.** Required Plan 11-04 (G5 closure) to record them as a planning delta. Going forward: close the milestone before fixing post-verification regressions, OR open a small decimal phase to host the fixes.
- **Phase 8 UAT-3 chat HTTP 422 was a contract-drift bug at the wire boundary.** Frontend `postChat()` typed body as `{content: string}` while backend `ChatRequest` requires `{message: string}` with `extra="forbid"`. Backend tests sent the right shape; frontend tests didn't exercise the wire payload. Fixed in commit c2a2c88. Going forward: add a contract test that runs the actual frontend payload shape against the backend Pydantic model.
- **RETROSPECTIVE.md was not maintained throughout the milestone.** Created retrospectively at close. Going forward: append after each phase, not just at milestone close.
- **Several Phase 7 plan SUMMARYs lack `requirements-completed` frontmatter.** Caught and superseded by Plan 11-02 traceability sweep, but should be set per-plan.

### Patterns Established

- **Factory-closure routers everywhere.** `create_stream_router(cache)` (Phase 1), `create_portfolio_router(db, cache)` (Phase 3), `create_watchlist_router(db, cache, source)` (Phase 4), `create_chat_router(...)` (Phase 5). No module-level routers; fresh APIRouter per call avoids accumulated routes across factory invocations.
- **Pure-function services with FastAPI thinly wrapping.** Service layer takes `(conn, cache, *args)`, raises domain exceptions; route layer translates exceptions to HTTP status codes. Easy unit tests, easy reuse from chat auto-exec.
- **Idempotent CRUD with status discriminator over HTTP status.** Watchlist add/remove returns `status="added"|"exists"|"removed"|"not_present"` with HTTP 200 always; never 409/404. Lets LLM auto-exec branch on `status` without HTTP-code sniffing.
- **`useShallow` for any Zustand selector that synthesizes an object/array literal.** Without it, React 19's identity check throws "Maximum update depth exceeded." Caught in Plan 08-03 Heatmap; pattern documented.
- **Tailwind v4 CSS-first `@theme` + `:root` dual declaration for tree-shaking.** Phase 7-reserved tokens (accent-purple, surface-alt, etc.) need to land in compiled CSS even before utility classes use them.
- **Module-scoped pytest-asyncio fixtures.** `@pytest_asyncio.fixture(loop_scope="module", scope="module")` + `pytestmark = pytest.mark.asyncio(loop_scope="module")` + module-scoped `event_loop_policy` override required by pytest-asyncio 1.x.
- **Per-project Playwright viewport + `tmpfs:/app/db` on test-side appsvc.** Viewport matches the design contract; tmpfs gives canonical-command reproducibility without changing the canonical command.
- **`gsd-verifier` produces VERIFICATION.md as the closure artifact, not human assertion.** Pattern carried through Phase 11 plan 11-01 backfill.
- **Atomic commits per task with prefix `feat(NN-MM):` or `docs(NN-MM):`.** 364 commits across 51 plans = ~7 commits/plan; each plan `SUMMARY.md` lists exact commit SHAs for traceability.

### Key Lessons

1. **A detailed pre-existing spec is gold.** `planning/PLAN.md` carried this milestone end-to-end with no redesign. Reach for an existing spec before drafting a new one.
2. **Close paper trail in the same phase as the runtime work.** Drift between code and planning docs (G1, G2, G5) cost an entire closure phase. Each verifier pass should flip its traceability rows.
3. **Test the actual wire payload, not what the backend expects.** UAT-3 422 was a backend-test blind spot that frontend tests also missed. Add at least one contract test per HTTP boundary that exercises the frontend body shape against the backend Pydantic model.
4. **Trust enum-preservation patterns when paper-trailing accepted policy debt.** Mutating `human_needed` → `passed` would lie about the artifact; adding a `human_acceptance: indefinite` sibling key + dated rationale is honest and audit-stable.
5. **Match the test environment to the design contract.** Viewport, locale, color scheme, motion preferences — if the production design assumes them, the test config must set them. Default device profiles produce phantom failures.
6. **`tmpfs` over `down -v` for compose reproducibility.** Doesn't require changing the canonical command, doesn't require a wrapper, doesn't require a test-only application endpoint, and the production VOLUME is preserved unchanged.

### Cost Observations

- **Model mix:** Predominantly Opus 4.6/4.7 across discuss/plan/execute phases; Sonnet 4.5/4.6 for high-throughput verification and code-review subagents.
- **Sessions:** Distributed across ~9 days; most phases consumed 1-3 sessions.
- **Notable:** Phase 6 plan 06-01 ran 1h 5m (frontend scaffold + Tailwind v4 CSS-first migration); other plans averaged 5-15 minutes. Single-task atomic plan structure kept cycle time low.
- **Auto-advance was disabled** (`workflow.auto_advance: false`) — every phase transition required explicit `/gsd-next` or equivalent. Trade-off: more checkpoints, less autonomous flight.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 11 | 51 | Initial milestone — adopted `planning/PLAN.md` wholesale; introduced Phase 11 doc-sweep closure pattern; Option B `human_needed` enum-preservation; per-project Playwright viewport contract; tmpfs over compose-down for E2E reproducibility. |

### Cumulative Quality

| Milestone | Tests (Vitest + pytest + E2E) | E2E Pass Rate | Zero-Production-Source Closure Phases |
|-----------|-------------------------------|---------------|--------------------------------------|
| v1.0 | 111 Vitest + ~600 pytest + 21 Playwright | 21/21 × 2 consecutive runs (100%) | 1 (Phase 11) |

### Top Lessons (Verified Across Milestones)

*(Will populate as v1.1+ retrospectives validate v1.0 lessons.)*

1. *(pending v1.1)* — Validate: "Detailed pre-existing spec carries a milestone end-to-end" — does v1.1 hold this if the next milestone has thinner spec coverage?
2. *(pending v1.1)* — Validate: "Close paper trail in the same phase as runtime work" — does the per-phase verifier-flips-traceability-rows pattern actually prevent the G2-style drift?

---

*Living document. Append a new `## Milestone:` section after each `/gsd-complete-milestone`.*
