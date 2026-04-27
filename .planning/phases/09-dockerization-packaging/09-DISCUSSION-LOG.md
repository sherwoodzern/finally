# Phase 9 Discussion Log (auto-mode)

**Date:** 2026-04-26
**Mode:** `/gsd-discuss-phase 9 --auto`
**Approach:** All gray areas auto-selected; recommended option per area chosen without interactive prompts. This file captures the option matrix each decision came from so the human user (and downstream agents) can audit the choices.

For the locked decisions themselves, see `09-CONTEXT.md`.

---

## Gray Area 1 — Container file layout / static_dir resolution

**Question:** How should the container lay out source files so FastAPI's `StaticFiles` mount finds `frontend/out/`?

**`backend/app/lifespan.py` resolves the static dir as `Path(__file__).resolve().parents[2] / "frontend" / "out"`.**

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: Mirror dev tree (`/app/backend/`, `/app/frontend/out/`)** | Zero code changes, identical to dev layout, `parents[2]` resolves naturally | Slightly more `COPY` lines | **✓ recommended (D-01)** |
| B: Add `STATIC_DIR` env var, patch lifespan.py | Decouples runtime layout from code | Drags Phase 9 into a Phase-8 contract change; touches a file owned by another phase |  |

**Auto-selected:** A — mirrors the dev tree, no code change needed.

---

## Gray Area 2 — Image base & multi-stage layout

**Question:** Which base images and split between stages?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: `node:20-slim` (build) + `python:3.12-slim` (runtime)** | Documented in PLAN.md §11; `slim` has glibc that LiteLLM + numpy wheels resolve cleanly against | Bigger than distroless | **✓ recommended (D-02)** |
| B: Distroless final stage | Smallest, no shell | Harder to debug; `uv` and `nodejs` startup quirks |  |
| C: Alpine (musl) | Smallest with shell | numpy + LiteLLM wheel availability is fragile on musl |  |

**Auto-selected:** A — matches PLAN.md, lowest risk for the wheel chain (numpy + LiteLLM).

---

## Gray Area 3 — Dependency install determinism

**Question:** How are frontend and backend deps installed in the image?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: `npm ci` (Stage 1) + `uv sync --frozen --no-dev` (Stage 2)** | Lockfile-deterministic; fails fast if drift; excludes test/lint deps from runtime | Requires committed `package-lock.json` and `uv.lock` (already committed) | **✓ recommended (D-03)** |
| B: `npm install` + `uv sync` | Tolerant of stale lockfiles | Non-reproducible; can introduce a fresh dep into the image |  |
| C: `npm ci` + `uv sync --extra dev` | Determinism + extras included | Bloats runtime image with vitest/pytest/ruff/playwright |  |

**Auto-selected:** A — best determinism + smallest runtime image.

---

## Gray Area 4 — Container user (root vs appuser)

**Question:** Run the container process as root, or create a non-root user?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: Run as root (single-user localhost demo)** | Simpler Dockerfile; no permission edge cases on Docker Desktop volume mounts | "Don't run as root" is a security best-practice default | **✓ recommended (D-04)** |
| B: `useradd appuser && USER appuser` | Defense in depth | Volume permissions on Docker Desktop for Mac/Win sometimes need explicit `chown`; capstone scope doesn't pay back the complexity |  |

**Auto-selected:** A — single-user localhost demo; deferred to v2 hardening.

---

## Gray Area 5 — DB persistence: env var + volume declaration

**Question:** How does the SQLite database persist across container restarts?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: `ENV DB_PATH=/app/db/finally.db` + `VOLUME /app/db` + named volume `finally-data`** | Matches PLAN.md §11 verbatim and ROADMAP SC#2 | None for the capstone | **✓ recommended (D-05)** |
| B: Bind mount to host path | Easier to inspect on host | Cross-platform path differences (macOS vs Windows); not the documented invocation |  |

**Auto-selected:** A — matches the PLAN.md canonical invocation.

---

## Gray Area 6 — `.env` handling at runtime

**Question:** How does the container get its environment variables?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: `--env-file .env` at `docker run` time** | Secrets stay out of image layers; rotate `OPENROUTER_API_KEY` without rebuild | User must remember to copy `.env.example` → `.env` (covered by start script) | **✓ recommended (D-06)** |
| B: `COPY .env .env` in Dockerfile | Simpler run command | Bakes secrets into image layers; rebuild required on key rotation; image not portable |  |

**Auto-selected:** A — also matches PLAN.md §11.

---

## Gray Area 7 — `docker-compose.yml` in production?

**Question:** Should Phase 9 ship a `docker-compose.yml` for the prod path?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: No — single-container `docker run` only** | PLAN.md §3 explicitly excludes compose from prod; one less moving piece | Users who prefer compose will have to write their own (trivial) | **✓ recommended (D-07)** |
| B: Yes, optional convenience compose file | One-line `docker compose up` start | Two paths to maintain; muddies the canonical invocation |  |

**Auto-selected:** A — honors PLAN.md.

---

## Gray Area 8 — `HEALTHCHECK` clause in the Dockerfile?

**Question:** Should the Dockerfile carry a `HEALTHCHECK CMD` line?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: No HEALTHCHECK** | Smaller Dockerfile; the demo signal is "browser opens"; cloud orchestrators inject their own probes | `docker ps` STATUS column won't show health for the running container | **✓ recommended (D-08)** |
| B: HEALTHCHECK CMD with curl | Visible health in `docker ps` | Requires `apt-get install curl` in slim → bigger image; or a Python one-liner that's noisy |  |

**Auto-selected:** A — capstone demo doesn't need it; v2 cloud deploy adds external probes.

---

## Gray Area 9 — Build-on-first-run vs always-rebuild in scripts

**Question:** When `scripts/start_mac.sh` runs, should it always `docker build` first?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: Build only if image absent or `--build` flag passed** | Fast subsequent starts; explicit flag for forced rebuild | Drift possible between source and running image (mitigated by the `--build` flag) | **✓ recommended (D-09)** |
| B: Always rebuild | No drift | Slow start every time; bad demo UX |  |
| C: Never rebuild (require manual `docker build`) | Predictable | Hostile first-run experience |  |

**Auto-selected:** A — best demo UX with an escape hatch.

---

## Gray Area 10 — Stop-script semantics

**Question:** What does `scripts/stop_mac.sh` do, and does it touch the volume?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: `docker stop` + `docker rm` of the container; volume preserved** | Idempotent; data survives restarts (the whole point of the named volume) | Users wanting a full reset must `docker volume rm finally-data` manually | **✓ recommended (D-10)** |
| B: Also `docker volume rm finally-data` | Full reset in one command | Surprising data loss; demo state evaporates |  |

**Auto-selected:** A — preserves data by default; `--purge` deferred to ideas.

---

## Gray Area 11 — `.env.example` defaults

**Question:** What values does the committed `.env.example` carry?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: All keys present with safe defaults that boot the simulator-mode demo (`OPENROUTER_API_KEY=`, `MASSIVE_API_KEY=`, `LLM_MOCK=false`)** | Satisfies SC#4 verbatim — copy → run works; chat 502s gracefully without key, but everything else streams | User must add `OPENROUTER_API_KEY` to use chat | **✓ recommended (D-12)** |
| B: All keys present, all empty | Slightly simpler | `LLM_MOCK=` is interpreted as the default ("false"); trivial difference |  |
| C: Real placeholder strings (`OPENROUTER_API_KEY=sk-or-v1-...`) | Discoverable | Risks the user pushing the placeholder unchanged |  |

**Auto-selected:** A — matches SC#4 wording exactly.

---

## Gray Area 12 — `.dockerignore` aggressiveness

**Question:** What does `.dockerignore` exclude?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: Aggressive — exclude `node_modules/`, `.next/`, `.venv/`, `__pycache__/`, `*.pyc`, `frontend/out/`, `.git/`, `.idea/`, `.claude/`, `.planning/`, `db/`, all test files, all `*.md` except `README.md`** | Smallest build context; fastest builds; reproducible (host's dev artifacts can't leak in) | More lines to maintain | **✓ recommended (D-13)** |
| B: Minimal — just `node_modules/` and `.git/` | Shorter file | Build context bloats with `.next/` cache, `.venv/`, IDE files, planning docs |  |

**Auto-selected:** A — keeps Stage 1 reproducible; the host's `frontend/out/` MUST NOT shadow the in-image rebuild.

---

## Gray Area 13 — Documentation footprint

**Question:** Where do the Docker run instructions live?

| Option | Pros | Cons | Recommendation |
|---|---|---|---|
| **A: 10-line Quick Start in `README.md` + `docs/DOCKER.md` long-form reference** | Onboarding answer is right where users look (top of README); deep dive is one click away | Two files to keep in sync | **✓ recommended (D-14)** |
| B: All in README | One file | Long README; troubleshooting section dominates the Quick Start |  |
| C: All in docs/DOCKER.md, README points to it | Clean README | Users who skim README miss the demo invocation |  |

**Auto-selected:** A — best balance; matches the project's "concise README" rule from CLAUDE.md.

---

## Auto-mode summary

- **14 gray areas surfaced; 14 decisions locked** (D-01 through D-14 in `09-CONTEXT.md`).
- **Zero scope creep** — each decision either implements an OPS-0X requirement or supports an existing PLAN.md §11 contract.
- **No ambiguity left for the planner:** the Dockerfile structure, dep-install commands, layout paths, env handling, volume name, and script semantics are all locked.
- **Deferred ideas captured** in CONTEXT.md `<deferred>` so nothing valuable was lost.

Next: `/gsd-plan-phase 9 --auto` (auto-advance per `--auto` flag chain).
