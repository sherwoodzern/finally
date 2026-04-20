"""Persistence: data survives close/re-open of the same file (DB-03 proxy)."""

from app.db import init_database, open_database, seed_defaults


class TestPersistence:
    """Integration tests for the file-level persistence contract.

    Phase 9 proves the Docker-volume variant; here we prove the primitive:
    the same file path opened twice in sequence retains its rows.
    """

    def test_data_survives_reopen(self, tmp_path):
        """Open, init+seed, close, re-open same path, rows present."""
        path = tmp_path / "finally.db"

        conn1 = open_database(str(path))
        init_database(conn1)
        seed_defaults(conn1)
        conn1.close()

        conn2 = open_database(str(path))
        users = conn2.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn2.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        conn2.close()

        assert users == 1
        assert wl == 10

    def test_parent_directory_created_on_first_open(self, tmp_path):
        """open_database creates a missing parent dir (D-09)."""
        path = tmp_path / "nested" / "deeper" / "finally.db"
        assert not path.parent.exists()

        conn = open_database(str(path))
        conn.close()

        assert path.parent.is_dir()
        assert path.exists()

    def test_reopen_after_seed_is_still_no_op(self, tmp_path):
        """Re-opening and re-running seed_defaults is a no-op."""
        path = tmp_path / "finally.db"

        conn1 = open_database(str(path))
        init_database(conn1)
        seed_defaults(conn1)
        conn1.close()

        conn2 = open_database(str(path))
        init_database(conn2)  # idempotent DDL
        seed_defaults(conn2)  # COUNT guard: watchlist non-empty, users PK collides
        users = conn2.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0]
        wl = conn2.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
        conn2.close()

        assert users == 1
        assert wl == 10
