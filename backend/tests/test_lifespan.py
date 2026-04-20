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

    async def test_attaches_price_cache_to_app_state(self):
        """Entering the lifespan attaches a PriceCache to app.state.price_cache."""
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                assert isinstance(app.state.price_cache, PriceCache)

    async def test_attaches_market_source_to_app_state(self):
        """Entering the lifespan attaches a started MarketDataSource to app.state."""
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                assert isinstance(app.state.market_source, MarketDataSource)
                assert set(app.state.market_source.get_tickers()) == set(SEED_PRICES)

    async def test_uses_simulator_when_massive_api_key_absent(self):
        """With no MASSIVE_API_KEY, the factory selects SimulatorDataSource."""
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                assert isinstance(app.state.market_source, SimulatorDataSource)

    async def test_seeds_cache_immediately_on_startup(self):
        """All SEED_PRICES tickers are present in the cache before any test code runs.

        This is the contract that makes /api/stream/prices have data on first connect
        (mirrors backend/tests/market/test_simulator_source.py::test_start_populates_cache).
        """
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                cache: PriceCache = app.state.price_cache
                for ticker in SEED_PRICES:
                    assert cache.get(ticker) is not None, ticker

    async def test_includes_sse_router_during_startup(self):
        """app.include_router(create_stream_router(cache)) ran in lifespan startup,
        so /api/stream/prices is registered on the app while the lifespan is active."""
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                paths = {getattr(r, "path", None) for r in app.router.routes}
                assert "/api/stream/prices" in paths, paths

    async def test_missing_openrouter_key_logs_warning_and_proceeds(self, caplog):
        """Missing OPENROUTER_API_KEY does not raise - only a single warning is logged.

        Implements CONTEXT.md missing-env policy: Phase 5 will fail loud when chat is
        hit; Phase 1 startup must not block on a key it does not yet use.
        """
        caplog.set_level(logging.WARNING, logger="app.lifespan")
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                pass
        messages = [rec.message for rec in caplog.records]
        assert any("OPENROUTER_API_KEY" in m for m in messages), messages

    async def test_stops_source_on_shutdown(self):
        """Exiting the lifespan awaits source.stop() - background task is no longer running."""
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                source = app.state.market_source
            # After exit, the simulator's _task is None or done (mirrors
            # SimulatorDataSource.stop semantics in backend/app/market/simulator.py:231-240).
            task = getattr(source, "_task", None)
            assert task is None or task.done()
