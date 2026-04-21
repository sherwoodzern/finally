"""Unit tests for add_ticker: new-row commit + duplicate no-op invariants."""

from __future__ import annotations

from app.watchlist.service import AddResult, add_ticker


def _count(conn, user_id: str = "default") -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


class TestAddTicker:
    def test_new_ticker_commits_row_and_returns_added(self, fresh_db):
        before = _count(fresh_db)
        result = add_ticker(fresh_db, "PYPL")
        assert result == AddResult(ticker="PYPL", status="added")
        assert _count(fresh_db) == before + 1

        row = fresh_db.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = 'default' AND ticker = 'PYPL'"
        ).fetchone()
        assert row is not None
        assert row["ticker"] == "PYPL"
        assert row["added_at"]  # ISO timestamp populated

    def test_duplicate_returns_exists_and_leaves_count_unchanged(self, fresh_db):
        """AAPL is seeded; add_ticker('AAPL') is a no-op that MUST NOT raise (SC#4, D-06)."""
        before = _count(fresh_db)
        result = add_ticker(fresh_db, "AAPL")
        assert result == AddResult(ticker="AAPL", status="exists")
        assert _count(fresh_db) == before

    def test_second_add_of_new_ticker_returns_exists(self, fresh_db):
        add_ticker(fresh_db, "PYPL")
        second = add_ticker(fresh_db, "PYPL")
        assert second.status == "exists"
        count_pypl = fresh_db.execute(
            "SELECT COUNT(*) FROM watchlist WHERE user_id = 'default' AND ticker = 'PYPL'"
        ).fetchone()[0]
        assert count_pypl == 1
