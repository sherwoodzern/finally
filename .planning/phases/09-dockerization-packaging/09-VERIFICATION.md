---
phase: 09-dockerization-packaging
verified: 2026-04-27T11:25:00Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Windows-host UAT for PowerShell scripts (start_windows.ps1, stop_windows.ps1)"
    expected: "Same idempotency + volume-preserving stop behavior as the bash counterparts; double-clicking start_windows.ps1 (or invoking from PowerShell 5.1+) builds the image (if missing), runs container with finally-data:/app/db + 8000:8000 + --env-file .env, and opens default browser; -Build forces rebuild; -NoOpen suppresses browser; stop_windows.ps1 stops + removes container while preserving volume; running stop twice exits 0."
    why_human: "pwsh is not installed on the integration-test host (macOS), so PowerShell scripts were validated by structural grep only (parity table, switches, no-PS7-only operators, no docker volume rm). The runtime contract on a real Windows host is not exercised by automated checks."
  - test: "Browser auto-open behavior on macOS / Linux start_mac.sh success"
    expected: "After `bash scripts/start_mac.sh` (no flags), default browser opens to http://localhost:8000; with `--no-open`, browser does NOT open."
    why_human: "macOS `open` and Linux `xdg-open` rely on a desktop session; cannot be asserted in headless CI or sandboxed shells. The integration test (09-03 Task 3) ran exclusively with `--no-open` and so did not exercise the auto-open path."
  - test: "Visual UI on http://localhost:8000 (after `bash scripts/start_mac.sh`)"
    expected: "The dark-theme terminal loads with a 10-ticker watchlist (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX), $10,000 cash in the header, prices streaming with green/red flash on change, sparklines accumulating, the chart area renders a selected ticker, the portfolio heatmap and P&L chart render, the trade bar accepts orders, and the AI chat panel is visible (and surfaces a 502 from /api/chat with the empty default OPENROUTER_API_KEY)."
    why_human: "Visual appearance, real-time price-flash CSS animations, sparkline rendering, and chat-panel UX cannot be asserted from curl. The container was confirmed to serve 12,830 bytes of HTML containing `<html lang=\"en\" class=\"dark\">` (Plan 09-03 Task 3 step 3); but actual rendered correctness is a human-eyes check."
  - test: "Cross-arch build (linux/amd64 vs linux/arm64) on the user's primary host architecture"
    expected: "`docker build -t finally:latest .` succeeds on the user's host arch (typically Apple Silicon arm64 or Intel/AMD amd64)."
    why_human: "Cross-arch buildx is deferred per VALIDATION manual section (Phase 9 v2 hardening). Spot-check on the user's primary architecture only. Already PASSED on macOS Apple Silicon during Plan 09-01 cold build (image hash `07a61744cb59`, 564 MB) but documented here for completeness."
---

# Phase 9: Dockerization & Packaging — Verification Report

**Phase Goal:** One Docker command produces a runnable container that boots the FinAlly terminal on http://localhost:8000 with a 10-ticker watchlist, $10k cash, working AI chat, and trades that persist across container restarts. Cross-platform start/stop scripts make this a single-command demo on macOS, Linux, and Windows.

**Verified:** 2026-04-27T11:25:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docker build -t finally:latest .` exits 0 from a multi-stage Node-20-slim → Python-3.12-slim Dockerfile (SC#1, OPS-01). | ✓ VERIFIED | 09-01-SUMMARY: cold build exit 0 in 162s; image `finally:latest` tagged; 564 MB disk / 124 MB content; both stages progressed under BuildKit; commit `5b8b456`. Dockerfile structural invariants pass: `FROM node:20-slim AS frontend-builder`, `FROM python:3.12-slim AS runtime`, both `WORKDIR` lines, both `uv sync` lines, `COPY --from=frontend-builder /app/frontend/out /app/frontend/out`, `ENV DB_PATH=/app/db/finally.db`, `VOLUME /app/db`, `EXPOSE 8000`, `STOPSIGNAL SIGINT`, exec-form `CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`. |
| 2 | Build context excludes secrets (`.env`), VCS metadata (`.git/`, `.idea/`, `.claude/`, `.planning/`), and dev artifacts (`node_modules/`, `**/.next/`, `frontend/out/`, `backend/.venv/`, `db/`, `**/__pycache__/`, tests, `*.md` except README) (OPS-01 / T-09-01, T-09-02). | ✓ VERIFIED | `.dockerignore` (commit `be8c0e2`) contains 12+ aggressive exclusions; `.env`, `.env.*` excluded with `!.env.example` negation; `!README.md` negation preserves README; lockfiles (`backend/uv.lock`, `frontend/package-lock.json`) NOT excluded (verified by negative grep). |
| 3 | `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally:latest` (via `start_mac.sh`) starts the container; `/api/health` returns `{"status":"ok"}` within 5s (SC#2a, OPS-02). | ✓ VERIFIED | 09-03-SUMMARY Task 3 steps 1-2: `docker inspect -f '{{.State.Running}}'` → `true`; `/api/health` returned `{"status":"ok"}` within 1s (well under 5s budget). VALIDATION rows 09-04-01, 09-04-02 GREEN. |
| 4 | The static frontend is served at `/` from `/app/frontend/out/index.html` (SC#2a, OPS-02 / D-01 path math). | ✓ VERIFIED | 09-03-SUMMARY Task 3 step 3: `GET /` returned 12,830 bytes of HTML containing `<html lang="en" class="dark">`. D-01 path math holds: `backend/app/lifespan.py:86 static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"` resolves to `/app/frontend/out` inside the container with `WORKDIR /app/backend`. VALIDATION row 09-04-03 GREEN. |
| 5 | `/api/stream/prices` SSE endpoint streams data inside the container (SC#2b, OPS-02). | ✓ VERIFIED | 09-03-SUMMARY Task 3 step 4: `/api/stream/prices` emitted `retry: 1000` + 1 `data:` frame in first 512 bytes (AAPL/AMZN/GOOGL prices). VALIDATION row 09-04-04 GREEN. |
| 6 | Trades persist across container stop+restart on the same named volume `finally-data` (SC#2c, OPS-02). | ✓ VERIFIED | 09-03-SUMMARY Task 3 step 7: BUY 1 AAPL @ 190.02 → cash 10000 → 9809.98; `bash scripts/stop_mac.sh && bash scripts/start_mac.sh --no-open` → cash_after = 9809.98 (PASS). Volume preserved through stop+rm cycle. VALIDATION row 09-04-05 GREEN. |
| 7 | `scripts/start_mac.sh` and `scripts/stop_mac.sh` are idempotent (re-run safe) and `stop_mac.sh` preserves the named volume (SC#3, OPS-03). | ✓ VERIFIED | 09-03-SUMMARY Task 3 step 5: second consecutive `bash scripts/start_mac.sh --no-open` exit 0; container still running. Step 8: two consecutive `bash scripts/stop_mac.sh` exit 0; `docker volume inspect finally-data` exit 0 (preserved). Step 6: `--build` flag forces rebuild ("Building finally:latest …" in output). Bash 3.2 portable: no `declare -A`, `mapfile`, `${var^^}`, `${var,,}` (verified by negative grep). VALIDATION rows 09-05-01..04 GREEN. |
| 8 | `scripts/start_windows.ps1` and `scripts/stop_windows.ps1` mirror the bash counterparts argument-for-argument (six-arg parity: `-d`, `--name finally-app`, `-v finally-data:/app/db`, `-p 8000:8000`, `--env-file .env`, `finally:latest`) (SC#3, OPS-03). | ⚠️ VERIFIED (structural only) | Files exist, `[switch]$Build` and `[switch]$NoOpen` parameters defined, `$LASTEXITCODE` checked after `docker build` and `docker run`, no PowerShell-7-only operators (`??`, ternary `?:`), no `docker volume rm` invoked as a command (only documented in user-facing hint). VALIDATION rows 09-05-05/06 deferred to manual UAT — see human_verification (pwsh not installed on integration-test host). |
| 9 | `.env.example` exists at repo root with three keys `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK=false`; no leaked secrets (SC#4a, OPS-04 / T-09-05). | ✓ VERIFIED | File exists (commit `a048102`); exactly 3 KEY= lines; `OPENROUTER_API_KEY=`, `MASSIVE_API_KEY=` (empty), `LLM_MOCK=false`; `grep -E "sk-or-v1-\|pk_test_\|sk_live_"` returns no matches. VALIDATION rows 09-03-01..03 GREEN. |
| 10 | `.env` is gitignored (SC#4b, OPS-04). | ✓ VERIFIED | `.gitignore:141` contains `.env` (existing, unchanged by Phase 9). VALIDATION row 09-03-04 GREEN. |
| 11 | `cp .env.example .env` is sufficient to boot simulator-mode demo with no edits (SC#4c, OPS-04). | ✓ VERIFIED | 09-03-SUMMARY Task 3 step 1: `cp .env.example .env` followed by `bash scripts/start_mac.sh --no-open` → container running with `MASSIVE_API_KEY` empty (simulator selected) → `/api/health` returned `{"status":"ok"}` within 1s. VALIDATION row 09-03-05 GREEN. |

**Score:** 11/11 truths verified (1 with structural-only confidence — see human_verification).

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `Dockerfile` | Multi-stage Node 20 slim → Python 3.12 slim per D-01..D-08 | ✓ VERIFIED | 65 lines; all 16 grep invariants pass (FROM lines, COPY uv, both WORKDIRs, RUN npm ci, RUN npm run build, both `uv sync` lines, `COPY --from=frontend-builder`, ENV DB_PATH, VOLUME, EXPOSE, STOPSIGNAL SIGINT, exec-form CMD). No `COPY .env`, no `HEALTHCHECK`, no `USER`. Cold build PASSED (commit `5b8b456`). |
| `.dockerignore` | Aggressive build-context filter per D-13 | ✓ VERIFIED | 64 lines; 12+ aggressive exclusions; `.env`, `db/`, `frontend/out/`, `backend/.venv/`, `**/node_modules/`, `**/__pycache__/`, `.planning/`, `.claude/`, `.git/`, `.idea/` all present; `!.env.example` and `!README.md` negations present; lockfiles preserved. (commit `be8c0e2`). |
| `.env.example` | Three keys with safe defaults per D-12 | ✓ VERIFIED | 15 lines, 648 bytes; exactly 3 KEY= lines (OPENROUTER_API_KEY=, MASSIVE_API_KEY=, LLM_MOCK=false); no leaked secrets; no DB_PATH (correctly internal). (commit `a048102`). |
| `scripts/start_mac.sh` | bash 3.2-portable idempotent start wrapper | ✓ VERIFIED | 73 lines, executable (mode 0755); parses cleanly via `bash -n`; six-arg docker run parity present; `--build` and `--no-open` flags supported; `.env`-missing pre-flight; D-09 build-on-first-run; D-11 browser-on-success; no bash-4 idioms. (commit `e52704b`). |
| `scripts/stop_mac.sh` | bash 3.2-portable idempotent stop, preserves volume | ✓ VERIFIED | 13 lines, executable (mode 0755); `docker stop \|\| true && docker rm \|\| true` idempotent; no `docker volume rm` invoked as a command (only documented in user hint per D-10). (commit `e52704b`). |
| `scripts/start_windows.ps1` | PowerShell 5.1+ mirror with byte-identical docker args | ⚠️ STRUCTURAL ONLY | 58 lines; six-arg parity confirmed; `[switch]$Build` + `[switch]$NoOpen`; `$LASTEXITCODE` checked; no PS7-only operators; uses `*> $null` (5.1 + 7.x compatible); `Resolve-Path`/`Join-Path` for cwd. pwsh not installed on integration host — runtime UAT deferred. (commit `6ae3480`). |
| `scripts/stop_windows.ps1` | PowerShell 5.1+ mirror, preserves volume | ⚠️ STRUCTURAL ONLY | 12 lines; idempotent stop+rm; no `docker volume rm` invoked as command. pwsh not installed on integration host — runtime UAT deferred. (commit `6ae3480`). |
| `docs/DOCKER.md` | Long-form reference with 7 sections per D-14 | ✓ VERIFIED | 221 lines; `grep -cE '^## (Quickstart\|Canonical run\|Image architecture\|Volume\|\.env workflow\|Troubleshooting\|Windows)$'` outputs `7`; cites all four scripts; canonical `docker run -d` + `finally-data:/app/db` + `8000:8000` + `--env-file .env` present; all three env vars documented; `--build` and `--no-open` flags documented; no leaked secrets. (commit `2057eb3`). |
| `README.md` | Quick Start ≤ 10 non-blank/non-fence lines, cites all four scripts, links docs/DOCKER.md | ✓ VERIFIED | Quick Start = 7 non-blank/non-fence lines (≤ 10 budget); cites all four scripts (one match per line, total 4); markdown link `[docs/DOCKER.md](docs/DOCKER.md)` present. (commit `88038c6`). |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Dockerfile `WORKDIR /app/backend` | `backend/app/lifespan.py:86 static_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"` | Repo-mirroring container layout (D-01) | ✓ WIRED | Verified at runtime: GET / returned 12,830 bytes of HTML (Plan 09-03 Task 3 step 3). The path math `parents[2]` from `/app/backend/app/lifespan.py` resolves to `/app`, so static_dir = `/app/frontend/out`. |
| Dockerfile `ENV DB_PATH=/app/db/finally.db` + `VOLUME /app/db` | `backend/app/lifespan.py:59 db_path = os.environ.get("DB_PATH", "db/finally.db")` | ENV pin overrides relative default; SQLite writes inside named volume | ✓ WIRED | Verified at runtime: cash 10000 → 9809.98 → 9809.98 across stop+restart (Plan 09-03 Task 3 step 7). DB persisted under `/app/db/finally.db` mapped to named volume `finally-data`. |
| Dockerfile Stage 1 `RUN npm run build` (output: 'export') | `COPY --from=frontend-builder /app/frontend/out /app/frontend/out` | Multi-stage artifact transfer | ✓ WIRED | Verified at build time: BuildKit log shows "Generating static pages using 6 workers (5/5)" then Stage 2 step 8/8 `COPY --from=frontend-builder` succeeded. Verified at runtime: `<html lang="en" class="dark">` served at `/`. |
| `.env.example` (`MASSIVE_API_KEY=` empty) | `backend/app/market/factory.py: os.environ.get('MASSIVE_API_KEY')` | Empty value → `SimulatorDataSource` selected | ✓ WIRED | Verified at runtime: container logs showed simulator was selected; `/api/stream/prices` emitted AAPL/AMZN/GOOGL price frames (Plan 09-03 Task 3 step 4). |
| `.env.example` → user copies to `.env` | `backend/app/main.py:16 load_dotenv()` | dotenv reads at app construction | ✓ WIRED | Verified at runtime: `cp .env.example .env && start_mac.sh` → `/api/health` returned `{"status":"ok"}` (Plan 09-03 Task 3 step 1-2). |
| `start_mac.sh` six-arg `docker run` | PLAN.md §11 canonical invocation + Dockerfile `VOLUME /app/db` + `EXPOSE 8000` | Six-argument parity per PATTERNS.md | ✓ WIRED | All six args present in script: `-d`, `--name finally-app`, `-v finally-data:/app/db`, `-p 8000:8000`, `--env-file .env`, `finally:latest`. Verified at runtime: container started, /api/health = ok, GET /, SSE, trade persistence all PASSED. |
| `start_windows.ps1` six-arg `docker run` | PLAN.md §11 canonical invocation | Argument parity with `start_mac.sh` | ⚠️ PARTIAL | Structural parity confirmed (file content matches bash counterpart's args). Runtime parity not exercised — pwsh not on integration host. See human_verification. |
| `README.md` Quick Start | `scripts/start_mac.sh`, `scripts/stop_mac.sh`, `scripts/start_windows.ps1`, `scripts/stop_windows.ps1` | Quick Start cites all four scripts | ✓ WIRED | grep count = 4 (one citation per line). Markdown link `[docs/DOCKER.md](docs/DOCKER.md)` present. |
| `docs/DOCKER.md` Canonical run section | PLAN.md §11 + Dockerfile + scripts | Verbatim invocation matching scripts' arguments | ✓ WIRED | Documents `docker run -d --name finally-app -v finally-data:/app/db -p 8000:8000 --env-file .env finally:latest` exactly as the scripts wrap. |

---

### Data-Flow Trace (Level 4)

Phase 9 ships infrastructure (Dockerfile, scripts, env templates, docs) — not components that render dynamic data. Level 4 trace is therefore exercised through the integration test rather than per-artifact:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Container `/api/portfolio` (read inside running image) | `cash_balance` | SQLite at `/app/db/finally.db` (named volume `finally-data`) | Yes — 10000 → 9809.98 after BUY 1 AAPL | ✓ FLOWING |
| Container `/api/stream/prices` (SSE) | price stream | SimulatorDataSource (MASSIVE_API_KEY empty in `.env.example`) | Yes — AAPL/AMZN/GOOGL `data:` frames in first 512 bytes | ✓ FLOWING |
| Container `GET /` | static HTML | `/app/frontend/out/index.html` (Stage 1 → Stage 2 COPY) | Yes — 12,830 bytes of `<html lang="en" class="dark">` | ✓ FLOWING |

---

### Behavioral Spot-Checks

Behavioral spot-checks for Phase 9 were exercised inline by the Plan 09-03 Task 3 integration suite (run against a live Docker daemon). Re-running them at verify-time would require docker-daemon access; the recorded results from 09-03-SUMMARY are the canonical evidence.

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Cold build produces tagged image | `docker build -t finally:latest .` | exit 0 in 162s; image 564 MB disk / 124 MB content | ✓ PASS |
| Container starts and stays running | `bash scripts/start_mac.sh --no-open && docker inspect -f '{{.State.Running}}' finally-app` | `true` | ✓ PASS |
| Health endpoint OK within 5s | `curl -fsS http://localhost:8000/api/health` | `{"status":"ok"}` within 1s | ✓ PASS |
| Static frontend served | `curl -fsS http://localhost:8000/` | 12,830 bytes; `<html lang="en" class="dark">` | ✓ PASS |
| SSE stream emits `data:` frames | `curl -N -fsS http://localhost:8000/api/stream/prices \| head -c 256` | `retry: 1000` + `data:` frames (AAPL/AMZN/GOOGL) | ✓ PASS |
| Volume persists trades across restart | trade → stop → start → re-read cash | 10000 → 9809.98 → 9809.98 | ✓ PASS |
| `start_mac.sh` idempotent | re-run after success | second invocation exit 0; container still running | ✓ PASS |
| `--build` flag forces rebuild | `bash scripts/start_mac.sh --build --no-open` | output contains "Building finally:latest" | ✓ PASS |
| `stop_mac.sh` idempotent + preserves volume | two consecutive `stop_mac.sh` + `docker volume inspect finally-data` | both exit 0; volume preserved | ✓ PASS |
| pwsh syntax check on Windows scripts | `pwsh -NoProfile -Command "Get-Command -Syntax ./scripts/start_windows.ps1"` | not run — pwsh not installed | ? SKIP |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| OPS-01 | 09-01 | Multi-stage Dockerfile (Node 20 slim → Python 3.12 slim) | ✓ SATISFIED | Dockerfile committed `5b8b456`; cold build exit 0 in 162s; image `finally:latest` produces `/app/frontend/out/index.html`; `.dockerignore` `be8c0e2` excludes 12+ aggressive patterns. Truths #1, #2 verified. |
| OPS-02 | 09-03, 09-04 | Single-container runtime — canonical `docker run` works | ✓ SATISFIED | `start_mac.sh` wraps the canonical `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally:latest`; integration test PASSED for /api/health, GET /, SSE, trade persistence. docs/DOCKER.md Canonical run section documents the verbatim invocation. Truths #3, #4, #5, #6 verified. |
| OPS-03 | 09-03 | Idempotent start/stop scripts (mac + windows) | ✓ SATISFIED for mac; ⚠️ STRUCTURAL for windows | All four scripts exist; mac scripts pass full integration suite (idempotent start, --build flag, idempotent stop, volume preservation); Windows scripts pass structural grep parity but pwsh not installed on integration host — Windows runtime UAT in human_verification. Truths #7, #8 verified. |
| OPS-04 | 09-02, 09-04 | `.env.example` committed with safe placeholder values; `.env` listed in `.gitignore` | ✓ SATISFIED | `.env.example` committed `a048102` with three keys, no leaked secrets; `.gitignore:141` confirms `.env` ignored; `cp .env.example .env` boots simulator-mode demo (Plan 09-03 Task 3 step 1). docs/DOCKER.md `.env workflow` section documents the contract. Truths #9, #10, #11 verified. |

**No orphaned requirements.** REQUIREMENTS.md maps OPS-01..04 to Phase 9 only; all four are claimed by at least one plan in this phase.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | No TODO/FIXME/placeholder/stub markers in any Phase 9 artifact. |

Targeted scan covered: Dockerfile, .dockerignore, .env.example, scripts/{start,stop}_{mac,windows}.{sh,ps1}, docs/DOCKER.md, README.md. Two informational hits (not anti-patterns):

- `scripts/stop_mac.sh:13` and `scripts/stop_windows.ps1:11` contain the literal string `docker volume rm finally-data` inside a `Write-Host`/`echo` user-facing hint. The plan's automated verify block over-restricted on this (asserted `! grep -q "docker volume rm"` against the prescribed body). Functional contract — "stop preserves the volume" — is upheld: neither script invokes `docker volume rm` as a command. Documented in 09-03-SUMMARY Deviation #2 as a plan-defect, not a code defect. **Severity: ℹ️ Info.**
- 09-03-SUMMARY documents that the user's pre-existing `.env` had a trailing space on `OPENROUTER_API_KEY ` that Docker rejected with `invalid env file (.env): variable 'OPENROUTER_API_KEY ' contains whitespaces`. The script propagates Docker's error verbatim, which is the desired fail-loud behavior. **Severity: ℹ️ Info — out of scope; documented for ops awareness.**

---

### Gaps Summary

**No blocking gaps.** All 11 truths verified, all 9 artifacts in place, all 9 key links wired, all 4 OPS requirements satisfied. Anti-pattern scan clean. Phase 9 goal is mechanically met.

The `human_needed` status is driven by intrinsically non-programmatic verifications:

1. **Windows-host UAT for PowerShell scripts.** The two `.ps1` files passed all structural checks (six-arg parity, switch parameters, `$LASTEXITCODE` checks, no PS7-only operators, no `docker volume rm` invocation), but pwsh was not installed on the integration-test host. The runtime contract on a real Windows host is the only thing that exercises Docker-Desktop-for-Windows + WSL2 path. Recommended UAT script:

   ```powershell
   Copy-Item .env.example .env
   .\scripts\start_windows.ps1 -NoOpen
   curl http://localhost:8000/api/health
   .\scripts\start_windows.ps1 -NoOpen          # idempotent re-run
   .\scripts\start_windows.ps1 -Build -NoOpen   # force rebuild
   .\scripts\stop_windows.ps1
   .\scripts\stop_windows.ps1                   # idempotent stop
   docker volume inspect finally-data           # preserved
   ```

2. **Browser auto-open behavior.** The integration suite ran exclusively with `--no-open` (CI-friendly). The `open`/`xdg-open`/`Start-Process` paths in the scripts work via shell association and were not exercised at verify-time.

3. **Visual UI on http://localhost:8000.** The container serves valid HTML (12,830 bytes containing `<html lang="en" class="dark">`), but visual correctness — price-flash animations, sparklines accumulating, heatmap colors, chat panel UX — requires human eyes against the running terminal. This is intrinsic to UI verification (carried from VALIDATION.md Manual-Only section).

4. **Cross-arch build spot-check.** Cross-arch buildx is deferred to v2 hardening. The user should confirm `docker build -t finally:latest .` succeeds on their primary host arch. Already PASSED on the integration host (macOS Apple Silicon arm64) via Plan 09-01 cold build (image `07a61744cb59`, 564 MB / 124 MB content).

### Pre-existing baseline (not Phase 9 scope)

- 5-error TSC baseline in `frontend/MainChart.test.tsx` and `Sparkline.test.tsx` (carried from Phase 7/8). Out of scope for Phase 9 (no `requirements: [TEST-*]`); not a Phase 9 gap.

---

_Verified: 2026-04-27T11:25:00Z_
_Verifier: Claude (gsd-verifier)_
