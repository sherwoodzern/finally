"""Integration tests for POST /api/portfolio/trade (PORT-02, PORT-03)."""

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
class TestBuy:
    """Happy-path BUY contract."""

    async def test_buy_happy_path(self, db_path):
        """POST buy AAPL x1 returns 200 with TradeResponse; GET /api/portfolio reflects it."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1.0},
                    )
                    assert resp.status_code == 200, resp.text
                    body = resp.json()
                    assert body["ticker"] == "AAPL"
                    assert body["side"] == "buy"
                    assert body["quantity"] == 1.0
                    assert body["price"] > 0
                    assert body["executed_at"]
                    assert body["cash_balance"] < 10000.0
                    assert body["position_quantity"] == 1.0

                    # Portfolio reflects the new position.
                    p = await client.get("/api/portfolio")
                    tickers = {pos["ticker"] for pos in p.json()["positions"]}
                    assert "AAPL" in tickers

    async def test_buy_fractional(self, db_path):
        """Fractional quantity (0.5) is accepted."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 0.5},
                    )
                    assert resp.status_code == 200, resp.text
                    assert resp.json()["quantity"] == 0.5


@pytest.mark.asyncio
class TestSell:
    """SELL behavior: avg_cost preservation + full-sell row delete."""

    async def test_partial_sell_keeps_avg_cost(self, db_path):
        """After BUY 2 then SELL 1, position_avg_cost equals the buy's avg_cost (D-16)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    buy = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 2.0},
                    )
                    assert buy.status_code == 200, buy.text
                    buy_avg_cost = buy.json()["position_avg_cost"]

                    sell = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "sell", "quantity": 1.0},
                    )
                    assert sell.status_code == 200, sell.text
                    body = sell.json()
                    assert body["position_quantity"] == 1.0
                    assert body["position_avg_cost"] == buy_avg_cost

    async def test_full_sell_deletes_row(self, db_path):
        """BUY 1 then SELL 1 zeros the position; the row is deleted (D-15)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    b = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1.0},
                    )
                    assert b.status_code == 200, b.text

                    s = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "sell", "quantity": 1.0},
                    )
                    assert s.status_code == 200, s.text
                    assert s.json()["position_quantity"] == 0.0

                    p = await client.get("/api/portfolio")
                    tickers = {pos["ticker"] for pos in p.json()["positions"]}
                    assert "AAPL" not in tickers


@pytest.mark.asyncio
class TestErrors:
    """400 errors for the four domain exceptions; DB state unchanged."""

    async def test_insufficient_cash(self, db_path):
        """Buying more than 10k of cash worth yields 400 insufficient_cash."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    before = (await client.get("/api/portfolio")).json()

                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1_000_000.0},
                    )
                    assert resp.status_code == 400
                    detail = resp.json()["detail"]
                    assert detail["error"] == "insufficient_cash"
                    assert detail["message"]

                    after = (await client.get("/api/portfolio")).json()
                    assert after["cash_balance"] == before["cash_balance"]
                    assert after["positions"] == before["positions"]

    async def test_insufficient_shares(self, db_path):
        """Selling without holding any yields 400 insufficient_shares."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    before = (await client.get("/api/portfolio")).json()

                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "sell", "quantity": 1.0},
                    )
                    assert resp.status_code == 400
                    assert resp.json()["detail"]["error"] == "insufficient_shares"

                    after = (await client.get("/api/portfolio")).json()
                    assert after["cash_balance"] == before["cash_balance"]

    async def test_unknown_ticker(self, db_path):
        """A ticker not in the watchlist yields 400 unknown_ticker."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    before = (await client.get("/api/portfolio")).json()

                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "ZZZ", "side": "buy", "quantity": 1.0},
                    )
                    assert resp.status_code == 400
                    assert resp.json()["detail"]["error"] == "unknown_ticker"

                    after = (await client.get("/api/portfolio")).json()
                    assert after["cash_balance"] == before["cash_balance"]

    async def test_price_unavailable(self, db_path):
        """Evict AAPL from cache then POST buy AAPL -> 400 price_unavailable."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    app.state.price_cache.remove("AAPL")
                    before = (await client.get("/api/portfolio")).json()

                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1.0},
                    )
                    assert resp.status_code == 400
                    assert resp.json()["detail"]["error"] == "price_unavailable"

                    after = (await client.get("/api/portfolio")).json()
                    assert after["cash_balance"] == before["cash_balance"]


@pytest.mark.asyncio
class TestSchema:
    """Pydantic 422 rejections for malformed bodies."""

    async def test_rejects_malformed_body(self, db_path):
        """Bad enum, non-positive quantity, and extra keys all return 422."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    bad_side = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "hold", "quantity": 1.0},
                    )
                    assert bad_side.status_code == 422

                    bad_qty = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 0},
                    )
                    assert bad_qty.status_code == 422

                    extra_key = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1, "extra": "x"},
                    )
                    assert extra_key.status_code == 422
