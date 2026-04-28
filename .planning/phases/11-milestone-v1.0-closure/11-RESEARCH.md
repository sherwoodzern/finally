# Phase 11: Milestone v1.0 Closure & Doc Sweep — Research

**Researched:** 2026-04-28
**Domain:** GSD process closure / planning-record reconciliation (NOT a build phase)
**Confidence:** HIGH

## Summary

This is a documentation/process closure phase. Production source is already green: 40/40
requirements functionally satisfied, 9/9 cross-phase wiring links pass, 7/7 E2E flows green
×3 browsers ×2 consecutive canonical-harness runs (`21 passed (24.6s)` / `21 passed (24.8s)`,
0 failed / 0 flaky / `Container test-appsvc-1 Healthy`). The milestone audit verdict is
`tech_debt` purely because of 5 process gaps in the `.planning/` tree.

Phase 11 closes those gaps in 4 small, deterministic, grep-verifiable plans. The 4 plans
match the ROADMAP's pre-named stubs (11-01..11-04) and map 1:1 onto gaps G1..G5 from
`.planning/v1.0-MILESTONE-AUDIT.md` (with 11-03 covering both G3 and G4 because they share
the same remediation pattern).

**Primary recommendation:** Adopt the ROADMAP's 4-plan split verbatim. Each plan touches
only the `.planning/` tree (plus a status comment in `MILESTONE_SUMMARY-v1.0.md` for G5)
and is independently verifiable by file presence + canonical-string grep. No production
source code changes, no test re-runs, no new requirements.

## User Constraints (from phase brief)

### Locked Decisions

- **ZERO production source code changes.** Only `.planning/` tree + `.planning/reports/`.
- **ZERO new requirements.** This phase ratifies (in planning records) the existing
  functional satisfaction of: CHAT-01..06, TEST-01, DB-01..03, PORT-05, WATCH-01..03,
  FE-03/04/07/08/10, OPS-02, OPS-03, FE-01, FE-05, FE-06, APP-02.
- **All evidence already exists** on disk (test run logs, harness output 21/21, prior
  phase VERIFICATION.md / SUMMARY.md files, git commits). Research → plan → execute must
  map evidence → claim, NOT re-prove anything.
- **gsd-verifier is the canonical way to backfill VERIFICATION.md** for G1 (Phase 5).
- **No test runs.** Acceptance is grep-verifiable file presence + canonical-string match.
- **Do NOT modify the audit document itself** (`.planning/v1.0-MILESTONE-AUDIT.md`) —
  it is the source of truth for what "closure" means and is frozen as the audit record.

### Claude's Discretion

- Plan ordering within Phase 11 (most plans are independent; see "Order/Dependencies").
- Choice between (a) bumping `human_needed` → `passed` with inline acceptance, or
  (b) accepting `human_needed` indefinitely with rationale (G3/G4 are policy choices).
- G5 record location: §6 entry in `MILESTONE_SUMMARY-v1.0.md` vs. a thin Phase 10.1
  SUMMARY (the ROADMAP allows either; the §6 entry is simpler and is already partially
  staged in `MILESTONE_SUMMARY-v1.0.md` lines 110-118).

### Deferred Ideas (OUT OF SCOPE)

- Re-running the canonical harness (already green twice).
- Re-verifying any phase besides Phase 5.
- Touching production source for any of the post-milestone commits.
- Adding RETROSPECTIVE.md (listed in audit tech_debt but NOT in Phase 11 SCs).
- Filling missing `requirements-completed` frontmatter on Phase 7 plan SUMMARYs (audit
  tech_debt §documentation but NOT in Phase 11 SCs).
- Promoting Nyquist `partial`/`missing` phases to `compliant` (advisory, audit §6).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| (none new) | Phase 11 ratifies existing satisfaction; no new REQ-IDs are introduced. | All evidence below maps to already-satisfied REQ-IDs from REQUIREMENTS.md. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Backfill Phase 5 VERIFICATION.md | Process / `.planning/` | gsd-verifier agent | gsd-verifier is the canonical writer for VERIFICATION.md; produces the file by inspecting Phase 5 SUMMARYs + UAT + VALIDATION + greps against backend/app/chat code. |
| REQUIREMENTS.md status drift sweep | Documentation / `.planning/REQUIREMENTS.md` | — | Pure markdown table edit; no agent spawn. |
| Record `human_needed` decision (Phase 7 + Phase 9) | Documentation / each phase's VERIFICATION.md | optionally `MILESTONE_SUMMARY-v1.0.md` §6 | Frontmatter status + inline acceptance note (option A) OR rationale-only (option B); both edit existing files. |
| Record post-milestone commits (G5) | Documentation / `MILESTONE_SUMMARY-v1.0.md` §6 | — | Section 6 already exists in summary doc; this plan extends it (or adds a thin Phase 10.1 SUMMARY — orchestrator's call). |

## Standard Stack

This is a documentation phase — no library or framework decisions to make.

| Tool | Purpose | Why |
|------|---------|-----|
| `gsd-verifier` (agent) | Backfill `05-VERIFICATION.md` | Canonical pattern. Compare with `04-VERIFICATION.md`, `07-VERIFICATION.md`, `10-VERIFICATION.md` for the expected output shape (frontmatter + Goal Achievement + Required Artifacts + Key Link Verification + Behavioral Spot-Checks + Requirements Coverage + Anti-Patterns Found + Gaps Summary). |
| `grep` / `awk` | Acceptance verification | Every Phase 11 SC reduces to "file exists" + "string X appears in file Y" (or "string X NO LONGER appears in file Y" for the REQUIREMENTS.md sweep). |
| `git log --oneline` | G5 evidence | Confirms commits `73abc58` and `e79ad18` exist with the documented messages. Already verified in this research session. |

**Installation:** None required. All tools are already in use across prior phases.

## Architecture Patterns

### Document-edit phase pattern (project-specific)

This phase mirrors `gsd-complete-milestone` housekeeping work, but executed as a regular
phase so the changes are tracked, reviewed, and committed atomically per gap. Each plan:

1. Reads existing on-disk evidence (cited verbatim below).
2. Edits or creates exactly the artifacts named in its acceptance criteria.
3. Acceptance is `test -f {path}` + `grep -q "{canonical-string}" {path}`.
4. No test execution. No source recompile. No agent invocation except gsd-verifier in 11-01.

### Recommended `.planning/phases/11-milestone-v1.0-closure/` Structure

```
.planning/phases/11-milestone-v1.0-closure/
├── 11-RESEARCH.md           # this file
├── 11-CONTEXT.md            # written by gsd-discuss-phase (if invoked)
├── 11-01-PLAN.md            # G1 closure
├── 11-01-SUMMARY.md         # produced after 11-01 executes
├── 11-02-PLAN.md            # G2 closure
├── 11-02-SUMMARY.md
├── 11-03-PLAN.md            # G3 + G4 closure
├── 11-03-SUMMARY.md
├── 11-04-PLAN.md            # G5 closure
├── 11-04-SUMMARY.md
├── 11-VALIDATION.md         # see Validation Architecture below
└── 11-VERIFICATION.md       # produced by gsd-verifier at phase end
```

### Pattern 1: gsd-verifier invocation for backfill (G1)

**What:** Spawn `gsd-verifier` as a sub-agent with Phase 5 as its target.
**When to use:** Plan 11-01 only.
**Inputs to provide:**
- Phase number: `5`
- Phase slug: `ai-chat-integration`
- Canonical SCs (from `.planning/ROADMAP.md` Phase 5 §"Success Criteria" lines 92-97):
  CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, TEST-01.
- Output target: `.planning/phases/05-ai-chat-integration/05-VERIFICATION.md`.
- Reference shape: `.planning/phases/04-watchlist-api/04-VERIFICATION.md` and
  `.planning/phases/07-market-data-trading-ui/07-VERIFICATION.md`.

**Evidence inputs gsd-verifier will consume (already on disk):**
- `.planning/phases/05-ai-chat-integration/05-01-SUMMARY.md` (models, LiveChatClient,
  MockChatClient, prompts, build_messages — CHAT-02, CHAT-03, CHAT-06).
- `.planning/phases/05-ai-chat-integration/05-02-SUMMARY.md` (run_turn, get_history,
  ChatTurnError, auto-exec ordering — CHAT-04, CHAT-05).
- `.planning/phases/05-ai-chat-integration/05-03-SUMMARY.md` (POST /api/chat,
  GET /api/chat/history, lifespan wiring — CHAT-01, CHAT-05; explicitly tagged
  `requirements-completed: [CHAT-01, CHAT-05, TEST-01]`).
- `.planning/phases/05-ai-chat-integration/05-VALIDATION.md` line 65 + line 155
  (`295/295 backend tests green`, `app.chat coverage 99.17%` — TEST-01 evidence).
- `.planning/phases/05-ai-chat-integration/05-UAT.md` (7/7 manual smoke tests pass).
- `.planning/v1.0-MILESTONE-AUDIT.md` lines 21, 90, 144, 150 (audit-corroborated
  295/295 + `06-chat.spec.ts` ×3×2 evidence).
- `test/06-chat.spec.ts` (Playwright spec exists).
- `backend/app/chat/` (production code — for greppable invariants).

**Why this is sufficient:** Phase 5 is functionally proven. gsd-verifier's job here is
audit-trail-only, not gap-detection.

### Pattern 2: Markdown table sweep (G2)

**What:** Edit `.planning/REQUIREMENTS.md` traceability table — flip 15 stale rows.
**When to use:** Plan 11-02.
**Mechanic:** Each row to flip is a single line in the `| Requirement | Phase | Status |`
table at lines 130-169. The edit pattern is:

```
| {REQ-ID} | Phase {N} | Pending  →  Complete (Plan {N-NN}, ...) |
```

For each REQ-ID, the plan-ID evidence must come from the plan's SUMMARY.md
`requirements-completed` frontmatter (where present) or from the SUMMARY's "Accomplishments"
section. See "Evidence Map" below for the precomputed mapping.

**Coverage count (top of REQUIREMENTS.md, lines 171-174):** Already correct
("v1 requirements: 40 total / Mapped to phases: 40 (100%) / Unmapped: 0"). No
mathematical change needed; the audit confirmed 40/40 functionally satisfied. Plan 11-02
should verify this line is still 40/40 and update the timestamp on line 178.

### Pattern 3: VERIFICATION.md status flip (G3 + G4)

**What:** Choose between (A) bump `human_needed → passed` with inline acceptance, or
(B) accept indefinite `human_needed` with rationale.
**When to use:** Plan 11-03 (covers both Phase 7 and Phase 9 in one plan).
**Recommendation (planner's call):** Option B for both. Rationale:
- Phase 7's `human_verification` block (07-VERIFICATION.md frontmatter lines 20-38) is
  6 visual-feel items. The harness (E2E ×3 browsers ×2 runs) exercises every flow these
  items describe — so the runtime behavior is proven, the "feel" is the only deferred
  item. Recording this as accepted policy debt is honest.
- Phase 9's `human_verification` block (09-VERIFICATION.md frontmatter lines 7-19) is
  Windows pwsh runtime + macOS browser auto-open + visual UI. The structural validation
  is in place; the missing items are not blockers for the macOS/Linux demo path.

**Mechanic for Option B:**
- Edit each phase's VERIFICATION.md frontmatter `status:` line: leave as `human_needed`,
  add a new key `human_acceptance: indefinite` with a `rationale:` block citing the
  evidence (E2E green for the underlying behavior; visual-feel / pwsh-runtime deferred).
- Add a `## 6.6 — Indefinite human_needed acceptance` subsection (or extend §6.1) to
  `MILESTONE_SUMMARY-v1.0.md` listing both phases.

**Mechanic for Option A** (if planner chooses sign-off instead):
- Edit each phase's VERIFICATION.md frontmatter `status: human_needed` → `status: passed`.
- Append an `## Acceptance` section with a 3-5 line note ("Accepted on 2026-04-28 by
  S. Zern. Visual-feel items deferred; the underlying flows are E2E-green ×3 browsers ×2
  runs.").

### Pattern 4: Append §6 entry to MILESTONE_SUMMARY (G5)

**What:** Add a new §6 sub-entry (e.g., §6.6) to `.planning/reports/MILESTONE_SUMMARY-v1.0.md`
documenting commits `73abc58` and `e79ad18` as planning deltas.
**When to use:** Plan 11-04.
**Note:** §6.3 of `MILESTONE_SUMMARY-v1.0.md` (lines 110-118) ALREADY has a table for these
two commits. The G5 closure can be achieved by:
- (lightweight) Promoting that table from "tech debt" framing to a formal "post-milestone
  planning record" framing (rename §6.3 heading, add a "Status: recorded as planning delta"
  line).
- (heavier) Creating a thin `.planning/phases/10-e2e-validation/10-10-SUMMARY.md` (a
  Phase 10.1 retrofit) with the standard SUMMARY frontmatter and `requirements-completed`
  list of `[FE-05, FE-06, APP-02, FE-01]`.

The lightweight approach is simpler and matches the audit's recommended remediation
("note as pre-archive deltas in the milestone summary"). Recommended.

### Anti-Patterns to Avoid

- **Editing `.planning/v1.0-MILESTONE-AUDIT.md`.** It is the audit record and is frozen.
  The Phase 11 SC#5 says "re-running `/gsd-audit-milestone v1.0` returns verdict `passed`"
  — that's a NEW audit pass, not an edit of the existing audit doc.
- **Re-running the canonical harness.** Already green twice; running a third time risks
  introducing flake noise into the milestone close.
- **Touching production source.** No file under `backend/`, `frontend/`, `scripts/`,
  `Dockerfile`, `docker-compose.yml`, or `test/` should be edited.
- **Adding new SCs to phases.** Phase 11 ratifies satisfaction; it does not extend any
  prior phase's scope.
- **Spawning gsd-verifier on Phase 7, 9, or 10.** Phase 7 and 9 are at `human_needed` —
  re-running the verifier will re-emit the same `human_verification` block; the gap is
  the missing acceptance decision, not the verifier output. Phase 10 is `passed`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VERIFICATION.md for Phase 5 | Custom verification template | `gsd-verifier` agent | The agent exists, has a stable output shape (see 04/07/10-VERIFICATION.md), and is the canonical writer for these files. Hand-writing risks shape drift. |
| Audit-style verdict logic | Custom audit rerun | `/gsd-audit-milestone v1.0` (after closure) | SC#5 explicitly delegates the re-audit to the audit command. Phase 11 plans must NOT pre-compute a verdict. |

**Key insight:** All four plans are pure file-edit plans. Resist the urge to "verify by
re-running tests" — the Phase 11 brief is explicit that all evidence already exists on
disk. Plans should cite line numbers and grep results, not run anything.

## Runtime State Inventory

> Phase 11 is a documentation phase. There is no rename, refactor, or migration. This
> section is included for completeness with each category answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the canonical harness uses `tmpfs:/app/db` and starts each run from a clean SQLite. The user's persistent `finally-data` Docker volume is a runtime artifact, not a Phase 11 concern. | None. |
| Live service config | None — no n8n, Datadog, Tailscale, or external service is in scope. | None. |
| OS-registered state | None — no Task Scheduler, launchd, systemd, or pm2 entries are touched by Phase 11. | None. |
| Secrets / env vars | None — `.env` and `.env.example` are unchanged by this phase. `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` env-var names persist as-is. | None. |
| Build artifacts / installed packages | None — no `pip install`, `uv add`, or `npm install` runs. No build artifacts re-emit. | None. |

**Verified by:** Phase brief explicitly forbids production source changes; all four plan
acceptance criteria reduce to file-edit + grep.

## Common Pitfalls

### Pitfall 1: gsd-verifier "discovers" gaps in Phase 5

**What goes wrong:** gsd-verifier runs against Phase 5, finds something the audit didn't
flag, and tries to escalate (e.g., a missing test for an edge case, a coverage shortfall
in a sub-module).
**Why it happens:** gsd-verifier is gap-detection-oriented; it doesn't know the milestone
audit already certified Phase 5 functional.
**How to avoid:** Plan 11-01 must instruct gsd-verifier that (a) the audit's verdict is
authoritative, (b) the goal is audit-trail backfill not gap-discovery, and (c) any
"would-be gap" should be tagged as `audit_observation: deferred` rather than blocking
the VERIFICATION.md write.
**Warning signs:** gsd-verifier returns `## RESEARCH BLOCKED`-style output or sets
`status: gaps_found` in the frontmatter. If that happens, the planner's options are
to (i) fold the observation into a thin Phase 11.1 follow-up, or (ii) document it as
accepted policy debt in `MILESTONE_SUMMARY-v1.0.md`.

### Pitfall 2: REQUIREMENTS.md plan-ID evidence is wrong

**What goes wrong:** Plan 11-02 flips a row from `Pending` to `Complete (Plan 04-01)`
when the actual landing plan was `04-02`.
**Why it happens:** Some REQ-IDs landed across multiple plans (service layer in plan N-01,
HTTP route in plan N-02). The "Phase" column is right; the plan-ID list inside
`Complete (...)` must be precise.
**How to avoid:** Use the precomputed Evidence Map below. Each row cites the SUMMARY
file's `requirements-completed` frontmatter (where present) or the SUMMARY's
"Accomplishments" / "Files Created" section.
**Warning signs:** Plan-ID in the new status string doesn't appear in the cited SUMMARY's
metadata.

### Pitfall 3: G3 + G4 frontmatter mutated incorrectly

**What goes wrong:** Plan 11-03 changes `status: human_needed` to a free-form string
that breaks the audit's frontmatter schema.
**Why it happens:** YAML frontmatter is sensitive to key naming and value enums.
**How to avoid:** Either keep `status: human_needed` (Option B) and add a sibling
`human_acceptance: indefinite` key, or change `status:` to one of the known enum values
(`passed`, `gaps_found`, `human_needed`). Don't invent new enum values like
`status: accepted_with_debt`.
**Warning signs:** `/gsd-audit-milestone` rerun fails to parse the frontmatter or reports
the phase as `unverified`.

### Pitfall 4: G5 record creates phantom plan that breaks plan counts

**What goes wrong:** Creating a `10-10-SUMMARY.md` (Phase 10.1 retrofit) for the lightweight
G5 closure inflates Phase 10 plan count from 10 to 11, breaking the ROADMAP plan-count
invariants and STATE.md `completed_plans: 47`.
**Why it happens:** Adding a SUMMARY without a matching PLAN.md and ROADMAP entry creates
a counting mismatch.
**How to avoid:** Use the lightweight approach (extend §6 of `MILESTONE_SUMMARY-v1.0.md`).
If the planner DOES choose to add a Phase 10.1 SUMMARY, also update ROADMAP Phase 10 plan
list to `11/11` and STATE.md `completed_plans: 48` and `total_plans: 48`.
**Warning signs:** ROADMAP and STATE.md disagree on plan counts after Phase 11 executes.

### Pitfall 5: Coverage count math at top of REQUIREMENTS.md gets re-incremented

**What goes wrong:** Plan 11-02 sweeps 15 rows AND re-increments the coverage count at
the top from "40 (100%)" to "55 (137%)" because the planner thought "Complete" rows are
new entries.
**Why it happens:** The 40 IDs were always counted; only their status string was wrong.
**How to avoid:** Verify lines 171-174 of REQUIREMENTS.md still read `40 total / 40 mapped /
0 unmapped` after the sweep. The audit (line 9) confirms `40/40 functionally satisfied`.
**Warning signs:** Coverage count line changes from 40.

## Code Examples

This is a documentation phase. No code examples.

The closest analog to "code" is the gsd-verifier output shape, anchored by these existing
files (planner should reference for 05-VERIFICATION.md):
- `.planning/phases/04-watchlist-api/04-VERIFICATION.md` (small phase, similar SC count)
- `.planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` (similar size)
- `.planning/phases/10-e2e-validation/10-VERIFICATION.md` (most recent verifier output)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual VERIFICATION.md authoring | `gsd-verifier` agent | introduced in GSD framework | Removes shape drift; required for G1 closure. |
| Mixed `Pending` / `In progress` / `Complete` strings in REQUIREMENTS.md | Uniform `Complete (Plan N-NN, ...)` for satisfied items | this phase | Audit reads the table mechanically; uniform strings make `/gsd-audit-milestone` reproducible. |

**Deprecated/outdated:** None applicable to this phase.

## Evidence Map (G2 — REQUIREMENTS.md sweep)

Each row below maps a stale `Pending` / `In progress` REQUIREMENTS.md line to the concrete
plan-IDs that landed it. Sources are SUMMARY.md `requirements-completed` frontmatter
(when present) and SUMMARY "Accomplishments" sections (when frontmatter is absent).

| REQ-ID | Phase | Stale text (current) | Replacement text | Evidence path |
|--------|-------|----------------------|------------------|---------------|
| DB-01 | Phase 2 | `Pending` | `Complete (Plan 02-01, 02-02)` | `02-01-SUMMARY.md` (schema landed), `02-02-SUMMARY.md` (lifespan wiring) — verified by 02-VERIFICATION.md `passed` |
| DB-02 | Phase 2 | `Pending` | `Complete (Plan 02-01, 02-02)` | same as DB-01 — `seed_defaults` landed in 02-01, called from lifespan in 02-02 |
| DB-03 | Phase 2 | `Pending` | `Complete (Plan 02-02)` + Phase 9 volume mount | 02-02 wires DB to `db/finally.db`; 09-VERIFICATION.md SC#6 proves volume persistence (`cash 10000 → 9809.98 → 9809.98 across stop+restart`) |
| PORT-05 | Phase 3 | `Pending (03-03 — observer wiring)` | `Complete (Plan 03-02, 03-03)` | 03-02-SUMMARY (inline post-trade snapshot); 03-03-SUMMARY (60s observer registered in lifespan) — confirmed in STATE.md decision log line 100 |
| WATCH-01 | Phase 4 | `In progress (04-01 service layer; 04-02 adds HTTP route)` | `Complete (Plan 04-01, 04-02)` | 04-01-SUMMARY (`get_watchlist`); 04-02-SUMMARY (`GET /api/watchlist`) — 04-VERIFICATION.md SC#1 PASS |
| WATCH-02 | Phase 4 | `In progress (04-01 service layer; 04-02 adds HTTP route)` | `Complete (Plan 04-01, 04-02)` | same source files; 04-VERIFICATION.md SC#2 PASS |
| WATCH-03 | Phase 4 | `In progress (04-01 service layer; 04-02 adds HTTP route)` | `Complete (Plan 04-01, 04-02)` | same source files; 04-VERIFICATION.md SC#3 PASS |
| CHAT-01 | Phase 5 | `Pending` | `Complete (Plan 05-03)` | 05-03-SUMMARY frontmatter `requirements-completed: [CHAT-01, CHAT-05, TEST-01]` |
| CHAT-02 | Phase 5 | `Pending` | `Complete (Plan 05-01)` | 05-01-SUMMARY: LiveChatClient, MockChatClient, models, prompts |
| CHAT-03 | Phase 5 | `Pending` | `Complete (Plan 05-01)` | 05-01-SUMMARY: `build_messages` + `build_portfolio_context` |
| CHAT-04 | Phase 5 | `Pending` | `Complete (Plan 05-02)` | 05-02-SUMMARY: `run_turn` auto-exec orchestration |
| CHAT-05 | Phase 5 | `Pending` | `Complete (Plan 05-02, 05-03)` | 05-02 (persistence ordering D-18); 05-03 (`GET /api/chat/history`) |
| CHAT-06 | Phase 5 | `Pending` | `Complete (Plan 05-01)` | 05-01-SUMMARY: MockChatClient + `LLM_MOCK=true` factory branch |
| FE-03 | Phase 7 | `Pending` | `Complete (Plan 07-01, 07-03)` | 07-VERIFICATION.md SC#1 PASS — Watchlist + WatchlistRow + Sparkline |
| FE-04 | Phase 7 | `Pending` | `Complete (Plan 07-04)` | 07-VERIFICATION.md SC#2 PASS — MainChart |
| FE-07 | Phase 7 | `Pending` | `Complete (Plan 07-05)` | 07-VERIFICATION.md SC#3 PASS — PositionsTable + PositionRow |
| FE-08 | Phase 7 | `Pending` | `Complete (Plan 07-06)` | 07-VERIFICATION.md SC#4 PASS — TradeBar + portfolio.ts |
| FE-10 | Phase 7 | `Pending` | `Complete (Plan 07-07)` | 07-VERIFICATION.md SC#5 PASS — Header + ConnectionDot |
| TEST-01 | Phase 5 (primary) | `Pending` | `Complete (Plan 05-03)` | 05-03-SUMMARY frontmatter `requirements-completed: [..., TEST-01]`; 05-VALIDATION.md line 65 + 155 confirm `295 passed` and 99.17% coverage |

**15 rows to flip** (count matches audit G2 affected_reqs list).

The audit's `affected_reqs` list contains 19 IDs (lines 27-28), but 4 of those are
actually already partially right (`In progress (...)` strings on WATCH-01..03 and the
`Pending (03-03 — observer wiring)` on PORT-05 are not bare `Pending` but still need
the `Complete` flip). The plan should treat all 19 as eligible for sweep and the
acceptance grep should be:

```bash
# After sweep, no row in the table reads "Pending" or "In progress":
grep -E "^\| (DB-0[123]|PORT-05|WATCH-0[123]|CHAT-0[1-6]|FE-0[34]|FE-0[78]|FE-10|TEST-01) " .planning/REQUIREMENTS.md | grep -E "Pending|In progress"
# Expected exit code: 1 (no matches)
```

## Validation Architecture

> Documentation-only phase. Test framework is N/A. Validation is file-presence and
> canonical-string grep. Per `.planning/config.json` `workflow.nyquist_validation: true`,
> a 11-VALIDATION.md file should exist with the contract below.

### "Test" Framework

| Property | Value |
|----------|-------|
| Framework | bash + grep + test (no test runner) |
| Config file | none — Phase 11 has no test infrastructure |
| Quick run command | `bash -c 'cd .planning/phases/11-milestone-v1.0-closure && for f in 11-RESEARCH.md 11-CONTEXT.md 11-01-PLAN.md 11-02-PLAN.md 11-03-PLAN.md 11-04-PLAN.md; do test -f "$f" && echo "OK $f" \|\| echo "MISSING $f"; done'` |
| Full suite command | (per-plan greps, see "Phase Requirements → Test Map" below) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| Phase 11 SC#1 (G1) | `05-VERIFICATION.md` exists with frontmatter `phase: 05-ai-chat-integration` | file-presence + grep | `test -f .planning/phases/05-ai-chat-integration/05-VERIFICATION.md && grep -q "phase: 05-ai-chat-integration" .planning/phases/05-ai-chat-integration/05-VERIFICATION.md` | ❌ — Wave 0 (gsd-verifier produces) |
| Phase 11 SC#1 (G1) | VERIFICATION.md cites all 7 SCs (CHAT-01..06, TEST-01) | grep | `for r in CHAT-01 CHAT-02 CHAT-03 CHAT-04 CHAT-05 CHAT-06 TEST-01; do grep -q "$r" .planning/phases/05-ai-chat-integration/05-VERIFICATION.md \|\| echo "MISSING $r"; done` | ❌ — produced by 11-01 |
| Phase 11 SC#2 (G2) | All 15 drift rows now read `Complete (Plan ...)` | grep | `grep -E "^\\| (DB-0[123]\|PORT-05\|WATCH-0[123]\|CHAT-0[1-6]\|FE-0[34]\|FE-0[78]\|FE-10\|TEST-01) " .planning/REQUIREMENTS.md \| grep -cE "Pending\|In progress"` (expect 0) | ✓ — REQUIREMENTS.md exists |
| Phase 11 SC#2 (G2) | Coverage count line still reads 40/40 | grep | `grep -q "v1 requirements: 40 total" .planning/REQUIREMENTS.md && grep -q "Mapped to phases: 40 (100%)" .planning/REQUIREMENTS.md` | ✓ |
| Phase 11 SC#3 (G3) | Phase 7 VERIFICATION.md has explicit acceptance decision | grep | (Option A) `grep -q "^status: passed" .planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` OR (Option B) `grep -q "human_acceptance: indefinite" .planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` | ✓ — file exists |
| Phase 11 SC#3 (G4) | Phase 9 VERIFICATION.md has explicit acceptance decision | grep | same patterns as G3, against `09-VERIFICATION.md` | ✓ — file exists |
| Phase 11 SC#4 (G5) | `MILESTONE_SUMMARY-v1.0.md` §6 has explicit "post-milestone planning record" entry citing both commit SHAs | grep | `grep -q "73abc58" .planning/reports/MILESTONE_SUMMARY-v1.0.md && grep -q "e79ad18" .planning/reports/MILESTONE_SUMMARY-v1.0.md && grep -qE "(planning record\|planning delta)" .planning/reports/MILESTONE_SUMMARY-v1.0.md` | ✓ — both SHAs already in §6.3, status framing is what 11-04 promotes |
| Phase 11 SC#5 (audit re-run) | Verdict shifts from `tech_debt` to `passed` (or carries only G3/G4 policy debt) | manual run | `/gsd-audit-milestone v1.0` | N/A — orchestrator-level command, not run inside Phase 11 |

### Sampling Rate

- **Per task commit:** Run the relevant plan's grep block.
- **Per plan completion:** Run all greps for that plan's gap.
- **Phase gate:** All grep blocks above exit 0; Phase 11 VERIFICATION.md produced by
  gsd-verifier (Wave-end pass).

### Wave 0 Gaps

- [ ] `.planning/phases/11-milestone-v1.0-closure/11-VALIDATION.md` — produces the
      grep contract above as a structured table for the verifier.
- [ ] `.planning/phases/11-milestone-v1.0-closure/11-CONTEXT.md` — written by
      `/gsd-discuss-phase` (or skipped if proceeding straight to plans; Phase 11 has no
      open decisions other than the G3/G4 acceptance choice).

*(No code-level Wave 0 gaps; framework install is N/A.)*

## Security Domain

> Phase 11 is documentation-only. No new code paths, no new endpoints, no new external
> calls. ASVS and STRIDE are inherited from prior phases unchanged.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 11 introduces no auth surfaces. |
| V3 Session Management | no | No session state. |
| V4 Access Control | no | No new endpoints. |
| V5 Input Validation | no | No new inputs. |
| V6 Cryptography | no | No new crypto. |
| V7 Error Handling | no | No new error paths. |

### Known Threat Patterns for documentation-edit phases

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Accidental commit of `.env` content into a SUMMARY/VERIFICATION file | Information Disclosure | Re-run `grep -E "OPENROUTER_API_KEY=sk-or" .planning/` before final commit; should return 0 matches. The Phase 5 D-05 redaction pattern (no key formatted into log strings) extends to the audit-trail backfill — gsd-verifier should NOT include the key value in the produced 05-VERIFICATION.md. |
| Stale grep evidence (text changes upstream after research, evidence in plan no longer matches) | Repudiation (audit-trail integrity) | Each plan must re-run its citing greps against current HEAD before commit; the plan acceptance criteria should embed the grep + expected line numbers. |

## Sources

### Primary (HIGH confidence)

- `.planning/v1.0-MILESTONE-AUDIT.md` (lines 17-45 — gap definitions G1-G5; lines 84-95 —
  phase verification status table; lines 137-150 — REQ-ID drift list)
- `.planning/STATE.md` (line 6 — milestone status `complete`; line 12 — overall progress
  `100%`; lines 96-157 — Phase 5 / 7 / 9 decision log entries)
- `.planning/ROADMAP.md` (lines 202-218 — Phase 11 goal, requirements, SCs, named plans)
- `.planning/REQUIREMENTS.md` (lines 130-169 — traceability table to be swept; lines 171-174
  — coverage count to verify unchanged)
- `.planning/reports/MILESTONE_SUMMARY-v1.0.md` (lines 47-54 — phase verification table;
  lines 70-77 — drift breakdown table; lines 110-118 — §6.3 already lists G5 commits)
- `.planning/phases/05-ai-chat-integration/05-01-SUMMARY.md`,
  `05-02-SUMMARY.md`, `05-03-SUMMARY.md`, `05-VALIDATION.md`, `05-UAT.md` (gsd-verifier's
  evidence inputs for G1)
- `.planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` (G3 status =
  `human_needed`; frontmatter `human_verification` lines 20-38 = the deferred items)
- `.planning/phases/09-dockerization-packaging/09-VERIFICATION.md` (G4 status =
  `human_needed`; frontmatter `human_verification` lines 7-19 = the deferred items)
- `git log` output (G5 commits `73abc58` and `e79ad18` confirmed present on
  `finally-gsd` branch with the documented messages and file scopes)
- `.planning/phases/04-watchlist-api/04-VERIFICATION.md`,
  `.planning/phases/10-e2e-validation/10-VERIFICATION.md` (gsd-verifier output shape
  reference for 11-01)

### Secondary (MEDIUM confidence)

- (none — all evidence is on disk and verified in this session)

### Tertiary (LOW confidence)

- (none)

## Metadata

**Confidence breakdown:**

- Gap-to-artifact mapping: HIGH — every gap has a named target file already on disk
  (or to be produced by gsd-verifier per its standard contract).
- Evidence-to-claim mapping: HIGH — Evidence Map cites SUMMARY frontmatter
  `requirements-completed` lists or VERIFICATION.md SC numbers verbatim.
- Tooling for G1: HIGH — gsd-verifier is the canonical writer; output shape is stable
  across phases 1, 2, 3, 4, 6, 8, 10.
- G3/G4 acceptance pattern: MEDIUM — two viable options (passed-with-acceptance vs
  indefinite human_needed); planner picks based on user discretion.
- G5 record location: MEDIUM — two viable options (extend §6 of MILESTONE_SUMMARY vs
  create thin Phase 10.1 SUMMARY); lightweight option recommended.

**Order/Dependency hints between gaps:**

- 11-01 (G1), 11-02 (G2), 11-03 (G3+G4), 11-04 (G5) are **mostly independent** and can
  be planned in any order. Recommended execution order: 11-01 → 11-02 → 11-03 → 11-04
  (matches ROADMAP numbering and is the natural dependency: G2 references the Phase 5
  status that G1 produces, since flipping CHAT-01..06 + TEST-01 to `Complete` is more
  defensible once `05-VERIFICATION.md` exists).
- A weaker dependency: 11-04 (G5) extends `MILESTONE_SUMMARY-v1.0.md` §6, which 11-03
  (G3+G4) may also amend if Option B is chosen (extending §6.1 with the indefinite
  `human_needed` rationale). If both plans edit the same file, sequence them
  (11-03 → 11-04) to avoid merge friction within the same wave.

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable — documentation work; no library or framework drift
to track).
