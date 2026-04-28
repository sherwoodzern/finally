# Phase 11: Milestone v1.0 Closure & Doc Sweep — Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 5 (1 NEW, 4 MODIFY)
**Analogs found:** 5 / 5
**Scope:** documentation-only — `.planning/` and `.planning/reports/` only; **no production source files touched**

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| **NEW** `.planning/phases/05-ai-chat-integration/05-VERIFICATION.md` (G1) | verification doc (gsd-verifier output) | doc-write (one-shot) | `.planning/phases/04-watchlist-api/04-VERIFICATION.md` | exact (same role, same data flow, same agent author, comparable SC count) |
| **MODIFY** `.planning/REQUIREMENTS.md` (G2 — flip 15 rows + verify coverage count) | traceability table | row-by-row edit | Existing rows already at `Complete (Plan ...)` (APP-01, APP-03, APP-04, PORT-01..04, FE-05, FE-06, FE-09, OPS-01..04, TEST-02..04) | exact (same file, same row format) |
| **MODIFY** `.planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` (G3) | acceptance-decision frontmatter edit | YAML frontmatter mutation | Phase 7's own existing frontmatter (`status: human_needed` + `human_verification:` block) | exact (same file, same enum surface) |
| **MODIFY** `.planning/phases/09-dockerization-packaging/09-VERIFICATION.md` (G4) | acceptance-decision frontmatter edit | YAML frontmatter mutation | Phase 9's own existing frontmatter (`status: human_needed` + `human_verification:` block) | exact |
| **MODIFY** `.planning/reports/MILESTONE_SUMMARY-v1.0.md` (G5 — §6 entry; G3/G4 rationale if Option B) | milestone-summary `## 6.X` subsection | append/promote | §6.3 (post-milestone fixes) already lists both commits in a table; §6.1 is the cleanest analog for an indefinite-`human_needed` rationale entry | exact (same file, same section style) |

---

## Pattern Assignments

### `.planning/phases/05-ai-chat-integration/05-VERIFICATION.md` (G1, NEW)

**Analog:** `.planning/phases/04-watchlist-api/04-VERIFICATION.md` (canonical) + `.planning/phases/10-e2e-validation/10-VERIFICATION.md` (most-recent verifier output) + `.planning/phases/01-app-shell-config/01-VERIFICATION.md` (must-haves-style frontmatter)

**Author:** spawn `gsd-verifier` sub-agent (per RESEARCH.md "Pattern 1"). gsd-verifier writes the file from the analog template; the planner's plan should embed the agent invocation contract (target phase, slug, SCs, evidence inputs).

**Frontmatter pattern** (from `04-VERIFICATION.md` lines 1-13):

```yaml
---
phase: 05-ai-chat-integration
verified: 2026-04-28T00:00:00Z      # gsd-verifier sets to actual run time
status: passed                       # MUST be "passed" — audit already certified Phase 5 functional
score: 7/7 success criteria verified # SCs are CHAT-01..06 + TEST-01
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---
```

**Note (re_verification block):** This is an **initial** verification (Phase 5 has never had a VERIFICATION.md), so the block is empty per `04-VERIFICATION.md` — it's NOT a re-verification despite the audit-trail-backfill framing. Match the 04 shape, not the 10 shape (which has populated `gaps_closed`).

**Header pattern** (from `04-VERIFICATION.md` lines 15-21):

```markdown
# Phase 5: AI Chat Integration Verification Report

**Phase Goal:** [verbatim from ROADMAP.md Phase 5 §Goal lines 89-90: "A chat message posts to /api/chat, the LLM responds with a structured JSON answer, any trades or watchlist changes it proposes auto-execute through the same validation path as manual trades, and the full backend test suite passes for the feature set delivered so far."]

**Verified:** 2026-04-28T00:00:00Z
**Status:** passed
**Re-verification:** No — initial verification
```

**Section structure** (canonical, from `04-VERIFICATION.md` and `10-VERIFICATION.md`):

```
## Goal Achievement
  ### Observable Truths (ROADMAP Success Criteria + Plan must_haves)   <- table: # | Truth | Status | Evidence
  ### Required Artifacts (Plan 05-01 + 05-02 + 05-03 must_haves)        <- table: Artifact | Expected | Status | Details
  ### Key Link Verification                                              <- table: From | To | Via | Status | Details
  ### Data-Flow Trace (Level 4)                                          <- table: Artifact | Data Variable | Source | Produces Real Data | Status
  ### Behavioral Spot-Checks                                             <- table: Behavior | Command | Result | Status
  ### Requirements Coverage                                              <- table: Requirement | Source Plan | Description | Status | Evidence
  ### Anti-Patterns Found                                                <- table; "(none)" row if clean
  ### Human Verification Required                                        <- "None." paragraph if fully automated
  ### Gaps Summary                                                       <- prose paragraph
---
*Verified: <ISO ts>*
*Verifier: Claude (gsd-verifier)*
```

**Observable Truths SC list** (from ROADMAP.md Phase 5 lines 92-97 — verbatim, 5 SCs that map to 7 REQ-IDs CHAT-01..06 + TEST-01):

```
SC-1 (CHAT-01): POST /api/chat returns synchronous JSON with message + executed trades[] + watchlist_changes[]
SC-2 (CHAT-02): LiteLLM → OpenRouter → openrouter/openai/gpt-oss-120b with Cerebras provider, structured outputs
SC-3 (CHAT-03): Prompt includes cash, positions+P&L, watchlist+prices, total value, recent chat history
SC-4 (CHAT-04, CHAT-05): Auto-execute trades + watchlist_changes through manual-trade validation; persist user + assistant turns with actions JSON
SC-5 (CHAT-06, TEST-01): LLM_MOCK=true returns deterministic canned responses; extended pytest suite green
```

**Evidence inputs gsd-verifier consumes** (from RESEARCH.md "Pattern 1" §Evidence inputs — already cited verbatim there; planner copies into plan 11-01):

- `.planning/phases/05-ai-chat-integration/05-01-SUMMARY.md` (CHAT-02, CHAT-03, CHAT-06)
- `.planning/phases/05-ai-chat-integration/05-02-SUMMARY.md` (CHAT-04, CHAT-05)
- `.planning/phases/05-ai-chat-integration/05-03-SUMMARY.md` (CHAT-01, CHAT-05; frontmatter `requirements-completed: [CHAT-01, CHAT-05, TEST-01]`)
- `.planning/phases/05-ai-chat-integration/05-VALIDATION.md` line 65 + 155 (`295 passed`, `app.chat coverage 99.17%`)
- `.planning/phases/05-ai-chat-integration/05-UAT.md`
- `.planning/v1.0-MILESTONE-AUDIT.md` lines 21, 90, 144, 150
- `test/06-chat.spec.ts` (Playwright spec, green ×3 browsers ×2 runs)
- `backend/app/chat/` (production code — read-only inspection for invariants)

**Concrete excerpt — Observable Truths table (from `04-VERIFICATION.md` lines 27-32):**

```markdown
| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | GET /api/watchlist returns the current watchlist rows, each including the latest price from the in-memory cache | VERIFIED | `test_routes_get.py::TestGetWatchlist::test_returns_ten_seeded_tickers_with_prices` passes — asserts 10 seeded tickers returned with `price is not None` and `direction in ("up","down","flat")`. Service wiring `backend/app/watchlist/service.py:37-83` reads DB rows then calls `cache.get(ticker)` for each. |
```

**Concrete excerpt — Requirements Coverage table (from `04-VERIFICATION.md` lines 92-96):**

```markdown
| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WATCH-01 | 04-01, 04-02 | GET /api/watchlist returns user's watchlist with latest prices from the cache | SATISFIED | `service.get_watchlist(conn, cache)` + `routes.py::get_watchlist_route` + 4 service tests + 3 integration tests (`test_routes_get.py`) all green |
```

For Phase 5, the analogous row (planner can pre-fill in plan 11-01 acceptance criteria) is:

```markdown
| CHAT-01 | 05-03 | POST /api/chat synchronous response | SATISFIED | 05-03-SUMMARY frontmatter `requirements-completed: [CHAT-01, CHAT-05, TEST-01]`; routes integration tests; `06-chat.spec.ts` ×3 browsers ×2 runs |
```

**Concrete excerpt — Behavioral Spot-Checks table (from `04-VERIFICATION.md` lines 82-86):**

```markdown
| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Watchlist + lifespan test suite passes | `uv run --extra dev pytest tests/watchlist/ tests/test_lifespan.py -v` | 62 passed | PASS |
| Full backend test suite passes | `uv run --extra dev pytest -q` | 207 passed, 0 failed, 0 errors | PASS |
```

For Phase 5, the canonical evidence (from `05-VALIDATION.md` lines 65, 155): `295 passed`, `app.chat coverage 99.17%`.

**Sign-off footer pattern** (from `04-VERIFICATION.md` lines 129-132):

```markdown
---

*Verified: 2026-04-28T00:00:00Z*
*Verifier: Claude (gsd-verifier)*
```

**Acceptance grep contract for plan 11-01** (from RESEARCH.md "Validation Architecture" Phase Requirements → Test Map row 1):

```bash
test -f .planning/phases/05-ai-chat-integration/05-VERIFICATION.md \
  && grep -q "phase: 05-ai-chat-integration" .planning/phases/05-ai-chat-integration/05-VERIFICATION.md \
  && grep -q "^status: passed" .planning/phases/05-ai-chat-integration/05-VERIFICATION.md \
  && for r in CHAT-01 CHAT-02 CHAT-03 CHAT-04 CHAT-05 CHAT-06 TEST-01; do
       grep -q "$r" .planning/phases/05-ai-chat-integration/05-VERIFICATION.md || { echo "MISSING $r"; exit 1; }
     done
```

---

### `.planning/REQUIREMENTS.md` (G2, MODIFY)

**Analog:** the file's own already-correct rows. The canonical "Complete" row format is **on disk in the same table** at lines 130-133, 137-140, 151-152, 155-156, 159, 161-165, 167-169.

**Concrete excerpt — canonical "Complete" row format** (verbatim from `.planning/REQUIREMENTS.md` lines 130-133):

```markdown
| APP-01 | Phase 1 | Complete (01-01, 01-02) |
| APP-02 | Phase 8 | Complete (08-01 mount + G1 fix; 08-08 final build artifact) |
| APP-03 | Phase 1 | Complete (01-01, 01-02) |
| APP-04 | Phase 1 | Complete (01-03) |
```

**Decision rule (from observed data):**
- The `Phase` column does NOT include the word "Phase" in the status string — the phase number is implied by the second column.
- The status string format is **`Complete (<plan-id>[, <plan-id>]...[ — <one-line note>])`** where plan-IDs are written as `NN-MM` (without the "Plan " prefix used in some prose).
- When a REQ landed across multiple plans, list them comma-separated. Optional `;`-separated suffix for human notes (see APP-02 row).

**The 15 rows to flip** (from RESEARCH.md "Evidence Map" — already pre-computed, copy verbatim into plan 11-02):

Current state (REQUIREMENTS.md lines 134-136, 141-150, 153-154, 157-158, 160, 166):

```markdown
| DB-01 | Phase 2 | Pending |
| DB-02 | Phase 2 | Pending |
| DB-03 | Phase 2 | Pending |
| PORT-05 | Phase 3 | Pending (03-03 — observer wiring) |
| WATCH-01 | Phase 4 | In progress (04-01 service layer; 04-02 adds HTTP route) |
| WATCH-02 | Phase 4 | In progress (04-01 service layer; 04-02 adds HTTP route) |
| WATCH-03 | Phase 4 | In progress (04-01 service layer; 04-02 adds HTTP route) |
| CHAT-01 | Phase 5 | Pending |
| CHAT-02 | Phase 5 | Pending |
| CHAT-03 | Phase 5 | Pending |
| CHAT-04 | Phase 5 | Pending |
| CHAT-05 | Phase 5 | Pending |
| CHAT-06 | Phase 5 | Pending |
| FE-03 | Phase 7 | Pending |
| FE-04 | Phase 7 | Pending |
| FE-07 | Phase 7 | Pending |
| FE-08 | Phase 7 | Pending |
| FE-10 | Phase 7 | Pending |
| TEST-01 | Phase 5 | Pending |
```

Target state (apply RESEARCH.md "Evidence Map" mapping):

```markdown
| DB-01 | Phase 2 | Complete (02-01, 02-02) |
| DB-02 | Phase 2 | Complete (02-01, 02-02) |
| DB-03 | Phase 2 | Complete (02-02; volume persistence proven by 09-VERIFICATION SC#6) |
| PORT-05 | Phase 3 | Complete (03-02 inline post-trade snapshot; 03-03 60s observer in lifespan) |
| WATCH-01 | Phase 4 | Complete (04-01, 04-02) |
| WATCH-02 | Phase 4 | Complete (04-01, 04-02) |
| WATCH-03 | Phase 4 | Complete (04-01, 04-02) |
| CHAT-01 | Phase 5 | Complete (05-03) |
| CHAT-02 | Phase 5 | Complete (05-01) |
| CHAT-03 | Phase 5 | Complete (05-01) |
| CHAT-04 | Phase 5 | Complete (05-02) |
| CHAT-05 | Phase 5 | Complete (05-02, 05-03) |
| CHAT-06 | Phase 5 | Complete (05-01) |
| FE-03 | Phase 7 | Complete (07-01, 07-03) |
| FE-04 | Phase 7 | Complete (07-04) |
| FE-07 | Phase 7 | Complete (07-05) |
| FE-08 | Phase 7 | Complete (07-06) |
| FE-10 | Phase 7 | Complete (07-07) |
| TEST-01 | Phase 5 | Complete (05-03; 295/295 backend tests + 99.17% app.chat coverage per 05-VALIDATION.md) |
```

**Coverage count line** (REQUIREMENTS.md lines 171-174 — `grep`-VERIFY UNCHANGED, do NOT re-increment):

```markdown
**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40 (100%)
- Unmapped: 0
```

**Last-updated footer line** (REQUIREMENTS.md line 178 — UPDATE to today):

Current:
```markdown
*Last updated: 2026-04-26 after Phase 8 completion (APP-02, FE-05, FE-06, FE-09, FE-11, TEST-02 validated; 5/5 automated must-haves PASSED, 6 perceptual items deferred to 08-HUMAN-UAT.md)*
```

Target shape (planner authors the new line; follow same pattern of `*Last updated: <date> after <event>*`):
```markdown
*Last updated: 2026-04-28 after Phase 11 milestone-closure sweep (G2 — flipped 15 status-drift rows from Pending/In progress to Complete with plan-ID evidence; coverage count unchanged at 40/40)*
```

**Acceptance grep contract for plan 11-02** (from RESEARCH.md "Validation Architecture" rows 3-4):

```bash
# After sweep, no row in the table reads "Pending" or "In progress" for the 19 affected REQ-IDs:
grep -E "^\| (DB-0[123]|PORT-05|WATCH-0[123]|CHAT-0[1-6]|FE-0[34]|FE-0[78]|FE-10|TEST-01) " .planning/REQUIREMENTS.md \
  | grep -cE "Pending|In progress"
# Expected: 0

# Coverage count line still 40/40:
grep -q "v1 requirements: 40 total" .planning/REQUIREMENTS.md \
  && grep -q "Mapped to phases: 40 (100%)" .planning/REQUIREMENTS.md
# Expected: exit 0
```

---

### `.planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` (G3, MODIFY frontmatter)

**Analog:** Phase 7's own existing frontmatter at lines 1-39 (verbatim copy reproduced below).

**Concrete excerpt — current frontmatter** (lines 1-39):

```yaml
---
phase: 07-market-data-trading-ui
verified: 2026-04-24T23:45:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: 0/0
  gaps_closed: []
  gaps_remaining: []
  regressions: []
requirements:
  - FE-03
  - FE-04
  - FE-07
  - FE-08
  - FE-10
created: 2026-04-24
human_verification:
  - test: "Open http://localhost:8000 with backend running; observe the watchlist tickers"
    expected: "On every tick, the price cell briefly flashes green (uptick) or red (downtick) and fades out within ~500ms..."
    why_human: "CSS transition feel and browser repaint cadence cannot be verified by Vitest mocks of lightweight-charts"
  # ... 5 more visual-feel items (lines 24-38)
---
```

**Mutation pattern — Option A** (bump to passed; planner's choice if user signs off visual feel):

Replace `status: human_needed` with `status: passed` and **append** an `## Acceptance` section to the body (NOT a frontmatter key — keep frontmatter schema clean per RESEARCH.md Pitfall 3).

```yaml
status: passed
```

Body append (after the last existing section, before the `*Verified: ...*` footer):

```markdown
## Acceptance

**Accepted:** 2026-04-28 by S. Zern.

The 6 `human_verification` items above describe visual feel (price-flash cadence, sparkline canvas, click-to-select, instant-fill UX, EventSource state-machine dot, three-column aesthetic). The runtime behavior underlying every item is exercised end-to-end by the canonical Phase 10 harness (7 specs × 3 browsers × 2 consecutive runs = 21 passed × 2, 0 failed, 0 flaky, `Container test-appsvc-1 Healthy`). The "feel" is the only deferred item; the user has signed off on the live demo.

Phase 7 status moves from `human_needed` to `passed`.
```

**Mutation pattern — Option B** (recommended per RESEARCH.md "Pattern 3"; indefinite human_needed accepted with rationale):

Keep `status: human_needed` and **add a sibling `human_acceptance` key** to the frontmatter, with a `rationale:` block citing harness evidence:

```yaml
status: human_needed
human_acceptance: indefinite
human_acceptance_recorded: 2026-04-28
human_acceptance_rationale: |
  All 6 human_verification items are visual-feel checks (CSS price-flash cadence,
  Lightweight Charts sparkline canvas, click-to-select cross-panel flow, instant-fill
  UX, EventSource reconnect state-machine dot, three-column Bloomberg-style aesthetic).
  The runtime behavior underlying every item is exercised by the canonical Phase 10
  harness (7 specs × 3 browsers × 2 consecutive runs = 21 passed × 2, 0 failed, 0 flaky,
  Container test-appsvc-1 Healthy). The "feel" is the only deferred item. Recorded
  here as accepted policy debt for v1.0 milestone closure.
```

**Critical:** Do NOT invent new `status:` enum values like `accepted_with_debt`. Only `passed`, `gaps_found`, `human_needed` are valid (per RESEARCH.md Pitfall 3). Option B preserves the existing enum value and adds new sibling keys.

**Acceptance grep contract for plan 11-03 (G3 portion)** (from RESEARCH.md row 5):

```bash
# Option A:
grep -q "^status: passed" .planning/phases/07-market-data-trading-ui/07-VERIFICATION.md
# OR Option B:
grep -q "^human_acceptance: indefinite" .planning/phases/07-market-data-trading-ui/07-VERIFICATION.md
```

---

### `.planning/phases/09-dockerization-packaging/09-VERIFICATION.md` (G4, MODIFY frontmatter)

**Analog:** Phase 9's own existing frontmatter at lines 1-20.

**Concrete excerpt — current frontmatter** (lines 1-20):

```yaml
---
phase: 09-dockerization-packaging
verified: 2026-04-27T11:25:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Windows-host UAT for PowerShell scripts (start_windows.ps1, stop_windows.ps1)"
    expected: "Same idempotency + volume-preserving stop behavior as the bash counterparts..."
    why_human: "pwsh is not installed on the integration-test host (macOS), so PowerShell scripts were validated by structural grep only..."
  - test: "Browser auto-open behavior on macOS / Linux start_mac.sh success"
    # ...
  - test: "Visual UI on http://localhost:8000 (after `bash scripts/start_mac.sh`)"
    # ...
  - test: "Cross-arch build (linux/amd64 vs linux/arm64) on the user's primary host architecture"
    # ...
---
```

**Mutation pattern — same shape as G3 above.** Apply identical Option A or Option B to Phase 9. RESEARCH.md "Pattern 3" recommends Option B for both phases for consistency.

**Option B rationale (Phase 9 specific):**

```yaml
status: human_needed
human_acceptance: indefinite
human_acceptance_recorded: 2026-04-28
human_acceptance_rationale: |
  All 4 human_verification items are platform/visual checks (Windows pwsh runtime,
  macOS browser auto-open, visual UI of the live terminal, cross-arch buildx). The
  structural validation in 09-VERIFICATION.md SC#1-#11 passes (Dockerfile invariants,
  .dockerignore exclusions, .env.example shape, idempotent scripts, integration-test
  PASS on the canonical run command). The macOS/Linux demo path is fully proven; the
  Windows pwsh runtime, browser auto-open, and visual UI are deferred to per-host
  human spot-check. Recorded here as accepted policy debt for v1.0 milestone closure.
```

**Acceptance grep contract for plan 11-03 (G4 portion):**

```bash
# Option A:
grep -q "^status: passed" .planning/phases/09-dockerization-packaging/09-VERIFICATION.md
# OR Option B:
grep -q "^human_acceptance: indefinite" .planning/phases/09-dockerization-packaging/09-VERIFICATION.md
```

---

### `.planning/reports/MILESTONE_SUMMARY-v1.0.md` (G5, MODIFY §6 entry)

**Analog:** §6.3 of `MILESTONE_SUMMARY-v1.0.md` itself, lines 110-118 (already lists the two G5 commits in a table). The G5 closure is a **promotion of framing** ("tech debt" → "post-milestone planning record") — not a brand-new entry. If Option B is chosen for G3/G4, §6.1 also gets extended.

**Concrete excerpt — existing §6.3** (verbatim, lines 110-118):

```markdown
### 6.3 — Post-milestone fixes not retrofitted into a phase
Two source-impacting commits landed AFTER the verifier marked Phase 10 `passed`. Both are green under the canonical harness, but neither belongs to a phase:

| Commit | Fix | Why it surfaced post-verification |
|---|---|---|
| `73abc58` | Heatmap + P&L charts render at deterministic 360px height | The Playwright spec asserted `toBeVisible()` on the wrapper div, which passed even when Recharts emitted a 0×0 inner div under React 19 + ResponsiveContainer + flex-1 parent. The user noticed the empty charts in the live demo. **Verification gap also closed in `05-portfolio-viz.spec.ts` (now asserts `svg rect` and `svg path` count > 0).** |
| `e79ad18` | Light theme (white surfaces / dark text) | User-requested polish after verification; not a regression. CSS variable flip in `globals.css` + matching hex updates in chart components. |

If a v1.1 / Phase 10.1 is desired, both commits can be retroactively assigned. Otherwise, surface them as pre-archive notes.
```

**Mutation pattern — G5 closure (lightweight, recommended per RESEARCH.md "Pattern 4"):**

Promote §6.3 from tech-debt framing to a formal "post-milestone planning record" framing. Two edits:

1. **Rename heading** `### 6.3 — Post-milestone fixes not retrofitted into a phase` → `### 6.3 — Post-milestone planning record (commits 73abc58, e79ad18)`.

2. **Append a "Status" line** below the table:

```markdown
**Status:** Recorded as planning delta on 2026-04-28 (Phase 11 closure, gap G5). Both commits are functionally green under the canonical harness (`21 passed × 2 consecutive runs`); they are accepted as post-Phase-10 polish landed before milestone archive. No retroactive Phase 10.1 SUMMARY required (per Phase 11 RESEARCH "Pattern 4" lightweight option; preserves ROADMAP plan count at 47 and STATE.md `completed_plans: 47` invariants — see Phase 11 RESEARCH "Pitfall 4").
```

**Section-style pattern across MILESTONE_SUMMARY-v1.0.md** (numbered headings already established — `## 1. Project Overview`, `## 2. Architecture & Technical Decisions`, …, `## 6. Tech Debt & Deferred Items` with `### 6.1`, `### 6.2`, …, `### 6.5`):

The file's existing §6 numbering pattern is `### 6.<digit> — <title>`. Any new subsection MUST follow this pattern. The next available slot is `### 6.6`.

**Mutation pattern — G3/G4 indefinite-acceptance entry (only if Option B chosen for plan 11-03):**

Add a NEW `### 6.6` subsection after §6.5 (out-of-scope), following §6.1's prose style:

```markdown
### 6.6 — Indefinite human_needed acceptance (Phase 7 + Phase 9)

Both phases retain `status: human_needed` in their VERIFICATION.md frontmatter, with a sibling `human_acceptance: indefinite` key recording acceptance as policy debt:

- **Phase 7 (07-market-data-trading-ui).** 6 visual-feel items (price-flash CSS cadence, Lightweight Charts sparkline canvas, click-to-select, instant-fill UX, EventSource state-machine dot, three-column Bloomberg aesthetic). Runtime behavior fully exercised by canonical Phase 10 harness (`21 passed × 2 consecutive runs`).
- **Phase 9 (09-dockerization-packaging).** 4 platform/visual items (Windows pwsh runtime, macOS browser auto-open, visual UI on the live terminal, cross-arch buildx). Structural validation green (`11/11 must-haves verified`); macOS/Linux demo path fully proven; Windows pwsh + visual UI deferred to per-host human spot-check.

Recorded 2026-04-28 as accepted v1.0 milestone closure debt. The `/gsd-audit-milestone v1.0` re-run after Phase 11 should classify these as `policy_debt`, not `tech_debt`.
```

**Anti-pattern (RESEARCH.md Pitfall 4):** Do NOT create `.planning/phases/10-e2e-validation/10-10-SUMMARY.md`. The lightweight §6 promotion preserves Phase 10 plan count at 10/10 and STATE.md `completed_plans: 47` invariants. The "heavier" Phase 10.1 retrofit option in RESEARCH.md is explicitly NOT recommended.

**Acceptance grep contract for plan 11-04 (G5 portion)** (from RESEARCH.md row 7):

```bash
# Both commit SHAs present:
grep -q "73abc58" .planning/reports/MILESTONE_SUMMARY-v1.0.md \
  && grep -q "e79ad18" .planning/reports/MILESTONE_SUMMARY-v1.0.md

# "planning record" or "planning delta" framing present (NOT just "tech debt"):
grep -qE "(planning record|planning delta)" .planning/reports/MILESTONE_SUMMARY-v1.0.md
```

---

## Shared Patterns

### Shared Pattern 1: Frontmatter discipline (G1, G3, G4)

**Source:** every existing VERIFICATION.md frontmatter (canonical: `04-VERIFICATION.md` lines 1-13; `01-VERIFICATION.md` lines 1-7; `10-VERIFICATION.md` lines 1-17; `07-VERIFICATION.md` lines 1-39; `09-VERIFICATION.md` lines 1-20).

**Apply to:** plans 11-01 and 11-03.

**Rules** (all derived from observed on-disk patterns):

1. **`status:` is an enum.** Only three values exist in the codebase: `passed`, `gaps_found`, `human_needed`. Do not invent new values (Pitfall 3).
2. **`score:` is a fraction.** Format: `<met>/<total> must-haves verified` (Phases 1, 4, 9, 10) or `<met>/<total> success criteria verified` (Phase 4 also uses this) — both forms are observed. Match the analog you copy from.
3. **ISO timestamps with `T` and `Z`.** Format `YYYY-MM-DDTHH:MM:SSZ` — no offset notation, always UTC-Z.
4. **`re_verification:` block is optional but should be present.** For initial verifications, all sub-keys are empty (`previous_status: null`, `gaps_closed: []`, etc.). For re-verifications, populate `gaps_closed` with detail strings (10-VERIFICATION.md lines 10-13 is the canonical example).
5. **`human_verification:` is a list of `{test, expected, why_human}` triples.** Phase 7 has 6 items, Phase 9 has 4 items. The triple shape is uniform across phases.
6. **New custom keys (e.g. `human_acceptance:`) are added as siblings, not nested.** Frontmatter is flat per phase; only `re_verification:` and `human_verification:` use nested structures.
7. **Sign-off footer is uniform:** `*Verified: <ISO ts>*` then `*Verifier: Claude (gsd-verifier)*`. Some phases (e.g. `10-VERIFICATION.md` line 210) add a third `*Evidence: ...*` line; this is optional and acceptable.

### Shared Pattern 2: Plan-ID format in REQUIREMENTS.md (G2)

**Source:** REQUIREMENTS.md lines 130-169.

**Apply to:** plan 11-02.

**Rules:**

- Format: `Complete (NN-MM[, NN-MM]...[ — <one-line note>])` — plan-IDs are bare `NN-MM`, not "Plan NN-MM".
- Multiple plans: comma-separated, ascending plan-ID order (`02-01, 02-02`).
- Optional trailing note: `;`-separated for human context (see `Complete (08-01 mount + G1 fix; 08-08 final build artifact)` for APP-02).
- The `Phase` column always begins with `Phase ` and is the second pipe-cell (do not modify).

### Shared Pattern 3: §6 structure of MILESTONE_SUMMARY-v1.0.md (G5; G3/G4 if Option B)

**Source:** `.planning/reports/MILESTONE_SUMMARY-v1.0.md` lines 99-136 (§6 heading + §6.1..§6.5).

**Apply to:** plan 11-04 (and plan 11-03 if Option B chosen for G3/G4).

**Rules:**

- §6 heading is `## 6. Tech Debt & Deferred Items`.
- Subsections follow `### 6.<digit> — <Title>` pattern, with em-dash (`—`, not hyphen `-`) between number and title.
- Body is short prose followed by a table OR a bullet list; both styles co-exist (§6.1 is prose+bullet, §6.3 is prose+table, §6.5 is prose+bullet).
- New subsections append at the end (§6.6, §6.7, …) — do NOT renumber existing ones.

### Shared Pattern 4: Acceptance grep contract per plan

**Source:** RESEARCH.md "Validation Architecture" Phase Requirements → Test Map (lines 397-407).

**Apply to:** every plan in Phase 11.

Each plan's acceptance section MUST embed the grep block from RESEARCH.md verbatim, with expected exit codes documented. The Phase 11 brief is explicit: **acceptance is grep-verifiable file presence + canonical-string match. No test runs.**

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | Every Phase 11 target has a strong on-disk analog. The G3/G4 acceptance pattern (Option B's `human_acceptance:` sibling key) is novel YAML, but it's a non-disruptive extension of the existing frontmatter shape — no new file template needed. |

---

## Metadata

**Analog search scope:**
- `.planning/phases/*/[0-9][0-9]-VERIFICATION.md` — 9 files scanned (all phases except Phase 5 which has none — that absence IS the gap)
- `.planning/REQUIREMENTS.md` — 1 file scanned
- `.planning/reports/MILESTONE_SUMMARY-v1.0.md` — 1 file scanned
- `.planning/v1.0-MILESTONE-AUDIT.md` — 1 file scanned (frozen reference; not edited per RESEARCH.md anti-patterns)
- `.planning/ROADMAP.md` — 1 file scanned (Phase 11 SC source of truth)
- `.planning/phases/11-milestone-v1.0-closure/11-RESEARCH.md` — 1 file scanned (this phase's research)

**Files scanned:** 14
**Strong analogs identified:** 5 (one per Phase 11 target file)
**Pattern extraction date:** 2026-04-28

**Confidence:**
- G1 / 05-VERIFICATION.md template: **HIGH** — `04-VERIFICATION.md` is a structurally identical canonical analog (small phase, multiple SCs, single-agent author).
- G2 / REQUIREMENTS.md row format: **HIGH** — the file itself contains 25+ already-correct rows demonstrating the canonical format.
- G3/G4 frontmatter mutations: **HIGH** for Option A (status enum flip is well-defined); **MEDIUM** for Option B (`human_acceptance:` is a new sibling key but is a non-disruptive extension; planner should pick one and apply identically to both phases for consistency).
- G5 §6 entry: **HIGH** — `MILESTONE_SUMMARY-v1.0.md` already contains §6.1..§6.5 with established patterns; §6.6 follows the same shape.

**Closure note:** All 5 Phase 11 target files have concrete, copy-pasteable patterns extracted from on-disk analogs. The planner can author 11-01-PLAN.md through 11-04-PLAN.md with deterministic acceptance criteria (file-presence + grep) without further research.
