"""Integration tests for DELETE /api/watchlist/{ticker} (WATCH-03 + SC#4).

Module-scoped lifespan fixture; native lifespan mount; no shim.
"""

from __future__ import annotations

import datetime
import logging
import os
import uuid
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
    db_path = tmp_path_factory.mktemp("watchlist_delete") / "finally.db"
    app = FastAPI(lifespan=lifespan)
    with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
        async with LifespanManager(app):
            yield app


@pytest_asyncio.fixture(loop_scope="module")
async def client(app_with_lifespan: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app_with_lifespan)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _row_count(db, user_id: str = "default") -> int:
    return db.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


def _reinsert_if_missing(db, ticker: str, user_id: str = "default") -> None:
    """Restore a default ticker row after destructive tests so other tests see it."""
    existing = db.execute(
        "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    ).fetchone()
    if existing is None:
        db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                ticker,
                datetime.datetime.now(datetime.UTC).isoformat(),
            ),
        )
        db.commit()


class TestDeleteWatchlist:
    async def test_delete_existing_returns_removed(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        app = app_with_lifespan
        _reinsert_if_missing(app.state.db, "AAPL")
        before = _row_count(app.state.db)
        try:
            resp = await client.delete("/api/watchlist/AAPL")
            assert resp.status_code == 200, resp.text
            assert resp.json() == {"ticker": "AAPL", "status": "removed"}
            assert _row_count(app.state.db) == before - 1
            assert "AAPL" not in app.state.market_source.get_tickers()
            # simulator.remove_ticker cascades to cache (app/market/simulator.py:256)
            assert app.state.price_cache.get("AAPL") is None
        finally:
            # Restore AAPL for subsequent tests in this module.
            _reinsert_if_missing(app.state.db, "AAPL")
            try:
                await app.state.market_source.add_ticker("AAPL")
            except Exception:
                pass

    async def test_delete_normalizes_path_param(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """DELETE /api/watchlist/aapl -> normalized to AAPL, status=removed."""
        app = app_with_lifespan
        _reinsert_if_missing(app.state.db, "AAPL")
        try:
            resp = await client.delete("/api/watchlist/aapl")
            assert resp.status_code == 200, resp.text
            assert resp.json()["ticker"] == "AAPL"
            assert resp.json()["status"] == "removed"
        finally:
            _reinsert_if_missing(app.state.db, "AAPL")
            try:
                await app.state.market_source.add_ticker("AAPL")
            except Exception:
                pass

    async def test_missing_ticker_returns_not_present_not_404(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """SC#4: DELETE /api/watchlist/ZZZZ -> 200 status='not_present'."""
        app = app_with_lifespan
        before = _row_count(app.state.db)
        resp = await client.delete("/api/watchlist/ZZZZ")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ticker": "ZZZZ", "status": "not_present"}
        assert _row_count(app.state.db) == before

    async def test_source_failure_after_commit_returns_200(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI, caplog
    ):
        """D-11: DB wins for remove too. Post-commit source failure -> WARNING, 200 removed."""
        app = app_with_lifespan
        _reinsert_if_missing(app.state.db, "AAPL")
        original_remove = app.state.market_source.remove_ticker

        async def _boom(ticker: str) -> None:
            raise RuntimeError("source exploded")

        app.state.market_source.remove_ticker = _boom  # type: ignore[assignment]
        try:
            with caplog.at_level(logging.WARNING):
                resp = await client.delete("/api/watchlist/AAPL")
            assert resp.status_code == 200, resp.text
            assert resp.json() == {"ticker": "AAPL", "status": "removed"}
            assert any(
                "source.remove_ticker(AAPL) raised" in rec.message
                for rec in caplog.records
            )
        finally:
            app.state.market_source.remove_ticker = original_remove  # type: ignore[assignment]
            _reinsert_if_missing(app.state.db, "AAPL")
            try:
                await app.state.market_source.add_ticker("AAPL")
            except Exception:
                pass


class TestDeletePathValidation:
    @pytest.mark.parametrize(
        "bad_path",
        [
            pytest.param("1X", id="leading_digit"),
            pytest.param("AAPL!", id="special_char"),
            pytest.param("ABCDEFGHIJK", id="over_10_chars"),
        ],
    )
    async def test_bad_path_returns_422(
        self, client: httpx.AsyncClient, bad_path
    ):
        resp = await client.delete(f"/api/watchlist/{bad_path}")
        assert resp.status_code == 422, (bad_path, resp.text)
