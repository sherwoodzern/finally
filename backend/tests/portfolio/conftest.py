"""Shared fixtures for portfolio service + route tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest

from app.db import init_database, seed_defaults
from app.market import PriceCache
from app.market.seed_prices import SEED_PRICES


@pytest.fixture
def fresh_db() -> Iterator[sqlite3.Connection]:
    """Yield a seeded in-memory sqlite3.Connection with sqlite3.Row row factory."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_database(conn)
    seed_defaults(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def warmed_cache() -> PriceCache:
    """Return a PriceCache pre-populated with seed prices for the 10 default tickers."""
    cache = PriceCache()
    for ticker, price in SEED_PRICES.items():
        cache.update(ticker=ticker, price=price)
    return cache
