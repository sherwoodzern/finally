"""Integration tests for GET /api/portfolio (PORT-01)."""

from __future__ import annotations

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
class TestGetPortfolio:
    """HTTP contract for GET /api/portfolio."""

    async def test_returns_seeded_cash_balance_and_empty_positions(self, db_path):
        """Fresh DB -> cash_balance=10000.0, total_value=10000.0, positions=[]."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/portfolio")
                    assert resp.status_code == 200
                    body = resp.json()
                    assert body["cash_balance"] == 10000.0
                    assert body["total_value"] == 10000.0
                    assert body["positions"] == []

    async def test_current_price_falls_back_to_avg_cost_when_cache_empty(self, db_path):
        """After a BUY, remove the ticker from the cache and assert the GET response
        falls back to avg_cost for current_price and reports unrealized_pnl == 0."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    buy = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1.0},
                    )
                    assert buy.status_code == 200, buy.text
                    avg_cost = buy.json()["position_avg_cost"]

                    # Evict the ticker so get_portfolio falls back to avg_cost.
                    app.state.price_cache.remove("AAPL")

                    resp = await client.get("/api/portfolio")
                    assert resp.status_code == 200
                    body = resp.json()
                    aapl = next(p for p in body["positions"] if p["ticker"] == "AAPL")
                    assert aapl["current_price"] == avg_cost
                    assert aapl["unrealized_pnl"] == 0.0

    async def test_positions_ordered_by_ticker_asc(self, db_path):
        """Positions list is ordered by ticker ASC (see get_portfolio SQL)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    for ticker in ("MSFT", "AAPL", "GOOGL"):
                        r = await client.post(
                            "/api/portfolio/trade",
                            json={"ticker": ticker, "side": "buy", "quantity": 1.0},
                        )
                        assert r.status_code == 200, r.text

                    resp = await client.get("/api/portfolio")
                    assert resp.status_code == 200
                    tickers = [p["ticker"] for p in resp.json()["positions"]]
                    assert tickers == sorted(tickers)
                    assert set(tickers) == {"AAPL", "GOOGL", "MSFT"}
