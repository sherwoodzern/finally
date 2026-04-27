# syntax=docker/dockerfile:1
# FinAlly multi-stage build (Phase 9 / OPS-01, OPS-02).
# Stage 1: node:20-slim runs `next build` (output: 'export') -> frontend/out/.
# Stage 2: python:3.12-slim hosts FastAPI via uv; ships frontend/out + backend.
# CONTEXT.md: D-01 (repo-mirror layout), D-02 (slim bases), D-03 (lockfiles),
# D-04 (root user), D-05 (DB_PATH + VOLUME), D-06 (no .env in image),
# D-08 (no HEALTHCHECK).

############################
# Stage 1 — frontend builder
############################
FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

# Layer cache: lockfile-only copy first; npm ci is invalidated only by lockfile drift.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source after deps so dep layer is reusable across source edits.
COPY frontend/ ./

# next build with `output: 'export'` produces /app/frontend/out/index.html.
RUN npm run build

############################
# Stage 2 — backend runtime
############################
FROM python:3.12-slim AS runtime

# Install uv from official distroless image (smaller, reproducible, SHA-pinnable).
# RESEARCH §"Standard Stack" recommends this over `pip install uv` per astral.sh docs.
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# WORKDIR /app/backend so app.lifespan's `parents[2]` resolves to /app and
# StaticFiles finds /app/frontend/out (D-01).
WORKDIR /app/backend

# Layer cache: dep-only sync first.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy backend source; install the project itself.
COPY backend/ ./
RUN uv sync --frozen --no-dev

# Bring the prebuilt frontend artifact in last (cheap layer; rare invalidation).
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

# Runtime configuration.
# DB_PATH overrides the relative default (db/finally.db) so SQLite lands in the
# named volume mount at /app/db (D-05).
ENV DB_PATH=/app/db/finally.db
ENV PYTHONUNBUFFERED=1

# Volume mount target. Named volume `finally-data` attaches here at run time.
VOLUME /app/db

EXPOSE 8000

# Send SIGINT on `docker stop` so uvicorn shuts down cleanly through `uv run`.
STOPSIGNAL SIGINT

# Exec form (JSON array): no /bin/sh wrapper; signals reach the process tree.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
