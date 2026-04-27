---
phase: 09-dockerization-packaging
plan: 04
subsystem: infra

requires:
  - phase: 09 (Plan 01)
    provides: "Multi-stage Dockerfile + .dockerignore — referenced by Image architecture and Canonical run sections"
  - phase: 09 (Plan 02)
    provides: ".env.example with three documented keys — referenced by .env workflow section"
  - phase: 09 (Plan 03)
    provides: "Four cross-platform scripts — referenced by Quickstart and Windows sections, plus README"
provides:
  - "docs/DOCKER.md long-form reference (7 sections, 221 lines)"
  - "Updated README.md Quick Start citing all four scripts and linking the long-form reference"
affects: [user onboarding, demo runs, future Docker troubleshooting]

tech-stack:
  added: []
  patterns:
    - "README Quick Start ≤ 10 non-blank/non-fence lines + link to long-form reference (D-14)"
    - "docs/DOCKER.md as the canonical Docker reference for the project"

key-files:
  created:
    - "docs/DOCKER.md (NEW, 221 lines)"
  modified:
    - "README.md (Quick Start expanded from 3 to 5 script-citing lines + DOCKER.md link)"

key-decisions:
  - "Each of the four scripts cited on its own line in README so grep -c counts to 4 (the verify check counts matching LINES, not matches)"
  - "Forward-slash script paths used in README and DOCKER.md Quickstart for grep portability; Windows-specific commands keep PowerShell-native syntax in the Windows section table"
  - "No HEALTHCHECK or USER directive documented (matches Dockerfile reality — orchestration platforms own probes; localhost demo runs as root)"

patterns-established:
  - "Phase 9 docs: 7-section structure (Quickstart, Canonical run, Image architecture, Volume, .env workflow, Troubleshooting, Windows) is the template for any future Docker doc work"
  - "README minimal-edit pattern: keep existing structure, add focused links rather than rewriting (matches D-14)"

requirements-completed: [OPS-02, OPS-04]

duration: ~10min
completed: 2026-04-27
---

# Phase 09 Plan 04 Summary

**Long-form Docker reference (docs/DOCKER.md, 7 sections, 221 lines) plus a minimal README Quick Start update that cites all four cross-platform scripts and links the long-form reference.**

## Performance

- **Duration:** ~10 min (orchestrator inline — agent path was abandoned for this wave after the Plan 09-03 sandbox-policy issues)
- **Started:** 2026-04-27 (Wave 3 dispatch)
- **Completed:** 2026-04-27
- **Tasks:** 2
- **Files created:** 1 (docs/DOCKER.md)
- **Files modified:** 1 (README.md)

## Accomplishments

- 7-section docs/DOCKER.md covering Quickstart, Canonical run, Image architecture, Volume, .env workflow, Troubleshooting, and Windows
- README Quick Start now cites scripts/start_mac.sh, scripts/stop_mac.sh, scripts/start_windows.ps1, and scripts/stop_windows.ps1 (one per line)
- Markdown link from README to docs/DOCKER.md for the long-form reference
- All 4 Wave 3 verification blocks pass (7 sections; scripts + canonical docker run cited; no leaked secrets; README Quick Start ≤ 10 lines and ≥ 4 script-citing lines)

## Task Commits

1. **Task 1: docs/DOCKER.md** — `2057eb3` (feat)
2. **Task 2: README.md Quick Start** — `88038c6` (docs)

## Files Created/Modified

- `docs/DOCKER.md` (NEW, 221 lines) — long-form Docker reference
- `README.md` — Quick Start: 3 script-citing lines -> 4 script-citing lines (one per script, all four scripts cited); +1 link to docs/DOCKER.md

## Decisions Made

- **Each script on its own line in the README Quick Start.** The plan's verify-block uses `grep -c` (counts matching LINES, not matches). The original prescribed content packed two scripts per line, which would only register 2 lines. Restructured to four lines so the verify check counts to 4. Quick Start total stays at 7 non-blank, non-fence lines (within the ≤ 10 budget).
- **Forward-slash paths in DOCKER.md Quickstart and README.** PowerShell on Windows accepts forward slashes for relative paths, and forward slashes are what `grep "scripts/start_windows.ps1"` matches. Windows-specific section in DOCKER.md keeps native backslash syntax in the command-mapping table for clarity.
- **No `STOPSIGNAL` / `HEALTHCHECK` / `USER` doc tweaks.** Documented exactly what the Dockerfile actually contains (matches Plan 09-01's shipped image).

## Deviations from Plan

### 1. Plan-prescribed Quick Start content vs. plan-prescribed verify check were inconsistent

The plan's prescribed README block packs two scripts per line (`./scripts/start_mac.sh # or .\scripts\start_windows.ps1`). The plan's verify block requires `grep -c "scripts/..." >= 4`. Two lines × two scripts = 2, not 4. Resolved by expanding to four lines (one per script) — total Quick Start lines stay within the ≤ 10 budget. Functionally identical; copy-paste UX actually improves (no need to mentally split the comment).

### 2. Plan-prescribed DOCKER.md Quickstart used backslash Windows paths in the same line as forward-slash bash paths

`./scripts/stop_mac.sh # or .\scripts\stop_windows.ps1` — the verify check `grep -q "scripts/stop_windows.ps1"` (forward slash) failed against the backslash form. Resolved by giving each platform its own line in the Quickstart bash block; the Windows section table still shows native backslash syntax for the Windows audience.

---

**Total deviations:** 2 plan-defect resolutions; no functional content deviations.
**Impact on plan:** None. All plan must_haves and success criteria satisfied; verify blocks all pass.

## Issues Encountered

None — both tasks executed inline by the orchestrator using the dedicated `Write` and `Edit` tools (no sandbox blocker since `git commit` from the orchestrator works normally).

## Next Phase Readiness

Phase 9 work is complete. The next gates are: code review, regression tests, and phase-level verifier.

## Phase-level VALIDATION coverage map

All 26 rows from `09-VALIDATION.md` per-task verification map are addressed by the four plans in this phase:

### Plan 09-01 (Dockerfile + .dockerignore) — rows 09-01-01 through 09-02-02 (7 rows)

| Row | Coverage |
|-----|----------|
| 09-01-01 | `docker build -t finally:latest .` exited 0 in Plan 09-01 Task 3 cold-build smoke (162s, 564 MB image disk / 124 MB content). |
| 09-01-02 | Stage 1 produced `frontend/out/index.html` (build log: "Generating static pages using 6 workers (5/5)" + Stage 2's "COPY --from=frontend-builder /app/frontend/out /app/frontend/out" succeeded). |
| 09-01-03 | Plan 09-01 verify grep + Dockerfile inspection: only `[project]` deps installed via `uv sync --frozen`, not the `[project.optional-dependencies].dev` extras. |
| 09-01-04 | `.dockerignore` excludes `.env`; verified by structural grep in Plan 09-01 verify block. |
| 09-01-05 | `lifespan.py:86 static_dir = Path(__file__).resolve().parents[2] / 'frontend' / 'out'` — verified during Plan 08-08 ("Phase 8 build gate closed — `frontend/out/index.html` (12,458 bytes)"). Confirmed in Plan 09-03 Task 3 step 3 (GET / returned 12,830 bytes of HTML through the running container). |
| 09-02-01 | `.dockerignore` includes `node_modules/`, `.next/`, `frontend/out/`, `.venv/`, `__pycache__/`, `db/`, `.planning/`, `.claude/`, `.git/`, `.idea/` (≥10 matches; verified). |
| 09-02-02 | Final image content size = 124 MB (well under 500 MB ceiling); verified in Plan 09-01 Task 3 build smoke. |

### Plan 09-02 (.env.example) — rows 09-03-01 through 09-03-05 (5 rows)

| Row | Coverage |
|-----|----------|
| 09-03-01 | `.env.example` exists at repo root (committed in Plan 09-02). |
| 09-03-02 | Three keys (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`) verified in Plan 09-02 verify block. |
| 09-03-03 | No `sk-or-v1-` or `pk_test_` matches; verified in Plan 09-02 verify and re-verified in Plan 09-04 Block 3 across both docs. |
| 09-03-04 | `.env` line at `.gitignore:141` (existing); confirmed by Plan 09-02 agent. |
| 09-03-05 | Plan 09-03 Task 3 step 1: `cp .env.example .env` -> `bash scripts/start_mac.sh --no-open` -> `/api/health` returned `{"status":"ok"}` within 1s. |

### Plan 09-03 (run + volume + scripts) — rows 09-04-01 through 09-05-06 (10 rows)

| Row | Coverage |
|-----|----------|
| 09-04-01 | Plan 09-03 Task 3 step 1: container running, `docker inspect -f '{{.State.Running}}'` -> `true`. |
| 09-04-02 | Plan 09-03 Task 3 step 2: `/api/health` returned `{"status":"ok"}` within 1s (well under 5s budget). |
| 09-04-03 | Plan 09-03 Task 3 step 3: `GET /` returned 12,830 bytes of HTML containing `<html lang="en" class="dark">`. |
| 09-04-04 | Plan 09-03 Task 3 step 4: `/api/stream/prices` emitted `data:` SSE frames (AAPL/AMZN/GOOGL prices). |
| 09-04-05 | Plan 09-03 Task 3 step 7: BUY 1 AAPL @ 190.02 -> cash 10000 -> 9809.98; stop+restart -> cash_after = 9809.98 (volume preserved). |
| 09-05-01 | Plan 09-03 Task 1 verify: `test -x scripts/start_mac.sh && bash -n scripts/start_mac.sh` exit 0; orchestrator-confirmed `chmod +x` on disk + mode 100755 in index. |
| 09-05-02 | Plan 09-03 Task 3 step 5: second consecutive `bash scripts/start_mac.sh --no-open` exit 0; container still running. |
| 09-05-03 | Plan 09-03 Task 3 step 6: `bash scripts/start_mac.sh --build --no-open` output contained "Building finally:latest ..."; container running. |
| 09-05-04 | Plan 09-03 Task 3 step 8: two consecutive `bash scripts/stop_mac.sh` exit 0; `docker volume inspect finally-data` exit 0 (preserved). |
| 09-05-05 | Plan 09-03 Task 2 verify (structural grep on PowerShell content; pwsh not installed on host — Windows-host UAT deferred to manual verification). |
| 09-05-06 | Same — structural grep coverage; Windows-host UAT deferred. |

### Plan 09-04 (docs) — rows 09-06-01 through 09-06-03 (3 rows)

| Row | Coverage |
|-----|----------|
| 09-06-01 | Block 1: `grep -cE '^## (Quickstart|Canonical run|Image architecture|Volume|.env workflow|Troubleshooting|Windows)$' docs/DOCKER.md` outputs 7. |
| 09-06-02 | Block 4: README Quick Start non-blank/non-fence lines = 7 (≤ 10). |
| 09-06-03 | Block 4: `grep -c "scripts/start_mac.sh|scripts/stop_mac.sh|scripts/start_windows.ps1|scripts/stop_windows.ps1" README.md` outputs 4 (≥ 4). |

**Coverage:** 25 of 26 rows fully verified inline; 1 row (09-05-05/06 — pwsh syntax check) defers Windows-host validation to manual UAT (`pwsh` not installed on the host where the integration test ran). All other rows are GREEN.

---
*Phase: 09-dockerization-packaging*
*Completed: 2026-04-27*
