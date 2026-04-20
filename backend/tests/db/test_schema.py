"""Tests for SQLite schema DDL (DB-01)."""

import sqlite3

import pytest

from app.db import init_database

EXPECTED_TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}


class TestSchema:
    """Unit tests for the six-table SQLite schema."""

    def _fresh(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_database(conn)
        return conn

    def test_all_six_tables_created(self):
        """init_database creates all six PLAN.md section 7 tables."""
        conn = self._fresh()
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert EXPECTED_TABLES.issubset(names), names

    def test_init_database_is_idempotent(self):
        """Running init_database twice does not raise."""
        conn = self._fresh()
        init_database(conn)  # second call - should be a no-op.
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert EXPECTED_TABLES.issubset(names)

    def test_user_id_defaults_to_default(self):
        """Inserting a watchlist row without user_id yields user_id='default'."""
        conn = self._fresh()
        conn.execute(
            "INSERT INTO watchlist (id, ticker, added_at) VALUES (?, ?, ?)",
            ("abc", "AAPL", "2026-04-20T00:00:00+00:00"),
        )
        row = conn.execute(
            "SELECT user_id FROM watchlist WHERE ticker = 'AAPL'"
        ).fetchone()
        assert row["user_id"] == "default"

    def test_watchlist_unique_constraint(self):
        """UNIQUE (user_id, ticker) rejects duplicate (default, AAPL) inserts."""
        conn = self._fresh()
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            ("1", "default", "AAPL", "2026-04-20T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                ("2", "default", "AAPL", "2026-04-20T00:00:00+00:00"),
            )

    def test_positions_unique_constraint(self):
        """UNIQUE (user_id, ticker) rejects duplicate positions rows."""
        conn = self._fresh()
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("1", "default", "AAPL", 1.0, 190.0, "2026-04-20T00:00:00+00:00"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("2", "default", "AAPL", 2.0, 195.0, "2026-04-20T00:00:00+00:00"),
            )
