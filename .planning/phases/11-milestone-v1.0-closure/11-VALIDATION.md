---
phase: 11
slug: milestone-v1-0-closure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for the milestone v1.0 closure & doc sweep.
> This phase touches `.planning/` only — no production source. Validation is
> file-presence and grep-against-canonical-strings, not test runs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none — doc-only phase, no executable tests |
| **Config file** | none |
| **Quick run command** | `bash -c 'set -e; for f in .planning/phases/11-milestone-v1.0-closure/11-*-PLAN.md; do echo "$f exists"; done'` |
| **Full suite command** | `bash -c 'set -e; ls .planning/phases/11-milestone-v1.0-closure/11-*-PLAN.md && ls .planning/phases/05-ai-chat-integration/05-VERIFICATION.md'` |
| **Estimated runtime** | <2 seconds (file-system checks only) |

---

## Sampling Rate

- **After every task commit:** Confirm the artifact targeted by the task now exists at the canonical path and contains the canonical anchor string from the task's `<acceptance_criteria>`.
- **After every plan wave:** Re-grep all canonical anchor strings produced so far in the phase.
- **Before `/gsd-verify-work`:** All four target artifacts (05-VERIFICATION.md, REQUIREMENTS.md updated rows, 07/09-VERIFICATION.md decisions, MILESTONE_SUMMARY-v1.0.md §6) exist with their anchor strings.
- **Max feedback latency:** <5 seconds (file system + grep).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | CHAT-01..06, TEST-01 (ratify) | — | N/A (doc) | doc | `test -f .planning/phases/05-ai-chat-integration/05-VERIFICATION.md && grep -q "CHAT-01" .planning/phases/05-ai-chat-integration/05-VERIFICATION.md` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | DB-01..03, PORT-05, WATCH-01..03, CHAT-01..06, FE-03/04/07/08/10, TEST-01 (ratify) | — | N/A (doc) | doc | `bash -c 'for id in DB-01 DB-02 DB-03 PORT-05 WATCH-01 WATCH-02 WATCH-03 CHAT-01 CHAT-02 CHAT-03 CHAT-04 CHAT-05 CHAT-06 FE-03 FE-04 FE-07 FE-08 FE-10 TEST-01; do grep -q "\| ${id} \|.*Complete (Phase" .planning/REQUIREMENTS.md \|\| { echo "MISS: $id"; exit 1; }; done'` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 1 | FE-03/04/07/08/10, OPS-02, OPS-03 (ratify) | — | N/A (doc) | doc | `bash -c 'grep -qE "(passed\|human_acceptance: accepted)" .planning/phases/07-market-data-trading-ui/07-VERIFICATION.md && grep -qE "(passed\|human_acceptance: accepted)" .planning/phases/09-dockerization-packaging/09-VERIFICATION.md'` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 1 | FE-05, FE-06, APP-02, FE-01 (ratify) | — | N/A (doc) | doc | `bash -c 'grep -q "73abc58" .planning/reports/MILESTONE_SUMMARY-v1.0.md && grep -q "e79ad18" .planning/reports/MILESTONE_SUMMARY-v1.0.md'` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — no test framework changes needed. This is a doc-only phase. Wave 0 is "verify the source-of-truth files exist and are readable":*

- [ ] `.planning/v1.0-MILESTONE-AUDIT.md` exists (frozen — read-only input)
- [ ] `.planning/REQUIREMENTS.md` exists (G2 sweep target)
- [ ] `.planning/reports/MILESTONE_SUMMARY-v1.0.md` exists (G5 record target)
- [ ] `.planning/phases/05-ai-chat-integration/` artifacts exist (G1 evidence inputs for gsd-verifier)
- [ ] `.planning/phases/07-market-data-trading-ui/07-VERIFICATION.md` exists (G3 target)
- [ ] `.planning/phases/09-dockerization-packaging/09-VERIFICATION.md` exists (G4 target)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Re-running `/gsd-audit-milestone v1.0` returns verdict `passed` (or only carries forward consciously accepted policy debt with explicit acceptance) | Phase 11 SC #5 | Audit verdict is produced by the audit skill which reads documentation, not by a test runner | After all 4 plans land: run `/gsd-audit-milestone v1.0` and confirm verdict moves off `tech_debt` |

---

## Validation Sign-Off

- [ ] All tasks have grep-verifiable `<acceptance_criteria>` (no test runs needed)
- [ ] Sampling continuity: every task produces a checkable file artifact at a known path
- [ ] Wave 0 source-of-truth files all exist before planning starts
- [ ] No watch-mode flags (no test runner involved)
- [ ] Feedback latency <5s (file system + grep)
- [ ] `nyquist_compliant: true` set in frontmatter once tasks are accepted

**Approval:** pending
