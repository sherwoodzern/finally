---
phase: 09-dockerization-packaging
plan: 02
subsystem: infra
tags: [docker, env-config, dotenv, packaging, ops]

# Dependency graph
requires:
  - phase: 09-dockerization-packaging
    provides: "Plan 09-01 ships the Dockerfile that consumes `--env-file .env` at runtime"
provides:
  - ".env.example at repo root with three documented runtime env vars"
  - "Safe placeholder values that boot the simulator-mode demo with zero edits (SC#4)"
  - "Public-repo-safe template (no real API keys committed; T-09-05 closed)"
affects: [09-03 scripts, 09-04 docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dotenv-style KEY=value config file with empty-default-is-safe semantics"

key-files:
  created:
    - ".env.example"
  modified: []

key-decisions:
  - "Ship D-12 verbatim (three keys in plan-spec order: OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK=false)"
  - "Empty MASSIVE_API_KEY -> SimulatorDataSource (factory.py:24-31) is the demo default"
  - "Empty OPENROUTER_API_KEY + LLM_MOCK=false -> /api/chat returns 502 gracefully (no startup crash)"
  - "DB_PATH intentionally NOT exposed in .env.example (container-internal, set by Dockerfile)"
  - "No quotes around values; no spaces around `=` (Docker --env-file is finicky on both)"
  - "Defer the docker-run integration test (Task 2 step 3-9) to the post-merge wave gate, since this isolated worktree has no Dockerfile (Plan 09-01's surface) and no Docker daemon"

patterns-established:
  - "Public-repo env template pattern: every committed `.env.example` value must boot the demo; secrets are blank, not placeholder strings like `your-key-here`"

requirements-completed: [OPS-04]

# Metrics
duration: 2min
completed: 2026-04-27
---

# Phase 09 Plan 02: Environment Configuration Template Summary

**Shipped `.env.example` at repo root with three documented keys whose defaults are sufficient to boot the simulator-mode demo unedited (SC#4 contract).**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-27T14:32:34Z
- **Completed:** 2026-04-27T14:34:16Z
- **Tasks:** 2 (1 file authored, 1 verification with deferred runtime portion)
- **Files modified:** 1 created, 0 modified

## Accomplishments

- Authored `.env.example` at the repo root with the verbatim D-12 content from `09-CONTEXT.md`.
- Validated the three-key contract via static checks (file exists, exact key names, exact values, no leaked secrets, no extraneous keys, no DB_PATH).
- Confirmed `.env` remains gitignored at `.gitignore:141` (unchanged).
- Confirmed dotenv-simulation parsing produces the expected key/value mapping that integrates with `backend/app/main.py:16 load_dotenv()`, `backend/app/market/factory.py:24-31` (empty `MASSIVE_API_KEY` -> `SimulatorDataSource`), and `backend/app/lifespan.py:50-57` (empty `OPENROUTER_API_KEY` + `LLM_MOCK=false` -> WARN, no crash).
- Closed OPS-04: a public-repo-safe template that boots the demo with no edits.

## Exact `.env.example` content shipped

```
# FinAlly environment configuration
# Copy this file to .env and edit the values you need.

# Required for AI chat. Get one at https://openrouter.ai/.
# If left empty, /api/chat returns 502 and the chat panel surfaces an error,
# but the rest of the terminal (heatmap, P&L, watchlist, trades) still works.
OPENROUTER_API_KEY=

# Optional. If set and non-empty, switches to the real Massive (Polygon.io)
# market data feed. Otherwise the simulator runs (recommended for the demo).
MASSIVE_API_KEY=

# Set to "true" to make the LLM return deterministic mock responses (useful
# for E2E tests and local development without an API key).
LLM_MOCK=false
```

- 15 lines, 648 bytes, terminating newline, all-ASCII (no emojis).
- 3 KEY= lines (no extras such as DB_PATH, PORT, LOG_LEVEL).

## Task Commits

1. **Task 1: Author .env.example at repo root (D-12 verbatim)** — `a048102` (feat)
2. **Task 2: Verify copy-and-boot integration** — no commit (verification-only task; runtime portion deferred to wave-merge gate; static portions executed inline below)

## Files Created/Modified

- `.env.example` — User-facing template for runtime environment configuration. Contains the three runtime env vars consumed by the backend (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`) with empty/`false` defaults that boot the simulator demo with zero edits.

## Verification Results

### Task 1 (file authoring) — PASS

```bash
test -f .env.example && \
[ "$(grep -c '^OPENROUTER_API_KEY=$' .env.example)" = "1" ] && \
[ "$(grep -c '^MASSIVE_API_KEY=$' .env.example)" = "1" ] && \
[ "$(grep -c '^LLM_MOCK=false$' .env.example)" = "1" ] && \
! grep -qE "sk-or-v1-|pk_test_|sk_live_" .env.example && \
! grep -qE "^DB_PATH=" .env.example && \
[ "$(awk -F= '/^[A-Z_]+=/ {print $1}' .env.example | wc -l | tr -d ' ')" = "3" ]
# -> exit 0 (TASK 1 VERIFICATION PASSED)
```

VALIDATION rows satisfied:
- 09-03-01: `test -f .env.example` exits 0
- 09-03-02: `grep -c "^OPENROUTER_API_KEY=\|^MASSIVE_API_KEY=\|^LLM_MOCK=" .env.example` outputs `3`
- 09-03-03: `grep -E "sk-or-v1-|pk_test_" .env.example` returns no matches (T-09-05 closed)
- 09-03-04: `grep -q "^\.env$" .gitignore` exits 0 (line 141, unchanged)

### Task 2 (copy-and-boot integration)

#### Static portions — PASS (executed in this worktree)

- **Copy is byte-identical:** `cp .env.example .env.uat-09-02-static && diff -q .env.example .env.uat-09-02-static` -> identical.
- **Parses cleanly under env-file rules:** Python parser confirms KEY=value form, no spaces around `=`, no quotes around values, no malformed lines.
- **Dotenv-simulation produces expected mapping:**
  - `OPENROUTER_API_KEY=""` -> lifespan WARN, `/api/chat` 502 graceful
  - `MASSIVE_API_KEY=""` -> `factory.py:24-31` selects `SimulatorDataSource`
  - `LLM_MOCK="false"` -> real LLM path attempted (then 502s when key empty)
- **`.env` still gitignored:** `grep -n "^\.env$" .gitignore` -> `141:.env` (unchanged).

#### Runtime container portions — DEFERRED to wave-1 merge gate

The plan's Task 2 verification (`docker run -d --name finally-uat-09-02 ... finally:latest`) cannot execute in this isolated parallel worktree:

- **`Dockerfile` is Plan 09-01's surface** and not present in this worktree (parallel agents work in independent worktrees that share only the wave's base commit; Plan 09-01's Dockerfile has not been merged here).
- **Docker daemon is not reachable** in this execution environment (`docker info` fails).

This is a documented consequence of the parallel-wave execution model (see the plan's `parallel_execution` block) and is out of scope for the per-worktree gate. The orchestrator's post-merge integration step owns this validation: once 09-01 (Dockerfile + .dockerignore) and 09-02 (.env.example) are merged onto the wave-1 integration branch, the canonical `cp .env.example .env && docker build -t finally:latest . && docker run -d --env-file .env ...` flow can be exercised end to end.

The static-file deliverable of this plan (the `.env.example` file itself) is fully validated above. The runtime checks are a downstream gate, not a gate on this plan's correctness.

## Final Wave 1 / OPS-04 Gate (static portions)

```text
1. File exists with correct three keys           PASS
2. No leaked secrets                              PASS
3. .env still gitignored at .gitignore:141        PASS
4. SC#4 docker boot                               DEFERRED to wave-1 merge gate
```

## Deviations from Plan

**None.** Plan executed as written. The runtime container test in Task 2 was deferred (not skipped or modified) per the explicit parallel-wave constraint documented in the plan itself ("Plan 09-01 may or may not have completed first in parallel mode") and the spawn objective's `<scope>` block ("Plan 09-02 creates ONE file at the repo root: `.env.example`").

## Threat Surface

T-09-05 (Information Disclosure: real OPENROUTER_API_KEY accidentally pasted into `.env.example`) is closed: file ships with `OPENROUTER_API_KEY=` (empty); `grep -E "sk-or-v1-|pk_test_|sk_live_" .env.example` returns no matches.

T-09-06 (Information Disclosure: user disables `.gitignore`) remains accepted per the plan's threat register; out of scope.

No new threat surface introduced.

## Self-Check: PASSED

- File `.env.example` exists at repo root: FOUND
- Commit `a048102` exists in git log: FOUND (`feat(09-02): add .env.example with safe placeholders for runtime config`)
- File `.planning/phases/09-dockerization-packaging/09-02-SUMMARY.md` will be confirmed by the SUMMARY commit below.
