"""Regression: market_data_demo.TICKERS is derived from SEED_PRICES (D-06)."""

from app.market.seed_prices import SEED_PRICES


class TestDemoTickerList:
    """Pin the demo's ticker list to the canonical SEED_PRICES dict."""

    def test_demo_tickers_match_seed_prices(self):
        """market_data_demo.TICKERS must equal list(SEED_PRICES.keys()).

        Closes CONCERNS.md #9 — preventing a future drift where the demo
        has tickers that don't appear in the DB watchlist seed (or vice versa).
        """
        import market_data_demo

        assert set(market_data_demo.TICKERS) == set(SEED_PRICES)
        assert len(market_data_demo.TICKERS) == 10
        # list() of a dict's keys preserves insertion order in Python 3.7+.
        assert market_data_demo.TICKERS == list(SEED_PRICES.keys())
