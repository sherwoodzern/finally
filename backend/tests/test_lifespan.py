"""Async lifecycle tests for the FastAPI app shell lifespan."""

import logging
import os
from unittest.mock import patch

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan
from app.market import MarketDataSource, PriceCache
from app.market.seed_prices import SEED_PRICES
from app.market.simulator import SimulatorDataSource


def _build_app() -> FastAPI:
    """Build a fresh FastAPI app bound to the production lifespan.

    A fresh app per test ensures no state bleeds between cases (PriceCache,
    market source, included routers all live on app.state / app.router).
    """
    return FastAPI(lifespan=lifespan)


@pytest.mark.asyncio
class TestLifespan:
    """The lifespan wires PriceCache + market source + SSE router on entry,
    and cleanly stops the source on exit."""

    async def test_attaches_price_cache_to_app_state(self, db_path):
        """Entering the lifespan attaches a PriceCache to app.state.price_cache."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                assert isinstance(app.state.price_cache, PriceCache)

    async def test_attaches_market_source_to_app_state(self, db_path):
        """Entering the lifespan attaches a started MarketDataSource to app.state."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                assert isinstance(app.state.market_source, MarketDataSource)
                assert set(app.state.market_source.get_tickers()) == set(SEED_PRICES)

    async def test_uses_simulator_when_massive_api_key_absent(self, db_path):
        """With no MASSIVE_API_KEY, the factory selects SimulatorDataSource."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                assert isinstance(app.state.market_source, SimulatorDataSource)

    async def test_seeds_cache_immediately_on_startup(self, db_path):
        """All SEED_PRICES tickers are present in the cache before any test code runs.

        This is the contract that makes /api/stream/prices have data on first connect
        (mirrors backend/tests/market/test_simulator_source.py::test_start_populates_cache).
        """
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                cache: PriceCache = app.state.price_cache
                for ticker in SEED_PRICES:
                    assert cache.get(ticker) is not None, ticker

    async def test_includes_sse_router_during_startup(self, db_path):
        """app.include_router(create_stream_router(cache)) ran in lifespan startup,
        so /api/stream/prices is registered on the app while the lifespan is active."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                paths = {getattr(r, "path", None) for r in app.router.routes}
                assert "/api/stream/prices" in paths, paths

    async def test_missing_openrouter_key_logs_warning_and_proceeds(self, caplog, db_path):
        """Missing OPENROUTER_API_KEY does not raise - only a single warning is logged.

        Implements CONTEXT.md missing-env policy: Phase 5 will fail loud when chat is
        hit; Phase 1 startup must not block on a key it does not yet use.
        """
        caplog.set_level(logging.WARNING, logger="app.lifespan")
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                pass
        messages = [rec.message for rec in caplog.records]
        assert any("OPENROUTER_API_KEY" in m for m in messages), messages

    async def test_stops_source_on_shutdown(self, db_path):
        """Exiting the lifespan awaits source.stop() - background task is no longer running."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                source = app.state.market_source
            # After exit, the simulator's _task is None or done (mirrors
            # SimulatorDataSource.stop semantics in backend/app/market/simulator.py:231-240).
            task = getattr(source, "_task", None)
            assert task is None or task.done()

    async def test_attaches_db_to_app_state(self, db_path):
        """lifespan attaches a seeded sqlite3.Connection to app.state.db."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                conn = app.state.db
                row = conn.execute(
                    "SELECT cash_balance FROM users_profile WHERE id = 'default'"
                ).fetchone()
                assert row is not None
                assert row["cash_balance"] == 10000.0

    async def test_tickers_come_from_db_watchlist(self, db_path):
        """source.start(tickers) is driven by the DB watchlist, not SEED_PRICES directly (D-05).

        On a fresh DB the seed produces exactly set(SEED_PRICES.keys()), so the
        ticker set must equal SEED_PRICES - this is a *derived* equivalence via
        the DB, not a direct import from seed_prices.
        """
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                tickers = set(app.state.market_source.get_tickers())
                # Count-only sanity: 10 tickers seeded.
                assert len(tickers) == 10
                assert tickers == set(SEED_PRICES)

    async def test_second_startup_is_no_op(self, db_path):
        """Restarting the lifespan against the same DB_PATH adds no duplicate rows (DB-03)."""
        app1 = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app1):
                pass

        app2 = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app2):
                conn = app2.state.db
                user_count = conn.execute(
                    "SELECT COUNT(*) FROM users_profile"
                ).fetchone()[0]
                wl_count = conn.execute(
                    "SELECT COUNT(*) FROM watchlist"
                ).fetchone()[0]
                assert user_count == 1
                assert wl_count == 10

    async def test_attaches_last_snapshot_at_to_app_state(self, db_path):
        """Phase 3 D-06: startup initialises app.state.last_snapshot_at to 0.0.

        The boot-time observer may advance it on the first tick, so assert the
        value is set to 0.0 BEFORE the first tick fires (i.e. the attribute
        exists with the correct initial value at registration time). We check
        the attribute exists and that it was 0.0 or has since advanced to a
        non-negative float.
        """
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                assert hasattr(app.state, "last_snapshot_at")
                assert isinstance(app.state.last_snapshot_at, float)
                assert app.state.last_snapshot_at >= 0.0

    async def test_includes_portfolio_router_during_startup(self, db_path):
        """app.include_router(create_portfolio_router(conn, cache)) runs in lifespan."""
        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                paths = {getattr(r, "path", None) for r in app.router.routes}
                assert "/api/portfolio" in paths, paths
                assert "/api/portfolio/trade" in paths, paths
                assert "/api/portfolio/history" in paths, paths

    async def test_registers_snapshot_observer_on_market_source(self, db_path):
        """Phase 3 D-05: source.register_tick_observer(make_snapshot_observer(app.state))
        runs in startup, and the boot-time first tick advances last_snapshot_at > 0.0."""
        import asyncio

        app = _build_app()
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            async with LifespanManager(app):
                observers = getattr(app.state.market_source, "_observers", None)
                assert observers is not None, "SimulatorDataSource must expose _observers"
                assert len(observers) >= 1
                # After the next tick, last_snapshot_at advances from 0.0 (boot snapshot).
                await asyncio.sleep(0.7)
                assert app.state.last_snapshot_at > 0.0
