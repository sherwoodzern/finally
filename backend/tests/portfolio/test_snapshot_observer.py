"""Tests for make_snapshot_observer + lifespan observer registration (PORT-05)."""

from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
import types
from datetime import UTC, datetime
from unittest.mock import patch

import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.db import init_database, seed_defaults
from app.lifespan import lifespan
from app.market import PriceCache
from app.market.seed_prices import SEED_PRICES
from app.portfolio import make_snapshot_observer


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    seed_defaults(conn)
    return conn


def _warmed_cache() -> PriceCache:
    cache = PriceCache()
    for ticker, price in SEED_PRICES.items():
        cache.update(ticker=ticker, price=price)
    return cache


def _make_state(conn, cache, last_snapshot_at: float = 0.0):
    return types.SimpleNamespace(
        db=conn, price_cache=cache, last_snapshot_at=last_snapshot_at,
    )


def _count_snapshots(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM portfolio_snapshots").fetchone()[0]


def _build_app() -> FastAPI:
    return FastAPI(lifespan=lifespan)


class TestSnapshotObserver:
    """60s cadence, trade-reset clock, and observer exception isolation."""

    def test_60s_threshold_writes_snapshot(self):
        """last_snapshot_at=0.0, monotonic=61.0 -> one snapshot written and clock advanced."""
        conn = _fresh_conn()
        try:
            cache = _warmed_cache()
            state = _make_state(conn, cache, last_snapshot_at=0.0)
            observer = make_snapshot_observer(state)

            before = _count_snapshots(conn)
            with patch("app.portfolio.service.time.monotonic", return_value=61.0):
                observer()
            assert _count_snapshots(conn) == before + 1
            assert state.last_snapshot_at == 61.0
        finally:
            conn.close()

    def test_noop_under_threshold(self):
        """delta < 60 -> no write, clock unchanged."""
        conn = _fresh_conn()
        try:
            cache = _warmed_cache()
            state = _make_state(conn, cache, last_snapshot_at=100.0)
            observer = make_snapshot_observer(state)

            before = _count_snapshots(conn)
            with patch("app.portfolio.service.time.monotonic", return_value=150.0):
                observer()
            assert _count_snapshots(conn) == before
            assert state.last_snapshot_at == 100.0
        finally:
            conn.close()

    def test_boot_time_initial_snapshot(self):
        """last_snapshot_at=0.0, monotonic=0.5 -> boot snapshot fires (assumption A2)."""
        conn = _fresh_conn()
        try:
            cache = _warmed_cache()
            state = _make_state(conn, cache, last_snapshot_at=0.0)
            observer = make_snapshot_observer(state)

            before = _count_snapshots(conn)
            with patch("app.portfolio.service.time.monotonic", return_value=0.5):
                observer()
            assert _count_snapshots(conn) == before + 1
        finally:
            conn.close()

    def test_writes_recorded_at_iso_utc_string(self):
        """The snapshot row's recorded_at parses as a UTC ISO string (Pitfall 6)."""
        conn = _fresh_conn()
        try:
            cache = _warmed_cache()
            state = _make_state(conn, cache, last_snapshot_at=0.0)
            observer = make_snapshot_observer(state)

            with patch("app.portfolio.service.time.monotonic", return_value=61.0):
                observer()

            row = conn.execute(
                "SELECT recorded_at FROM portfolio_snapshots ORDER BY recorded_at DESC LIMIT 1"
            ).fetchone()
            assert row is not None
            parsed = datetime.fromisoformat(row["recorded_at"])
            assert parsed.tzinfo is not None
            assert parsed.utcoffset() == UTC.utcoffset(None)
        finally:
            conn.close()

    @pytest.mark.asyncio
    async def test_trade_resets_clock(self, db_path):
        """A successful POST /api/portfolio/trade advances last_snapshot_at to a
        recent time.monotonic() value (D-07 route-level reset)."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    before = time.monotonic()
                    resp = await client.post(
                        "/api/portfolio/trade",
                        json={"ticker": "AAPL", "side": "buy", "quantity": 1.0},
                    )
                    after = time.monotonic()
                    assert resp.status_code == 200, resp.text
                    # Route handler reset the clock to a monotonic value within
                    # the [before, after] window bounding the request.
                    assert before <= app.state.last_snapshot_at <= after

    @pytest.mark.asyncio
    async def test_raising_observer_does_not_kill_tick_loop(self, db_path, caplog):
        """A raising observer is logged and swallowed; subsequent observers still fire
        and the simulator loop continues (D-08)."""
        app = _build_app()
        caplog.set_level(logging.ERROR, logger="app.market.simulator")
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                called = {"flag": False}

                def raiser() -> None:
                    raise RuntimeError("boom")

                def flag_setter() -> None:
                    called["flag"] = True

                source = app.state.market_source
                source.register_tick_observer(raiser)
                source.register_tick_observer(flag_setter)

                # Wait for at least one tick after registration.
                await asyncio.sleep(0.7)

                assert called["flag"] is True
                task = getattr(source, "_task", None)
                assert task is not None and not task.done()
                assert any("boom" in (rec.exc_text or "") for rec in caplog.records)
