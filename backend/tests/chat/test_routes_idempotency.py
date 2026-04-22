"""Integration test for the 'idempotent-adjacent replay' invariant (VALIDATION.md).

Property: replaying the same user message via POST /api/chat yields a NEW
(user, assistant) chat_messages pair without mutating the prior rows. This
locks the VALIDATION.md 'Property & Contract Coverage' row:

    "Chat turn is idempotent-adjacent: replaying the same user message
     yields a new chat_messages pair without mutating prior rows"

The property matters because chat_messages is an append-only log. A regression
that UPDATE-in-places prior rows (e.g., changing created_at or content) would
silently break history replay + transcript integrity.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.lifespan import lifespan

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def app_with_lifespan(tmp_path_factory) -> AsyncIterator[FastAPI]:
    db_path = tmp_path_factory.mktemp("chat_idempotency") / "finally.db"
    app = FastAPI(lifespan=lifespan)
    env = {"DB_PATH": str(db_path), "LLM_MOCK": "true"}
    with patch.dict(os.environ, env, clear=True):
        async with LifespanManager(app):
            yield app


@pytest_asyncio.fixture(loop_scope="module")
async def client(app_with_lifespan: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app_with_lifespan)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _snapshot_rows(db, user_id: str = "default") -> list[tuple]:
    """Return (id, role, content, actions, created_at) tuples in ASC order."""
    return [
        tuple(r)
        for r in db.execute(
            "SELECT id, role, content, actions, created_at "
            "FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC",
            (user_id,),
        ).fetchall()
    ]


def _purge(db, user_id: str = "default") -> None:
    db.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    db.commit()


class TestReplayIdempotency:
    async def test_same_message_twice_appends_without_mutating_priors(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """Two POSTs of the same body -> 4 rows total; first 2 are byte-identical to snapshot-after-first."""
        app = app_with_lifespan
        _purge(app.state.db)

        # First turn
        resp1 = await client.post("/api/chat", json={"message": "hello"})
        assert resp1.status_code == 200, resp1.text
        snapshot_after_first = _snapshot_rows(app.state.db)
        assert len(snapshot_after_first) == 2

        # Second turn with IDENTICAL payload
        resp2 = await client.post("/api/chat", json={"message": "hello"})
        assert resp2.status_code == 200, resp2.text
        snapshot_after_second = _snapshot_rows(app.state.db)

        # Append-only: exactly 2 new rows, prior 2 rows byte-identical.
        assert len(snapshot_after_second) == 4
        assert snapshot_after_second[:2] == snapshot_after_first, (
            "Prior chat_messages rows were mutated by replay — append-only "
            "invariant violated."
        )
        # New rows carry the same content; distinct ids.
        assert snapshot_after_second[2][1] == "user"
        assert snapshot_after_second[2][2] == "hello"
        assert snapshot_after_second[3][1] == "assistant"
        # Distinct primary keys: four UUIDs, no collision.
        ids = {row[0] for row in snapshot_after_second}
        assert len(ids) == 4
