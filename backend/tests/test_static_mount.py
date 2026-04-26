"""APP-02: assert StaticFiles mount at / is registered AFTER all /api/* routers and serves index.html when present."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from starlette.routing import Mount

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


@pytest.mark.asyncio
class TestStaticMount:
    async def test_static_mount_registered_at_root(self, db_path: Path) -> None:
        """The StaticFiles mount appears as a Mount route with path '/'."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                # Starlette internally normalizes '/' mount path to '' for matching
                paths = [getattr(r, "path", None) for r in app.router.routes]
                assert "" in paths or "/" in paths, paths

    async def test_mount_registered_after_api_routers(self, db_path: Path) -> None:
        """Catch-all StaticFiles must appear AFTER every /api/* route in registration order (D-14)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                routes = list(app.router.routes)
                api_indices = [
                    i
                    for i, r in enumerate(routes)
                    if getattr(r, "path", "").startswith("/api")
                ]
                mount_indices = [
                    i
                    for i, r in enumerate(routes)
                    if isinstance(r, Mount) and getattr(r, "path", None) in ("", "/")
                ]
                assert api_indices, "No /api/* routes registered"
                assert mount_indices, "No StaticFiles mount registered"
                assert min(mount_indices) > max(api_indices), (
                    f"Mount at index {mount_indices} must come after all /api routes at {api_indices}"
                )

    async def test_index_html_served_at_root(self, db_path: Path) -> None:
        """GET / returns the Next.js index.html when frontend/out/index.html exists."""
        repo_root = Path(__file__).resolve().parents[2]
        index_path = repo_root / "frontend" / "out" / "index.html"
        if not index_path.exists():
            pytest.skip("frontend/out/index.html missing - run `npm run build` first")
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                    res = await c.get("/")
                    assert res.status_code == 200, res.text
                    assert "text/html" in res.headers.get("content-type", "")

    async def test_api_health_still_resolves_after_mount(self, db_path: Path) -> None:
        """The catch-all StaticFiles does NOT shadow /api/health (route precedence)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
                    res = await c.get("/api/health")
                    assert res.status_code == 200
                    assert res.json() == {"status": "ok"}
