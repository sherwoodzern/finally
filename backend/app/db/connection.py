"""SQLite connection lifecycle for FinAlly."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


def open_database(path: str) -> sqlite3.Connection:
    """Open a long-lived SQLite connection at `path`.

    Creates the parent directory if missing (D-09). Returns a connection with
    `sqlite3.Row` as the row factory (D-02) and `check_same_thread=False` (D-01).
    Manual-commit isolation mode is left at the stdlib default (D-03) - callers
    that write must call `conn.commit()` explicitly.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    logger.info("DB opened at %s", path)
    return conn
