# Milestones — FinAlly

Historical record of shipped versions.

---

## v1.0 — MVP (AI Trading Workstation)

**Shipped:** 2026-04-28
**Phases:** 1-11 (11 total) | **Plans:** 51 | **Tasks:** 200+ across 51 plan summaries
**Files modified:** 418 (98,290 net insertions)
**LOC:** Python 7,721 · TypeScript 4,292 · Tests 2,352
**Timeline:** 9 days (2026-04-19 → 2026-04-28)
**Git:** 364 commits (63 `feat`)
**Tag:** `v1.0`

**Delivered:** A single-Docker-command Bloomberg-style AI trading workstation — live SSE price streaming for 10 default tickers, a simulated $10k portfolio with instant-fill market orders, a three-column terminal layout plus a collapsible LLM chat copilot that auto-executes trades and watchlist changes via structured outputs, all served by FastAPI on `:8000` from a single multi-stage container.

### Key Accomplishments

1. Single-Docker-command Bloomberg-style trading terminal at `localhost:8000` (canonical demo moment).
2. Live SSE price streaming + simulated $10k portfolio with instant-fill market orders + 60s P&L snapshots.
3. AI copilot via LiteLLM/OpenRouter/Cerebras `gpt-oss-120b` with structured-output auto-execution; `LLM_MOCK=true` deterministic path.
4. Treemap heatmap (Recharts) + P&L line chart (dotted $10k reference, stroke flips at break-even) + collapsible AI chat drawer with action cards, XSS guard, prefers-reduced-motion.
5. Multi-stage Docker (Node 20 → Python 3.12 slim) + idempotent macOS/Linux + Windows start/stop scripts + `.env.example`.
6. 21/21 Playwright E2E green × 2 consecutive canonical-harness runs (0 failed, 0 flaky) across chromium/firefox/webkit at viewport 1440×900.
7. Phase 11 doc-sweep closure: all 5 audit gaps (G1-G5) closed without touching production source.

### Audit Verdict

**`passed`** — 40/40 functional requirements satisfied; 9/9 cross-phase wiring links pass; 7/7 E2E user flows pass green × 3 browsers × 2 consecutive runs. Audit doc: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`.

### Known Deferred Items at Close

2 items acknowledged as accepted policy debt (see `.planning/STATE.md` ## Deferred Items):
- Phase 07 VERIFICATION.md `human_needed` (indefinite acceptance per G3 closure — visual feel deferred; canonical Phase 10 harness covers all automated SCs)
- Phase 09 VERIFICATION.md `human_needed` (indefinite acceptance per G4 closure — Windows pwsh + browser auto-open + cross-arch buildx deferred to per-host human spot-check)

### Archives

- `.planning/milestones/v1.0-ROADMAP.md` — full phase details and milestone summary
- `.planning/milestones/v1.0-REQUIREMENTS.md` — 40/40 v1 requirements with frozen traceability
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — final audit (verdict: passed)
- `.planning/reports/MILESTONE_SUMMARY-v1.0.md` — onboarding/review summary

---

*This index keeps a constant-size record of every shipped milestone. Active development goes in ROADMAP.md.*
