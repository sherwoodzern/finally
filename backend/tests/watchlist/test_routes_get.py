"""Integration tests for GET /api/watchlist (WATCH-01).

One LifespanManager per MODULE (not per test) - see checker note on runtime budget.
The watchlist router is mounted natively by app.lifespan.lifespan (Plan 04-02 Task 2),
so no shim is needed.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def event_loop_policy():
    """Module-scoped override so module-scoped async fixtures can share a loop."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def app_with_lifespan(tmp_path_factory) -> AsyncIterator[FastAPI]:
    """Enter the lifespan once per module. Yields a live app with /api/watchlist mounted."""
    db_path = tmp_path_factory.mktemp("watchlist_get") / "finally.db"
    app = FastAPI(lifespan=lifespan)
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            yield app


@pytest_asyncio.fixture(loop_scope="module")
async def client(app_with_lifespan: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app_with_lifespan)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestGetWatchlist:
    """HTTP contract for GET /api/watchlist."""

    async def test_returns_ten_seeded_tickers_with_prices(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        resp = await client.get("/api/watchlist")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "items" in body
        tickers = [it["ticker"] for it in body["items"]]
        expected = sorted(
            ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
             "NVDA", "META", "JPM", "V", "NFLX"]
        )
        assert sorted(tickers) == expected
        aapl = next(it for it in body["items"] if it["ticker"] == "AAPL")
        # Simulator seeds the cache on lifespan start.
        assert aapl["price"] is not None
        assert aapl["direction"] in ("up", "down", "flat")

    async def test_cold_cache_ticker_returns_none_fields(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """Evicting a cached ticker causes GET to return None price fields (D-05)."""
        # Stash the current AAPL snapshot so we can restore it for other tests.
        cache = app_with_lifespan.state.price_cache
        saved = cache.get("AAPL")
        try:
            cache.remove("AAPL")
            resp = await client.get("/api/watchlist")
            assert resp.status_code == 200
            body = resp.json()
            aapl = next(it for it in body["items"] if it["ticker"] == "AAPL")
            assert aapl["price"] is None
            assert aapl["previous_price"] is None
            assert aapl["change_percent"] is None
            assert aapl["direction"] is None
            assert aapl["timestamp"] is None
            assert aapl["added_at"]  # still populated from DB
        finally:
            # Restore so subsequent tests in this module see a warm cache.
            if saved is not None:
                cache.update(ticker="AAPL", price=saved.price)

    async def test_response_items_order_added_at_then_ticker(
        self, client: httpx.AsyncClient
    ):
        """D-08: ORDER BY added_at ASC, ticker ASC."""
        resp = await client.get("/api/watchlist")
        body = resp.json()
        # All seed rows share the same added_at, so order is ticker-ASC among the defaults.
        tickers = [it["ticker"] for it in body["items"]]
        assert tickers == sorted(tickers)
