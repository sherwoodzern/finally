---
phase: 10-e2e-validation
plan: 01
subsystem: testing
tags: [playwright, docker-compose, e2e, harness, ci]

requires:
  - phase: 09-dockerization-packaging
    provides: production multi-stage Dockerfile (frontend+backend), /api/health endpoint, .env.example with safe placeholders
  - phase: 02-database-foundation
    provides: lazy SQLite seed (10 default tickers + $10k cash) per fresh anonymous volume
  - phase: 05-llm-chat (planned)
    provides: LLM_MOCK=true env switch consumed by mocked chat path

provides:
  - "test/ npm project with @playwright/test pinned exact 1.59.1 + committed package-lock.json"
  - "test/playwright.config.ts: three browser projects (chromium/firefox/webkit), workers=3 + fullyParallel=false, baseURL http://app:8000, list+html reporters, 30s test timeout"
  - "test/docker-compose.test.yml: app (build from repo-root Dockerfile, LLM_MOCK=true, compose-side python3+urllib HEALTHCHECK) + playwright (mcr.microsoft.com/playwright:v1.59.1-jammy, depends_on service_healthy, ../test mounted at /work)"
  - "test/README.md: two-paragraph harness doc with the canonical one-command invocation and single-spec debug recipe"
  - ".gitignore: three appended Phase 10 artefact entries (test/playwright-report/, test/test-results/, test/node_modules/)"
  - "Auto-discovery: testMatch /\\d{2}-.+\\.spec\\.ts$/ picks up Wave 2 spec files automatically (no further config edits required)"

affects:
  - 10-02-fresh-start+watchlist-crud
  - 10-03-buy+sell
  - 10-04-portfolio-viz+chat
  - 10-05-sse-reconnect+full-suite

tech-stack:
  added:
    - "@playwright/test@1.59.1 (npm, exact pin)"
    - "mcr.microsoft.com/playwright:v1.59.1-jammy (Docker image)"
  patterns:
    - "Self-contained E2E harness under test/ (no root package.json, no frontend/ pollution)"
    - "Compose-side HEALTHCHECK (python3+urllib) keeps test affordances out of the production image"
    - "Anonymous SQLite volume per `up` - fresh seed every test run"
    - "Empty OPENROUTER_API_KEY/MASSIVE_API_KEY env literals (no --env-file, no ${VAR} interpolation) keeps developer secrets isolated from test runs"
    - "workers=3 + fullyParallel=false realises CONTEXT D-07 intent (one worker per spec file, up to 3 spec files concurrent across browser projects)"

key-files:
  created:
    - test/package.json
    - test/package-lock.json
    - test/playwright.config.ts
    - test/docker-compose.test.yml
    - test/README.md
  modified:
    - .gitignore

key-decisions:
  - "Pinned @playwright/test exact 1.59.1 (no caret) - reproducibility wins per RESEARCH.md"
  - "Selected -jammy over -noble Docker tag - matches CONTEXT.md D-01 example shape, slightly smaller and longer-tested base; mcr.microsoft.com/playwright:v1.59.1-jammy verified-pulls 2026-04-27"
  - "Added --pass-with-no-tests flag to npx playwright test invocation in compose (Rule 3 fix) - Playwright 1.59.1 exits 1 on zero specs as a no-silent-pass safety default; flag is harmless once Wave 2 ships specs"
  - "Single H1 + two paragraphs README (no extra headings, no emojis) per planner final wording"

patterns-established:
  - "test/ harness layout: package.json + package-lock.json + playwright.config.ts + docker-compose.test.yml + README.md + 0X-*.spec.ts (Wave 2)"
  - "Compose contract: app service builds from ../Dockerfile, playwright service waits on service_healthy, both share compose default network so playwright reaches app via service-name DNS at http://app:8000"
  - "testMatch /\\d{2}-.+\\.spec\\.ts$/ - Wave 2 plans drop spec files matching this pattern and they are picked up automatically with zero config edits"

requirements-completed: [TEST-03]

duration: 6m 39s
completed: 2026-04-27
---

# Phase 10 Plan 01: E2E Harness Foundation Summary

**Playwright 1.59.1 + docker-compose harness scaffolded under test/ - canonical one-command invocation `docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright` runs end-to-end and exits 0 with zero specs, ready for Wave 2 to drop the seven §12 spec files.**

## Performance

- **Duration:** 6m 39s (399 seconds)
- **Started:** 2026-04-27T17:32:41Z
- **Completed:** 2026-04-27T17:39:20Z
- **Tasks:** 4
- **Files modified:** 6 (5 new + .gitignore)

## Accomplishments

- Self-contained `test/` npm project with `@playwright/test` pinned exact `1.59.1` and a committed `package-lock.json` consumed by `npm ci` inside the Playwright container.
- Playwright config with three browser projects (chromium/firefox/webkit), `testMatch` regex auto-discovering Wave 2 spec files, baseURL fallback to `http://app:8000`, 30s test timeout, and list+html reporters.
- Two-service docker-compose harness: `app` builds from repo-root `Dockerfile` with `LLM_MOCK=true` plus compose-side `python3`+`urllib` healthcheck against `/api/health`; `playwright` runs `mcr.microsoft.com/playwright:v1.59.1-jammy`, gated by `service_healthy`, mounts `../test:/work`, runs `npm ci && npx playwright test --pass-with-no-tests`.
- `.gitignore` appended with three Phase 10 artefact entries (`test/playwright-report/`, `test/test-results/`, `test/node_modules/`) under a labelled section comment.
- `test/README.md` (two paragraphs, single H1, no emojis) documenting the canonical invocation, HTML report path, and the single-spec/single-browser debugging recipe.
- Smoke gate green: full canonical command exits 0 in ~10s (with cached image) and ~3-4 minutes from a cold build.

## Task Commits

Each task was committed atomically (`--no-verify`, parallel-executor in worktree):

1. **Task 1: scaffold `test/` npm project + Playwright dep pin** - `528e44b` (chore)
2. **Task 2: add Playwright config (3 browsers, baseURL http://app:8000)** - `836c9ea` (chore)
3. **Task 3: add docker-compose.test.yml E2E harness** - `e9535d2` (chore)
4. **Task 4: close harness foundation - .gitignore + README + smoke fix** - `cd038f2` (chore)

## Files Created/Modified

**Created:**

- `test/package.json` - Self-contained Node project for the E2E harness; pins `@playwright/test` to exact `1.59.1`.
- `test/package-lock.json` - Deterministic lockfile (generated by `npm install` once, committed); consumed by `npm ci` inside the Playwright container.
- `test/playwright.config.ts` - Three browser projects, workers=3, fullyParallel=false, retries=0/1, baseURL `http://app:8000`, list+html reporters, outputDir `test-results`, no `setupFiles`.
- `test/docker-compose.test.yml` - Two-service compose: `app` (build context ..; LLM_MOCK=true; empty OPENROUTER/MASSIVE keys; DB_PATH=/app/db/finally.db; compose-side healthcheck) + `playwright` (mcr.microsoft.com/playwright:v1.59.1-jammy; depends_on app:service_healthy; mounts ../test at /work; runs `npm ci && npx playwright test --pass-with-no-tests`).
- `test/README.md` - Two-paragraph harness doc.

**Modified:**

- `.gitignore` - Three new lines under `# Phase 10 E2E artefacts (Playwright)` section (untouched the previous 211 lines).

**Source files tracked (NOT gitignored):** `test/package.json`, `test/package-lock.json`, `test/playwright.config.ts`, `test/docker-compose.test.yml`, `test/README.md`. Verified via `git check-ignore` returning empty.

**Generated/run artefacts gitignored:** `test/playwright-report/`, `test/test-results/`, `test/node_modules/`.

## Decisions Made

- **Pinned `@playwright/test` to exact `1.59.1`** (no caret prefix) per RESEARCH.md "reproducibility wins". `package-lock.json` references the same exact version.
- **Selected `-jammy` over `-noble` Playwright Docker tag**, matching CONTEXT.md D-01's example shape. The `-jammy` tag pull was verified live during Task 3 (`docker pull mcr.microsoft.com/playwright:v1.59.1-jammy` exited 0, digest `sha256:8a0360...c8ff`). No `-noble` substitution was required.
- **No top-level `volumes:` block, no `services.app.volumes:`** - per CONTEXT D-06 the SQLite database lives in a fresh anonymous volume each `docker compose up` so every test run starts from the lazy-init Phase 2 seed (10 default tickers + $10k cash).
- **No `version:` key in compose** - modern Compose v2 ignores it and the RESEARCH-provided YAML omits it.
- **Empty OPENROUTER_API_KEY and MASSIVE_API_KEY env literals; no `--env-file` directive** - keeps developer secrets isolated from test runs (mitigates threat T-10-01-02). The empty `MASSIVE_API_KEY` selects `SimulatorDataSource` automatically.
- **Compose-side HEALTHCHECK only**, in `test/docker-compose.test.yml` rather than the production `Dockerfile`, preserving Phase 9 D-08's "no test affordances in the production image" boundary.
- **`--pass-with-no-tests` flag added to `npx playwright test`** in the playwright service command. See "Deviations" below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `--pass-with-no-tests` to the Playwright invocation**

- **Found during:** Task 4 (canonical compose smoke run)
- **Issue:** The unmodified RESEARCH-verbatim command `sh -c "npm ci && npx playwright test"` exits with code 1 (and message "Error: No tests found") when `testMatch` produces zero matches. This is Playwright 1.59.1's no-silent-pass safety default. With `--abort-on-container-exit --exit-code-from playwright`, compose propagates that 1, which fails the plan's Task 4 smoke gate that explicitly requires "exits 0 with Playwright reporting `0 tests`" while Wave 2 has not yet shipped specs.
- **Root-cause evidence:** `npx playwright test --help` shows `--pass-with-no-tests   Makes test run succeed even if no tests were [run]`. Confirmed by running the smoke gate without the flag and observing `playwright-1 exited with code 1` followed by `SMOKE_EXIT=1`. With the flag added, Playwright exits 0 and compose exits 0.
- **Fix:** One-line edit in `test/docker-compose.test.yml`: `command` becomes `sh -c "npm ci && npx playwright test --pass-with-no-tests"`. Three-line comment block above the command explains the rationale and that the flag is harmless once Wave 2 ships specs (it only changes the empty-suite case).
- **Files modified:** `test/docker-compose.test.yml`
- **Verification:** Re-ran the canonical command end-to-end (`docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from playwright`); compose exits 0 in ~10s with cached image. Playwright stdout shows `npm ci` audit output, blank line, and exit 0 - no "No tests found" error.
- **Committed in:** `cd038f2` (Task 4 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix is necessary for the plan's own smoke gate to pass during Wave 1 (foundation only) and is a no-op once Wave 2 ships specs. No scope creep, no behavior change in the eventual full suite. The RESEARCH.md verbatim command body should be updated for any future plans derived from it; logging this here so the planner can pick it up.

## Issues Encountered

- **Playwright Docker image pull bandwidth.** `docker pull mcr.microsoft.com/playwright:v1.59.1-jammy` took ~30-60s on the first pull (single-digit GB image including all three browser builds). Subsequent runs are cached. Not a plan concern, but Wave 2 plans should not be surprised if a fresh CI runner spends time on this pull on first invocation.
- **`npx playwright test --list` exit code with zero specs.** Task 2's automated verify uses a piped `grep` to detect the "Listing"/"0 tests" lines, so the gate passes. The plan's acceptance-criteria text "exits 0" is technically incorrect for zero-spec configurations - same Playwright safety default as above. The plan-level smoke gate (Task 4) is what matters for the harness contract; that one is now green via the `--pass-with-no-tests` fix.

## User Setup Required

None - no external service configuration required. The harness uses the simulator-mode market data (`MASSIVE_API_KEY=""`) and the mocked LLM path (`LLM_MOCK=true`); no real API keys are needed by any test run.

## Next Phase Readiness

- **ROADMAP Phase 10 SC#1 closed:** compose harness up + LLM_MOCK + Playwright service co-located.
- **TEST-03 substantially closed:** the harness exists and runs end-to-end. Wave 2 spec files (`10-02` through `10-05`) auto-load via `testMatch /\d{2}-.+\.spec\.ts$/` with zero further config edits.
- **No blockers for Wave 2.** The four downstream plans can be implemented in parallel; they share the harness foundation and never need to touch `test/playwright.config.ts` or `test/docker-compose.test.yml`.
- **Recommendation for planner:** when 10-02 ships its first spec, drop `--pass-with-no-tests` from the compose command (or leave it - it is a no-op when specs exist). Either is fine; leaving it gives a graceful path if a future plan-level cleanup temporarily removes all specs.

## Self-Check: PASSED

Verified after writing this SUMMARY.md:

- `test/package.json` exists, contains `"@playwright/test": "1.59.1"` exact.
- `test/package-lock.json` exists, references `@playwright/test` 1.59.1.
- `test/playwright.config.ts` exists, contains `defineConfig`, `workers: 3`, `fullyParallel: false`, three browser projects, `baseURL` fallback, no `setupFiles`.
- `test/docker-compose.test.yml` exists, `docker compose ... config` exits 0, `context: ..`, `LLM_MOCK: "true"`, `service_healthy`, `mcr.microsoft.com/playwright:v1.59.1-jammy`, `../test:/work`, no `services.app.volumes:`, no top-level `volumes:`, no `version:` key.
- `test/README.md` exists, single H1, two paragraphs, contains the canonical command, HTML report path, and single-spec recipe; no emojis (Python `unicodedata.category` scan returned 0 So-class chars).
- `.gitignore` ends with the three appended entries; `git check-ignore` confirms `test/playwright-report/foo.html` is ignored AND `test/package.json`, `test/package-lock.json`, `test/playwright.config.ts`, `test/docker-compose.test.yml`, `test/README.md` are NOT ignored.
- Canonical one-command invocation exits 0 (verified twice; with --build and without; both ~10s on cached image).
- All four task commits exist on the worktree branch: `528e44b`, `836c9ea`, `e9535d2`, `cd038f2`.
- `git diff --name-only HEAD~4 HEAD` returns exactly: `.gitignore`, `test/README.md`, `test/docker-compose.test.yml`, `test/package-lock.json`, `test/package.json`, `test/playwright.config.ts` - no other files touched.

---
*Phase: 10-e2e-validation*
*Plan: 01*
*Completed: 2026-04-27*
