# FinAlly — Docker Reference

Long-form reference for the FinAlly Docker image. For the absolute minimum needed
to run the demo, see the **Quick Start** section in the top-level
[`README.md`](../README.md).

## Quickstart

From a fresh clone:

```bash
cp .env.example .env
./scripts/start_mac.sh        # macOS / Linux
# or
./scripts/start_windows.ps1   # Windows PowerShell 5.1+
```

Open <http://localhost:8000>. You start with a 10-ticker watchlist and
$10,000 in simulated cash. To stop the container while preserving your data:

```bash
./scripts/stop_mac.sh         # macOS / Linux
./scripts/stop_windows.ps1    # Windows (run from PowerShell)
```

## Canonical run

The four start/stop scripts wrap this single invocation, taken verbatim from
[`planning/PLAN.md`](../planning/PLAN.md) section 11:

```bash
docker run -d \
  --name finally-app \
  -v finally-data:/app/db \
  -p 8000:8000 \
  --env-file .env \
  finally:latest
```

Build the image first if you have not already:

```bash
docker build -t finally:latest .
```

After the container is running, you can inspect it directly:

```bash
docker logs -f finally-app                                # tail logs
curl -fsS http://localhost:8000/api/health                # health check
docker exec -it finally-app /bin/bash                     # shell inside the container
```

## Image architecture

The Dockerfile is multi-stage:

| Stage | Base image          | Purpose                                                       |
|-------|---------------------|---------------------------------------------------------------|
| 1     | `node:20-slim`      | `npm ci` then `npm run build` produces `frontend/out/`        |
| 2     | `python:3.12-slim`  | Installs `uv`, syncs `backend/uv.lock` (no dev extras), copies the frontend export from Stage 1 |

Inside the final image:

```
/app/
├── backend/        WORKDIR; uvicorn runs here; .venv lives here
│   └── app/
│       ├── lifespan.py   # parents[2] resolves to /app
│       └── main.py
├── frontend/
│   └── out/        # static export served by FastAPI's StaticFiles
└── db/             # named volume mount target (SQLite finally.db)
```

The runtime command is:

```
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Notes:
- `uv` is installed via `COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/`
  (smaller and more reproducible than `pip install uv`).
- The image runs as `root`; this is a single-user localhost demo and the
  named volume avoids the permission edge cases that come with non-root
  ownership of bind-mounted directories on Docker Desktop.
- `STOPSIGNAL SIGINT` is set so `docker stop` triggers uvicorn's graceful
  shutdown directly.
- No `HEALTHCHECK` is declared — orchestration platforms (App Runner,
  Render, Fly.io) provide their own probes.

## Volume

The container declares `VOLUME /app/db` and the canonical run command attaches
the named volume `finally-data`:

```bash
-v finally-data:/app/db
```

`backend/app/lifespan.py` reads `DB_PATH` (set inside the image to
`/app/db/finally.db`) and lazily creates the SQLite file on first request.
The volume persists across `docker stop`, `docker rm`, and image rebuilds.

The stop scripts deliberately do **not** remove the volume:

```bash
./scripts/stop_mac.sh
# Stopped finally-app. Data preserved in volume 'finally-data'.
```

To wipe all data and start fresh:

```bash
./scripts/stop_mac.sh
docker volume rm finally-data
```

This is destructive — it removes your simulated portfolio, trade history,
watchlist edits, and chat history.

## .env workflow

The image is portable: secrets are **not** baked in. The `.env` file is read
at run time via `--env-file .env`. Three keys are documented:

| Variable               | Required?                          | What happens if empty                                                                 |
|------------------------|------------------------------------|---------------------------------------------------------------------------------------|
| `OPENROUTER_API_KEY`   | required for AI chat               | `/api/chat` returns 502; the rest of the terminal works (heatmap, P&L, trades, watchlist) |
| `MASSIVE_API_KEY`      | optional                           | The built-in market simulator runs (recommended for the demo)                          |
| `LLM_MOCK`             | optional (default `false`)         | Real LLM calls go out via OpenRouter; set to `true` for deterministic mock responses    |

Get an OpenRouter API key from <https://openrouter.ai/>. Edit `.env` and
restart the container:

```bash
./scripts/stop_mac.sh
./scripts/start_mac.sh
```

The image is **never** rebuilt to rotate a key — `.env` is read fresh on
every `docker run`.

## Troubleshooting

**Port 8000 already in use.**

```bash
# macOS / Linux
lsof -i :8000

# Windows PowerShell
Get-NetTCPConnection -LocalPort 8000
```

Stop the conflicting process or change the port mapping in
`scripts/start_mac.sh` (`PORT=8000` -> another value, then re-run).

**`Error: .env not found`.**

The start scripts pre-flight-check for `.env`. Copy the example:

```bash
cp .env.example .env
```

**Image not found.**

```bash
./scripts/start_mac.sh --build
```

The `--build` flag forces a rebuild even when an older `finally:latest`
image is cached.

**Browser does not auto-open.**

Either `--no-open` was passed, or the OS browser launcher (`open` on macOS,
`xdg-open` on Linux, `Start-Process` on Windows) is unavailable. Visit
<http://localhost:8000> manually.

**Container starts but `/` returns 404.**

The static export from Stage 1 did not land in `/app/frontend/out/`. Confirm
with:

```bash
docker run --rm finally:latest test -f /app/frontend/out/index.html
```

If this exits non-zero, force a rebuild: `./scripts/start_mac.sh --build`.

**Volume reset (data loss).**

```bash
./scripts/stop_mac.sh
docker volume rm finally-data
./scripts/start_mac.sh
```

This wipes the SQLite database; the lifespan re-seeds the default user,
$10k cash, and the 10 default watchlist tickers on the next request.

## Windows

Every command above has a PowerShell 5.1+ equivalent:

| macOS / Linux                          | Windows PowerShell                          |
|----------------------------------------|---------------------------------------------|
| `cp .env.example .env`                 | `Copy-Item .env.example .env`               |
| `./scripts/start_mac.sh`               | `.\scripts\start_windows.ps1`               |
| `./scripts/start_mac.sh --build`       | `.\scripts\start_windows.ps1 -Build`        |
| `./scripts/start_mac.sh --no-open`     | `.\scripts\start_windows.ps1 -NoOpen`       |
| `./scripts/stop_mac.sh`                | `.\scripts\stop_windows.ps1`                |
| `lsof -i :8000`                        | `Get-NetTCPConnection -LocalPort 8000`      |
| `docker logs -f finally-app`           | `docker logs -f finally-app`                |
| `docker volume rm finally-data`        | `docker volume rm finally-data`             |

The PowerShell scripts target PowerShell 5.1 (Windows default) and 7.x. They
require Docker Desktop for Windows with WSL2 enabled (the standard install).
