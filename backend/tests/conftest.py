"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture
def event_loop_policy():
    """Use the default event loop policy for all async tests."""
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Override DB_PATH to a per-test sqlite file under pytest tmp_path.

    Use this fixture in lifespan tests so the lifespan opens a fresh DB per
    test and cleans up automatically when tmp_path is torn down. Tests that
    also call `patch.dict(os.environ, {...}, clear=True)` MUST include
    `"DB_PATH": str(db_path)` in the dict - the clear would otherwise wipe
    the monkeypatched value before the lifespan reads it.
    """
    path = tmp_path / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    return path
