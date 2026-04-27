# Phase 9: Dockerization & Packaging - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning
**Mode:** auto (recommended defaults selected; see DISCUSSION-LOG.md for option matrices)

<domain>
## Phase Boundary

Package the entire FinAlly stack — Next.js static export + FastAPI backend
+ SQLite persistence — into a single Docker image, runnable with one
`docker run` command, preserving data across restarts via a named volume.
Ship cross-platform start/stop scripts (`scripts/start_mac.sh`,
`scripts/stop_mac.sh`, `scripts/start_windows.ps1`,
`scripts/stop_windows.ps1`) and a committed `.env.example` so a fresh
clone can run the simulator-mode demo without an API key.

**In scope (OPS-01, OPS-02, OPS-03, OPS-04):**

- Multi-stage `Dockerfile` at the repo root: Stage 1 `node:20-slim` builds
  `frontend/out/`; Stage 2 `python:3.12-slim` installs the `uv`-managed
  backend, copies `frontend/out/` from Stage 1, exposes :8000, runs
  `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `.dockerignore` at repo root excluding `node_modules/`, `.next/`,
  `.venv/`, `__pycache__/`, `.git/`, `.idea/`, `.claude/`, `.planning/`,
  `db/`, `frontend/out/` (rebuilt fresh in stage 1), and any `*.test.*`
  files.
- `.env.example` at repo root listing all three env vars
  (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`) with safe
  placeholder values that boot the simulator-mode demo without edits.
- Four start/stop scripts under `scripts/` that wrap `docker build`,
  `docker run`, and `docker stop` idempotently (safe to re-run).
- One-page `docs/DOCKER.md` (or top of README) explaining the canonical
  invocation, the named volume, and the `.env` workflow.

**Out of scope (later or v2):**

- Cloud deploy (AWS App Runner / Render / Fly.io) — DEPLOY-01, v2.
- Image size optimization beyond multi-stage slim (distroless / Alpine
  experiments) — pragmatic; `python:3.12-slim` is the documented baseline.
- Container orchestration (`docker-compose.yml` for production) —
  PLAN.md §3 explicitly excludes a compose file from the prod path.
- HTTPS / reverse proxy in front of the container — single-user
  localhost demo doesn't need it; cloud deploys add it externally.
- Healthcheck integration with external monitors — see D-08.
- Linux-native start/stop scripts — macOS shell scripts work on Linux
  with no changes; PowerShell covers Windows; no pure-Linux variant
  needed for the capstone scope.

**Carry-over from prior phases:**

- **APP-02 contract (Phase 8):** FastAPI's `StaticFiles` mount points at
  `Path(__file__).resolve().parents[2] / "frontend" / "out"` —
  i.e., from `backend/app/lifespan.py`, two levels up to the repo root,
  then `frontend/out/`. The container layout MUST mirror this (D-01).
- **DB-03 contract (Phase 2):** SQLite file at `db/finally.db` resolved
  via `DB_PATH` env var (defaults to a relative path). The container
  binds `/app/db` to the named volume.
- **APP-03 contract (Phase 1):** `.env` is loaded from the working
  directory upward via `dotenv.load_dotenv()` at startup. Missing
  values do not crash startup. `.env.example` must reflect this
  promise.

</domain>

<decisions>
## Implementation Decisions

### Image Architecture

- **D-01: Repo-mirroring container layout.** The image places source at
  `/app/backend/` and `/app/frontend/out/`, mirroring the dev tree, so
  `Path(__file__).resolve().parents[2] / "frontend" / "out"` resolves
  inside the container without any code change to `lifespan.py`. Working
  directory is `/app/backend` for the uvicorn process. Rejected:
  introducing a `STATIC_DIR` env var and patching `lifespan.py` —
  drags Phase 9 into a Phase 8 contract change for no gain.

- **D-02: Multi-stage `node:20-slim` → `python:3.12-slim`.** Stage 1
  installs frontend deps with `npm ci` (deterministic from
  `package-lock.json`), runs `npm run build` to produce
  `frontend/out/`, and exits. Stage 2 is the runtime image: installs
  `uv` (`pip install --no-cache-dir uv`), copies `backend/`,
  runs `uv sync --frozen --no-dev` (production lock, no test deps),
  copies the `frontend/out/` artifact from Stage 1, sets working dir
  `/app/backend`, exposes `8000`, and CMDs the canonical
  `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`. Rejected:
  distroless or Alpine final stage (numpy/Cholesky from
  `app/market/simulator.py` and the LiteLLM dep tree have known wheels
  on slim-glibc but unstable on musl — capstone scope has no payoff
  for the size win).

- **D-03: `npm ci` (Stage 1) and `uv sync --frozen --no-dev` (Stage 2).**
  Both use lockfiles for determinism and exclude test/lint deps from
  the runtime image. The phase 9 build MUST fail if either lockfile is
  out of date (`npm ci` fails fast; `uv sync --frozen` likewise). This
  also keeps the runtime image lean (no vitest, no pytest, no ruff).

- **D-04: Run as root, single-user demo.** The image does not create
  an `appuser`. The container is single-user, runs on localhost, owns
  only `/app/db` (volume) and `/app/backend` (read-only at runtime).
  Adding a non-root user is a v2 hardening concern (POLISH-01-equivalent
  for ops). Rejected: `useradd appuser && USER appuser` (six extra
  Dockerfile lines, no demo benefit, and running as non-root inside
  a container with a single named volume sometimes hits permissions
  edge cases on Docker Desktop for Mac/Windows that distract from the
  demo).

### Runtime + Persistence

- **D-05: `ENV DB_PATH=/app/db/finally.db` and `VOLUME /app/db`.** The
  Dockerfile declares `/app/db` as a named volume so SQLite persists
  across `docker rm`. The canonical run command pins it to the named
  volume `finally-data`:
  `docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally`.
  This matches PLAN.md §11 verbatim and ROADMAP SC#2.

- **D-06: `.env` is mounted via `--env-file`, not baked into the image.**
  The Dockerfile does NOT `COPY .env .env`. The user's `.env` (or a
  copy of `.env.example`) is read at `docker run` time via
  `--env-file .env`. Rationale: secrets out of image layers,
  `OPENROUTER_API_KEY` rotates without rebuild, image is portable.

- **D-07: No `docker-compose.yml` in production.** PLAN.md §3 calls
  out single-container, single-port, no compose file. The repo MAY
  later carry an optional `docker-compose.yml` for convenience, but
  Phase 9 ships only `Dockerfile` + scripts + `.env.example`.
  `docker-compose.test.yml` for E2E lives in `test/` and is Phase 10
  scope.

- **D-08: No `HEALTHCHECK` in the Dockerfile.** The image is run as a
  single process on localhost; the user's success signal is "the
  browser opens". A `HEALTHCHECK` would either need `curl` (extra apt
  install) or a Python one-liner, both of which add noise without
  changing the demo. The orchestration platform that eventually runs
  this image (App Runner / Render in v2) will provide its own probe.

### Scripts (cross-platform)

- **D-09: Build-on-first-run, cached thereafter; `--build` forces
  rebuild.** `scripts/start_mac.sh` checks for the `finally:latest`
  image tag with `docker image inspect`. If absent or `--build` was
  passed, runs `docker build -t finally .`. Then runs the canonical
  `docker run -d --name finally-app ...` with the named volume and
  port mapping. The Windows PowerShell script mirrors this. Rejected:
  always-rebuild (slow), never-rebuild (drift between source and
  running image).

- **D-10: Idempotent stop.** `scripts/stop_mac.sh` runs
  `docker stop finally-app 2>/dev/null` then `docker rm finally-app
  2>/dev/null`. Both are safe if the container isn't running. The
  named volume `finally-data` is NOT removed — data persists by
  default. A `--purge` flag (deferred idea) would remove the volume.

- **D-11: Scripts open the browser only on success.** macOS uses
  `open http://localhost:8000`; Windows PowerShell uses
  `Start-Process http://localhost:8000`. Both gated on a successful
  `docker run` exit code. Suppress on `--no-open` for CI/headless use.

### Configuration & Documentation

- **D-12: `.env.example` ships with safe defaults that boot the demo.**

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

  Rationale: SC#4 says copying `.env.example` → `.env` must be
  sufficient to run the simulator-mode demo. With all three values
  blank/false, the lifespan boots the simulator (no `MASSIVE_API_KEY`
  → `SimulatorDataSource`), the chat 502s gracefully if the user
  hasn't added a key, and everything else works.

- **D-13: `.dockerignore` is aggressive.** Exclude `node_modules/`,
  `.next/`, `.venv/`, `__pycache__/`, `*.pyc`, `frontend/out/`,
  `.git/`, `.idea/`, `.claude/`, `.planning/`, `db/` (host runtime
  artifacts), `*.test.ts`, `*.test.tsx`, `tests/`, `test/`, `*.md`
  except `README.md`. The build context should be small and
  reproducible — the `.next/` and `frontend/out/` directories
  (already locally rebuilt during dev) must NOT be copied into Stage 1.

- **D-14: README gets a 10-line Quick Start; `docs/DOCKER.md` is the
  long-form reference.** The README change is minimal: a copy-paste
  block with the start script and the URL. `docs/DOCKER.md` covers:
  canonical `docker run`, volume semantics, `.env` workflow,
  troubleshooting (port collision, image not found, volume reset),
  and the Windows PowerShell equivalents.

</decisions>

<canonical_refs>
## Canonical References

These docs are MANDATORY reading for the researcher and planner agents:

- `planning/PLAN.md` §3 (Architecture Overview), §4 (Directory Structure),
  §5 (Environment Variables), §11 (Docker & Deployment) — the spec
  Phase 9 implements.
- `.planning/ROADMAP.md` §"Phase 9: Dockerization & Packaging" — the
  four success criteria and requirement IDs (OPS-01..04).
- `backend/app/lifespan.py` — `StaticFiles(directory=str(static_dir),
  html=True, check_dir=False)` with `static_dir =
  Path(__file__).resolve().parents[2] / "frontend" / "out"`. The
  container layout in D-01 must keep `parents[2]` resolving to a
  parent that contains `frontend/out`.
- `backend/app/main.py` — entry point `app.main:app`; `load_dotenv()`
  runs before app construction.
- `backend/pyproject.toml` — `requires-python = ">=3.12"`, runtime
  vs dev extras split. Used to pick `python:3.12-slim` and
  `uv sync --frozen --no-dev`.
- `frontend/package.json` — `next build` produces `frontend/out/` due
  to `output: 'export'` in `next.config.mjs`.
- `frontend/next.config.mjs` — `output: 'export'`, `trailingSlash: true`,
  `skipTrailingSlashRedirect: true` (Plan 08-01 G1 fix). Stage 1 must
  produce `frontend/out/index.html`.
- `.gitignore` — `db.sqlite3*` and `.env` already ignored. Phase 9
  must NOT add `frontend/out/` to gitignore (the runtime in dev mode
  consumes it via the static mount; only the container-build artifact
  is the in-image copy). It DOES add `db/finally.db` if not already.

</canonical_refs>

<deferred>
## Deferred Ideas

Captured here so they aren't lost; out of Phase 9 scope.

- **`docker-compose.yml` (production convenience).** PLAN.md §3 says
  no compose in production. If users want it, a `docker-compose.yml`
  could ship later as an optional convenience.
- **Non-root container user.** v2 hardening (security pass).
- **Distroless / Alpine final stage.** v2 size optimization.
- **`HEALTHCHECK` clause.** Adds value when the container runs behind
  an orchestrator; not now.
- **`--purge` flag on stop scripts.** Removes the `finally-data`
  volume too; useful for repeat full-reset demos.
- **Cross-arch build (`--platform linux/amd64,linux/arm64`).** When
  the demo moves to a cloud registry; not now.
- **Dockerfile lint via `hadolint` in CI.** Polish; once the
  Dockerfile is stable, add it as a pre-merge check.
- **Cloud deploy recipe (App Runner / Render / Fly.io).** v2 scope
  per DEPLOY-01.

</deferred>

<scope_creep_notes>
## Scope Creep Avoided

- "Should we also add a CI workflow that builds the image?" → New
  capability; deferred to a later infra phase.
- "Should we add image-size budgets?" → Polish; deferred.
- "Should we add structured JSON logging for prod?" → Backend
  observability; not in Phase 9 acceptance.

</scope_creep_notes>

---
*Phase 9 CONTEXT.md gathered in --auto mode 2026-04-26. The 14 decisions
above were auto-selected as the recommended option for each gray area;
see `09-DISCUSSION-LOG.md` for the option matrices the choices came from.*
