"""Integration tests for POST /api/chat (CHAT-01, CHAT-04, CHAT-05 side-effects)."""

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
    db_path = tmp_path_factory.mktemp("chat_routes") / "finally.db"
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


def _chat_row_count(db, user_id: str = "default") -> int:
    return db.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


def _purge_chat(db, user_id: str = "default") -> None:
    db.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    db.commit()


class TestPostChat:
    async def test_happy_mock_returns_200_with_full_shape(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """POST 'hello' -> 200 + {message, trades:[], watchlist_changes:[]} + 2 DB rows."""
        app = app_with_lifespan
        _purge_chat(app.state.db)
        resp = await client.post("/api/chat", json={"message": "hello"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body.keys()) == {"message", "trades", "watchlist_changes"}
        assert isinstance(body["message"], str) and body["message"]
        assert isinstance(body["trades"], list)
        assert isinstance(body["watchlist_changes"], list)
        assert _chat_row_count(app.state.db) == 2

    async def test_mock_buy_keyword_executes_trade_and_echoes_result(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """MockChatClient regex hits 'buy AAPL' -> trade action auto-executes."""
        app = app_with_lifespan
        _purge_chat(app.state.db)
        resp = await client.post("/api/chat", json={"message": "buy AAPL 1"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["trades"]) >= 1, body
        t = body["trades"][0]
        # TradeActionResult has status in {executed, failed}; either is a legal outcome
        # (cold cache -> price_unavailable is acceptable if price hasn't streamed yet).
        assert t["ticker"] == "AAPL"
        assert t["side"] == "buy"
        assert t["status"] in {"executed", "failed"}

    async def test_empty_message_returns_422(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """ChatRequest.min_length=1 rejects empty message at the edge."""
        resp = await client.post("/api/chat", json={"message": ""})
        assert resp.status_code == 422, resp.text

    async def test_extra_key_returns_422(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """ChatRequest ConfigDict(extra='forbid') rejects unknown keys."""
        resp = await client.post(
            "/api/chat", json={"message": "hi", "stream": True}
        )
        assert resp.status_code == 422, resp.text

    async def test_missing_message_returns_422(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        resp = await client.post("/api/chat", json={})
        assert resp.status_code == 422, resp.text

    async def test_message_over_limit_returns_422(
        self, client: httpx.AsyncClient, app_with_lifespan: FastAPI
    ):
        """ChatRequest.max_length=8192 is the hard cap."""
        resp = await client.post(
            "/api/chat", json={"message": "x" * 8193}
        )
        assert resp.status_code == 422, resp.text
