---
phase: 09-dockerization-packaging
reviewed: 2026-04-27T12:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - Dockerfile
  - .dockerignore
  - .env.example
  - scripts/start_mac.sh
  - scripts/stop_mac.sh
  - scripts/start_windows.ps1
  - scripts/stop_windows.ps1
  - docs/DOCKER.md
  - README.md
findings:
  critical: 0
  warning: 0
  info: 4
  total: 4
status: clean
---

# Phase 9: Code Review Report

**Reviewed:** 2026-04-27T12:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** clean

## Summary

Reviewed all nine Phase 9 dockerization/packaging artifacts (Dockerfile, .dockerignore,
.env.example, four start/stop scripts, docs/DOCKER.md, README.md) against the Phase 9 plans,
PLAN.md section 11, and the project skill set in `.claude/skills/`. The review focused on the
concerns flagged by the orchestrator: Dockerfile security/correctness, .dockerignore breadth
and rescue patterns, secret leakage in `.env.example`, bash 3.2 portability with strict-mode
discipline, PowerShell 5.1 compatibility, and factual accuracy of the docs against the
shipped artifacts.

No Critical or Warning issues were found. The artifacts are well-aligned with PLAN.md,
defend against the well-known Dockerfile and shell-scripting pitfalls (no leaked secrets,
no command injection, no shell-form CMD, exec form with proper STOPSIGNAL, idempotent
container lifecycle, named-volume-only persistence), and the docs accurately reflect what
ships in the image.

Four Info-level observations are noted below — none block the phase. They are quality
nits worth tracking for a future polish pass:

1. Strict-mode inconsistency between `start_mac.sh` (`set -euo pipefail`) and
   `stop_mac.sh` (`set -eu`).
2. README Quick Start block presents `start` and `stop` adjacent without a separator,
   slightly ambiguous to a top-to-bottom reader.
3. `.dockerignore` could benefit from a comment explaining why `planning/` (no leading
   dot) is listed alongside `.planning/` — the former is the long-form spec dir; the
   latter is GSD agent state.
4. `docs/DOCKER.md` example `docker exec -it finally-app /bin/bash` works on
   `python:3.12-slim` but is fragile if the base image is ever swapped to a true
   distroless variant; `/bin/sh` would be a safer default.

Cross-checks performed and passed:

- `frontend/next.config.mjs` declares `output: 'export'` (matches Stage 1 build).
- `backend/app/lifespan.py` reads `DB_PATH` (line 59) defaulting to `db/finally.db`,
  and resolves `Path(__file__).resolve().parents[2] / "frontend" / "out"` (line 86) —
  consistent with `WORKDIR /app/backend` + `COPY ... /app/frontend/out` in the
  Dockerfile.
- `backend/pyproject.toml` requires Python `>=3.12` (matches `python:3.12-slim`).
- `frontend/package.json` engines field requires `node >=20.0.0 <21` (matches
  `node:20-slim`).
- `.env.example` contains no real-key prefixes (`sk-or-v1-`, `pk_test_`, `sk_live_`,
  raw `sk-`); all three keys are empty or `false`.
- `.dockerignore` correctly excludes `.env`, `.env.*`, `.git/`, `.planning/`,
  `**/node_modules/`, `**/.venv/`, and rescues `.env.example` and `README.md` from
  broader patterns.
- `scripts/start_mac.sh` has no `[[ ]]`, no associative arrays, no process
  substitution — bash 3.2 portable. All variable expansions in `docker run` are
  double-quoted (`"${VOLUME_NAME}:/app/db"`, `"${PORT}:${PORT}"`).
- `scripts/start_windows.ps1` uses no PS 7-only operators (no `??`, no `?:` ternary,
  no `&&`/`||` pipeline-chain). `[CmdletBinding()]` + `param([switch]...)` is
  PS 5.1-clean. `$LASTEXITCODE` is checked after `docker build` and `docker run`.
- Both stop scripts preserve the `finally-data` named volume and tell the user how
  to remove it explicitly.
- DOCKER.md relative links (`../README.md`, `../planning/PLAN.md`) resolve correctly
  from `docs/`.

## Info

### IN-01: Strict-mode inconsistency between mac scripts

**File:** `scripts/stop_mac.sh:5`
**Issue:** `start_mac.sh` uses `set -euo pipefail` (line 5) but `stop_mac.sh` uses only
`set -eu`. There are no pipes in `stop_mac.sh` today, so the missing `pipefail` is harmless
in practice — but the inconsistency is a small foot-gun if someone later adds a pipeline
(e.g., `docker ps | grep ...`) and the failure of the left-hand command is silently
swallowed.
**Fix:** Make the two scripts symmetric by promoting `stop_mac.sh` to the same strictness
as `start_mac.sh`:

```bash
set -euo pipefail
```

This is a one-line change with no behavioral risk for the current script body.

### IN-02: README Quick Start mixes start and stop in a single block

**File:** `README.md:18-24`
**Issue:** The Quick Start fenced code block lists four commands back-to-back with no
visual or comment separator:

```bash
cp .env.example .env                # add OPENROUTER_API_KEY
./scripts/start_mac.sh              # macOS / Linux
./scripts/stop_mac.sh               # macOS / Linux (when done)
scripts/start_windows.ps1           # Windows PowerShell
scripts/stop_windows.ps1            # Windows PowerShell (when done)
```

A user copy-pasting the whole block (a common impulse) would start the app and
immediately stop it, then try to start it on Windows. The "(when done)" comment is the
only signal not to run them sequentially.
**Fix:** Split into two blocks (start first, stop second) or insert a blank-comment
separator. Lowest-touch fix:

```bash
# Start (choose your platform)
cp .env.example .env                # add OPENROUTER_API_KEY
./scripts/start_mac.sh              # macOS / Linux
scripts/start_windows.ps1           # Windows PowerShell

# Stop (when done; data is preserved in the finally-data volume)
./scripts/stop_mac.sh
scripts/stop_windows.ps1
```

### IN-03: `.dockerignore` planning-dir entries lack rationale

**File:** `.dockerignore:13,51`
**Issue:** Two different planning directories are excluded — `.planning/` (line 13,
GSD agent state) and `planning/` (line 51, long-form project spec containing PLAN.md
and MARKET_*.md). A future contributor diffing the file may not know why both exist
or whether one is a typo for the other.
**Fix:** Add a one-line comment above line 51 to disambiguate:

```
# Long-form spec dir (PLAN.md, MARKET_*.md). Not needed in image; backend reads
# nothing from planning/ at runtime.
planning/
```

### IN-04: `docker exec` example assumes bash in base image

**File:** `docs/DOCKER.md:51`
**Issue:** The troubleshooting example `docker exec -it finally-app /bin/bash` works
today because `python:3.12-slim` ships bash. If the base image is ever switched to a
true distroless or alpine-based slim, `/bin/bash` will not exist and the example
breaks. `/bin/sh` is universally available on every Debian-derived base.
**Fix:** Prefer the lowest-common-denominator shell in the docs example:

```bash
docker exec -it finally-app /bin/sh                       # shell inside the container
```

This is a doc-only change; no script behavior depends on the choice.

---

_Reviewed: 2026-04-27T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
