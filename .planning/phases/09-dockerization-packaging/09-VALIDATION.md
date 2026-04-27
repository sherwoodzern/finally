---
phase: 09
slug: dockerization-packaging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Phase 9 is an infra phase: most validations are shell commands against a built image and a running container, not unit tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bash + `docker` CLI for image/container checks; existing `pytest` for backend regression; existing `vitest` for frontend regression. |
| **Config file** | none (image-build checks live in `scripts/` and Dockerfile RUN steps) |
| **Quick run command** | `docker build -t finally:latest . && docker run --rm finally:latest python -c "import app; print('ok')"` (~30s build, ~2s smoke) |
| **Full suite command** | `bash scripts/start_mac.sh` followed by the 16 OPS-01..04 acceptance checks listed in 09-RESEARCH.md §"Validation Architecture" |
| **Estimated runtime** | ~90s for build + 60s for full acceptance suite (~150s total cold) |

---

## Sampling Rate

- **After every task commit:** Run the relevant subset (e.g., `.dockerignore` task → `docker build` exits 0; script task → `bash -n scripts/start_mac.sh` parses).
- **After every plan wave:** Run `docker build` end-to-end, then `docker run` with the canonical args, then a `curl http://localhost:8000/api/health` smoke.
- **Before `/gsd-verify-work`:** All 16 OPS-01..04 acceptance checks pass.
- **Max feedback latency:** 90s (one full image build + container start).

---

## Per-Task Verification Map

This map locks the verification command for each requirement-bearing artifact. Plan IDs (`09-01-01`, etc.) are placeholders — the planner will materialize the actual plan/wave numbers; the verification commands stay anchored to the file/requirement.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-01 | Dockerfile | 1 | OPS-01 | — | Multi-stage build produces a runnable image | shell | `docker build -t finally:latest .` exit 0 | ❌ W0 (creates Dockerfile) | ⬜ pending |
| 09-01-02 | Dockerfile | 1 | OPS-01 | — | Stage 1 produces `frontend/out/index.html` inside builder | shell | `docker build -t finally:latest --target builder .` then `docker run --rm finally:latest test -f /app/frontend/out/index.html` exit 0 | ❌ W0 | ⬜ pending |
| 09-01-03 | Dockerfile | 1 | OPS-01 | — | Stage 2 has runtime deps but NO test/lint deps | shell | `docker run --rm finally:latest python -c "import pytest" 2>&1 \| grep -q "ModuleNotFoundError"` (must succeed — pytest absent) | ❌ W0 | ⬜ pending |
| 09-01-04 | Dockerfile | 1 | OPS-01 | T-09-secret | `.env` is NOT baked into the image | shell | `docker run --rm finally:latest test ! -e /app/.env` exit 0 | ❌ W0 | ⬜ pending |
| 09-01-05 | Dockerfile | 1 | OPS-01 | — | Static dir resolves to `/app/frontend/out` from `/app/backend/app/lifespan.py` | shell | `docker run --rm finally:latest python -c "from pathlib import Path; print(Path('/app/backend/app/lifespan.py').resolve().parents[2])"` outputs `/app` | ❌ W0 | ⬜ pending |
| 09-02-01 | dockerignore | 1 | OPS-01 | T-09-bloat | Build context excludes host artifacts | shell | `grep -E "^(node_modules\|\.next\|frontend/out\|\.venv\|__pycache__\|\.planning\|\.claude\|\.git\|\.idea\|db)" .dockerignore` returns ≥10 matches | ❌ W0 | ⬜ pending |
| 09-02-02 | dockerignore | 1 | OPS-01 | — | Build context size is bounded | shell | `du -sh $(docker build -q .) \| awk '{print $1}'` < 500MB | ❌ W0 | ⬜ pending |
| 09-03-01 | env-example | 1 | OPS-04 | — | `.env.example` exists at repo root | shell | `test -f .env.example` exit 0 | ❌ W0 | ⬜ pending |
| 09-03-02 | env-example | 1 | OPS-04 | — | Three documented env keys present | shell | `grep -c "^OPENROUTER_API_KEY=\\\|^MASSIVE_API_KEY=\\\|^LLM_MOCK=" .env.example` outputs `3` | ❌ W0 | ⬜ pending |
| 09-03-03 | env-example | 1 | OPS-04 | T-09-secret | `.env.example` does NOT contain a real API key | shell | `grep -E "sk-or-v1-\|pk_test_" .env.example` returns no matches (exit 1) | ❌ W0 | ⬜ pending |
| 09-03-04 | env-example | 1 | OPS-04 | — | `.env` remains gitignored | shell | `grep -q "^\\.env$" .gitignore` exit 0 | ✅ existing | ⬜ pending |
| 09-03-05 | env-example | 1 | OPS-04 | — | Copy → run produces simulator-mode demo | shell | `cp .env.example .env.test && docker run --rm --env-file .env.test -d --name finally-uat -p 8000:8000 finally:latest && sleep 3 && curl -fsS http://localhost:8000/api/health \| grep -q '"status":"ok"' && docker stop finally-uat` exit 0 | ❌ W0 | ⬜ pending |
| 09-04-01 | run + volume | 2 | OPS-02 | — | Canonical `docker run` from PLAN.md §11 starts container | shell | `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env -d --name finally-app finally:latest` exit 0 | ❌ W0 | ⬜ pending |
| 09-04-02 | run + volume | 2 | OPS-02 | — | App reachable on port 8000 | shell | After `docker run`, `curl -fsS http://localhost:8000/api/health \| grep -q '"status":"ok"'` exit 0 within 5s | ❌ W0 | ⬜ pending |
| 09-04-03 | run + volume | 2 | OPS-02 | — | Static frontend served at `/` | shell | `curl -fsS -H 'Accept: text/html' http://localhost:8000/ \| grep -q '<html'` exit 0 | ❌ W0 | ⬜ pending |
| 09-04-04 | run + volume | 2 | OPS-02 | — | SSE endpoint streams in container | shell | `curl -N -fsS http://localhost:8000/api/stream/prices \| head -c 256 \| grep -q "data:"` exit 0 | ❌ W0 | ⬜ pending |
| 09-04-05 | run + volume | 2 | OPS-02 | — | Volume persists trades across restart | shell | Place a trade via `POST /api/portfolio/trade`; `docker stop finally-app && docker rm finally-app && docker run ...` (same volume); `curl /api/portfolio` shows the trade | ❌ W0 | ⬜ pending |
| 09-05-01 | scripts mac | 3 | OPS-03 | — | `scripts/start_mac.sh` is executable + bash 3.2 parses | shell | `test -x scripts/start_mac.sh && bash -n scripts/start_mac.sh` exit 0 | ❌ W0 | ⬜ pending |
| 09-05-02 | scripts mac | 3 | OPS-03 | — | `start_mac.sh` is idempotent (re-run is safe) | shell | `bash scripts/start_mac.sh && bash scripts/start_mac.sh` exit 0 (second run reuses image) | ❌ W0 | ⬜ pending |
| 09-05-03 | scripts mac | 3 | OPS-03 | — | `--build` flag forces rebuild | shell | `bash scripts/start_mac.sh --build 2>&1 \| grep -q "docker build"` exit 0 | ❌ W0 | ⬜ pending |
| 09-05-04 | scripts mac | 3 | OPS-03 | — | `stop_mac.sh` is idempotent + preserves volume | shell | `bash scripts/stop_mac.sh && bash scripts/stop_mac.sh && docker volume inspect finally-data` exit 0 | ❌ W0 | ⬜ pending |
| 09-05-05 | scripts win | 3 | OPS-03 | — | `start_windows.ps1` parses on PowerShell 5.1+ | shell | `pwsh -NoProfile -Command "Get-Command -Syntax ./scripts/start_windows.ps1"` exit 0 (or `powershell.exe` on Windows) | ❌ W0 | ⬜ pending |
| 09-05-06 | scripts win | 3 | OPS-03 | — | `stop_windows.ps1` parses on PowerShell 5.1+ | shell | `pwsh -NoProfile -Command "Get-Command -Syntax ./scripts/stop_windows.ps1"` exit 0 | ❌ W0 | ⬜ pending |
| 09-06-01 | docs | 4 | OPS-02, OPS-04 | — | `docs/DOCKER.md` exists with seven sections | shell | `grep -cE "^## (Quickstart\\\|Canonical run\\\|Image architecture\\\|Volume\\\|.env workflow\\\|Troubleshooting\\\|Windows)" docs/DOCKER.md` outputs `7` | ❌ W0 | ⬜ pending |
| 09-06-02 | docs | 4 | OPS-02 | — | README Quick Start updated to ≤10 lines | shell | `awk '/^## Quick Start/,/^## /' README.md \| grep -c "^[^#]" \| awk '$1 <= 10 {exit 0} {exit 1}'` exit 0 | ✅ existing (will be edited) | ⬜ pending |
| 09-06-03 | docs | 4 | OPS-02 | — | README Quick Start cites the four scripts | shell | `grep -c "scripts/start_mac.sh\\\|scripts/stop_mac.sh\\\|scripts/start_windows.ps1\\\|scripts/stop_windows.ps1" README.md` outputs ≥4 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `bash` (system, macOS 3.2+ confirmed) — start/stop scripts
- [x] `docker` CLI (Docker Desktop or Docker Engine) — build/run/stop image
- [x] `curl` (system) — `/api/health` smoke
- [x] Existing `pytest` and `vitest` infrastructure carries forward; **no new test framework needed for Phase 9** (validation is shell + curl).
- [ ] **Image-build smoke must run BEFORE any task commits** to catch Dockerfile typos early; planner adds this as a wave-1 gate.

*Phase 9 has no per-task unit tests because the artifacts are infrastructure, not code. Verification is by `docker build` exit code, `curl` output against a running container, and grep-on-file checks for `.dockerignore` / `.env.example` / scripts.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser auto-open on `start_mac.sh` success | OPS-03 | macOS `open <url>` opens the default browser; cannot be asserted in CI on a headless agent. | After `bash scripts/start_mac.sh`, default browser opens to `http://localhost:8000`. |
| Browser auto-open on `start_windows.ps1` success | OPS-03 | `Start-Process http://...` opens default browser; same headless caveat. | After `./scripts/start_windows.ps1`, default browser opens to `http://localhost:8000`. |
| Cross-arch image (`linux/amd64` vs `linux/arm64`) | OPS-01 (deferred) | Cross-arch buildx is deferred to v2 per CONTEXT.md `<deferred>`; spot-check on the user's primary architecture only. | `docker build -t finally:latest .` succeeds on the user's host arch. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (Phase 9 is dense in shell verifications — easily met)
- [ ] Wave 0 covers all MISSING references (none — bash/docker/curl exist on host)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter (planner sets after every plan task carries an `<automated>` block matching the table above)

**Approval:** pending — flips to approved after the planner produces 09-NN-PLAN.md files and the plan-checker confirms 100% coverage of this table.
