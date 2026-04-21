"""Integration tests for POST /api/watchlist (WATCH-02 + SC#4).

Module-scoped lifespan fixture keeps per-file SimulatorDataSource starts to exactly 1.
The watchlist router is mounted natively by the lifespan - no shim.
"""

from __future__ import annotations

import logging
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
    db_path = tmp_path_factory.mktemp("watchlist_post") / "finally.db"
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


def _ensure_absent(db, ticker: str, user_id: str = "default") -> None:
    db.execute(
        "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
    )
    db.commit()


class TestPostWatchlist:
    async def test_add_new_ticker_returns_added_and_source_tracks_it(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """POST PYPL -> 200 + status='added'; simulator source now tracks PYPL."""
        app = app_with_lifespan
        _ensure_absent(app.state.db, "PYPL")
        before = _row_count(app.state.db)
        try:
            resp = await client.post("/api/watchlist", json={"ticker": "PYPL"})
            assert resp.status_code == 200, resp.text
            assert resp.json() == {"ticker": "PYPL", "status": "added"}
            assert _row_count(app.state.db) == before + 1
            assert "PYPL" in app.state.market_source.get_tickers()
        finally:
            _ensure_absent(app.state.db, "PYPL")
            # Best-effort source cleanup; idempotent on both implementations.
            try:
                await app.state.market_source.remove_ticker("PYPL")
            except Exception:
                pass

    async def test_add_normalizes_lowercase(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """POST 'pypl' -> stored as 'PYPL' via before-mode validator."""
        app = app_with_lifespan
        _ensure_absent(app.state.db, "PYPL")
        try:
            resp = await client.post("/api/watchlist", json={"ticker": "  pypl  "})
            assert resp.status_code == 200, resp.text
            assert resp.json()["ticker"] == "PYPL"
        finally:
            _ensure_absent(app.state.db, "PYPL")
            try:
                await app.state.market_source.remove_ticker("PYPL")
            except Exception:
                pass

    async def test_duplicate_returns_exists_not_409(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """POST AAPL on seeded DB -> 200 status='exists'. SC#4: NOT 409, NOT 500."""
        app = app_with_lifespan
        before = _row_count(app.state.db)
        resp = await client.post("/api/watchlist", json={"ticker": "AAPL"})
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"ticker": "AAPL", "status": "exists"}
        assert _row_count(app.state.db) == before

    async def test_add_warms_cache_via_simulator(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """Simulator seeds the cache on add_ticker (app/market/simulator.py:247-250)."""
        app = app_with_lifespan
        _ensure_absent(app.state.db, "PYPL")
        try:
            await client.post("/api/watchlist", json={"ticker": "PYPL"})
            assert app.state.price_cache.get("PYPL") is not None
        finally:
            _ensure_absent(app.state.db, "PYPL")
            try:
                await app.state.market_source.remove_ticker("PYPL")
            except Exception:
                pass

    async def test_source_failure_after_commit_returns_200_and_logs_warning(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI, caplog
    ):
        """D-11: DB wins. Post-commit source failure -> WARNING log, still 200 added."""
        app = app_with_lifespan
        _ensure_absent(app.state.db, "PYPL")
        before = _row_count(app.state.db, "default")
        original_add = app.state.market_source.add_ticker

        async def _boom(ticker: str) -> None:
            raise RuntimeError("source exploded")

        app.state.market_source.add_ticker = _boom  # type: ignore[assignment]
        try:
            with caplog.at_level(logging.WARNING):
                resp = await client.post(
                    "/api/watchlist", json={"ticker": "PYPL"}
                )
            assert resp.status_code == 200, resp.text
            assert resp.json() == {"ticker": "PYPL", "status": "added"}
            assert _row_count(app.state.db, "default") == before + 1
            assert any(
                "source.add_ticker(PYPL) raised" in rec.message
                for rec in caplog.records
            )
        finally:
            app.state.market_source.add_ticker = original_add  # type: ignore[assignment]
            _ensure_absent(app.state.db, "PYPL")


class TestPostValidation:
    @pytest.mark.parametrize(
        "body",
        [
            pytest.param({}, id="missing_ticker"),
            pytest.param({"ticker": ""}, id="empty_string"),
            pytest.param({"ticker": "1X"}, id="leading_digit"),
            pytest.param({"ticker": "ABCDEFGHIJK"}, id="over_10_chars"),
            pytest.param({"ticker": "AAPL!"}, id="special_char"),
            pytest.param({"ticker": "AAPL", "extra": "x"}, id="extra_key_forbidden"),
        ],
    )
    async def test_rejects_malformed_body(
        self, client: httpx.AsyncClient, body
    ):
        resp = await client.post("/api/watchlist", json=body)
        assert resp.status_code == 422, (body, resp.text)
