"""Integration tests for GET /api/chat/history (CHAT-05, D-19)."""

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
    db_path = tmp_path_factory.mktemp("chat_history") / "finally.db"
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


def _purge(db, user_id: str = "default") -> None:
    db.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    db.commit()


class TestGetHistory:
    async def test_empty_history_returns_empty_list(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        _purge(app_with_lifespan.state.db)
        resp = await client.get("/api/chat/history")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"messages": []}

    async def test_asc_ordering_and_shape_invariant(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """Two turns -> 4 rows ordered ASC; user rows have actions=null."""
        _purge(app_with_lifespan.state.db)
        await client.post("/api/chat", json={"message": "first"})
        await client.post("/api/chat", json={"message": "second"})

        resp = await client.get("/api/chat/history?limit=10")
        assert resp.status_code == 200, resp.text
        msgs = resp.json()["messages"]
        assert len(msgs) == 4
        # ASC ordering: created_at non-decreasing
        timestamps = [m["created_at"] for m in msgs]
        assert timestamps == sorted(timestamps)
        # Role interleave: user, assistant, user, assistant
        assert [m["role"] for m in msgs] == [
            "user", "assistant", "user", "assistant"
        ]
        # User rows have actions=None; assistant rows have actions dict or None
        for m in msgs:
            assert set(m.keys()) == {"id", "role", "content", "actions", "created_at"}
            if m["role"] == "user":
                assert m["actions"] is None

    async def test_limit_bounds_rejected(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        resp_low = await client.get("/api/chat/history?limit=0")
        assert resp_low.status_code == 422
        resp_high = await client.get("/api/chat/history?limit=501")
        assert resp_high.status_code == 422

    async def test_limit_truncates_to_most_recent(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """Two turns (4 rows), limit=2 returns the LAST 2 rows ASC."""
        _purge(app_with_lifespan.state.db)
        await client.post("/api/chat", json={"message": "one"})
        await client.post("/api/chat", json={"message": "two"})

        resp = await client.get("/api/chat/history?limit=2")
        assert resp.status_code == 200
        msgs = resp.json()["messages"]
        assert len(msgs) == 2
        # The last 2 rows are (user:'two', assistant:'...') in ASC order.
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "two"
        assert msgs[1]["role"] == "assistant"
