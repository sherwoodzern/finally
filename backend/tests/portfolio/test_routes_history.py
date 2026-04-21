"""Integration tests for GET /api/portfolio/history (PORT-04)."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)


@pytest.mark.asyncio
class TestGetHistory:
    """HTTP contract for GET /api/portfolio/history."""

    async def test_empty_history_on_fresh_db(self, db_path):
        """Lifespan registers the observer with last_snapshot_at=0.0, so the first
        tick deterministically writes one boot-time snapshot (assumption A2)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                # Wait for the first simulator tick to fire the observer.
                await asyncio.sleep(0.7)
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/portfolio/history")
                    assert resp.status_code == 200
                    body = resp.json()
                    assert len(body["snapshots"]) == 1
                    assert body["snapshots"][0]["total_value"] == 10000.0

    async def test_snapshots_ordered_asc(self, db_path):
        """Two successful trades produce monotonically non-decreasing recorded_at."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    for ticker in ("AAPL", "GOOGL"):
                        r = await client.post(
                            "/api/portfolio/trade",
                            json={"ticker": ticker, "side": "buy", "quantity": 1.0},
                        )
                        assert r.status_code == 200, r.text

                    resp = await client.get("/api/portfolio/history")
                    assert resp.status_code == 200
                    recorded = [s["recorded_at"] for s in resp.json()["snapshots"]]
                    assert recorded == sorted(recorded)
                    assert len(recorded) >= 2

    async def test_limit_param(self, db_path):
        """?limit=2 returns the two EARLIEST snapshots (ORDER BY ASC + LIMIT)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    for ticker in ("AAPL", "GOOGL", "MSFT"):
                        r = await client.post(
                            "/api/portfolio/trade",
                            json={"ticker": ticker, "side": "buy", "quantity": 1.0},
                        )
                        assert r.status_code == 200, r.text

                    full = (await client.get("/api/portfolio/history")).json()["snapshots"]
                    limited = (await client.get("/api/portfolio/history?limit=2")).json()["snapshots"]
                    assert len(limited) == 2
                    assert limited == full[:2]
