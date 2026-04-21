"""Unit tests for get_watchlist: ordering, cache-cold fallback, warm-cache enrichment."""

from __future__ import annotations

from app.market.seed_prices import SEED_PRICES
from app.watchlist.service import get_watchlist


class TestGetWatchlist:
    def test_returns_ten_seeded_tickers_alpha_ordered(self, fresh_db, warmed_cache):
        response = get_watchlist(fresh_db, warmed_cache)
        tickers = [item.ticker for item in response.items]
        assert tickers == sorted(SEED_PRICES.keys())

    def test_enriches_from_warm_cache(self, fresh_db, warmed_cache):
        response = get_watchlist(fresh_db, warmed_cache)
        aapl = next(i for i in response.items if i.ticker == "AAPL")
        assert aapl.price == SEED_PRICES["AAPL"]
        assert aapl.direction in ("up", "down", "flat")
        assert aapl.timestamp is not None

    def test_cold_cache_returns_none_for_all_price_fields(self, fresh_db):
        from app.market import PriceCache

        empty_cache = PriceCache()
        response = get_watchlist(fresh_db, empty_cache)
        assert len(response.items) == 10
        for item in response.items:
            assert item.price is None
            assert item.previous_price is None
            assert item.change_percent is None
            assert item.direction is None
            assert item.timestamp is None
            assert item.added_at  # added_at always populated from DB

    def test_empty_watchlist_returns_empty_items(self, fresh_db, warmed_cache):
        fresh_db.execute("DELETE FROM watchlist WHERE user_id = 'default'")
        fresh_db.commit()
        response = get_watchlist(fresh_db, warmed_cache)
        assert response.items == []
