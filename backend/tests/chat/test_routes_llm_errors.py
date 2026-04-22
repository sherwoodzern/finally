"""Integration test: ChatTurnError bubbles from run_turn -> HTTP 502 (D-14, D-18).

Proves that when the LLM client raises, the user turn is STILL persisted (D-18
invariant) while the assistant turn is NOT - i.e., the DB shows exactly one
new row after a failing POST.

DESIGN NOTE (intentional mini-lifespan):
This file is the ONE test module that does NOT use `app.lifespan.lifespan`. The
reason is that `app.lifespan.lifespan` imports the factory with
`from .chat import create_chat_client`, which rebinds the name into the
`app.lifespan` module namespace at import time. A `unittest.mock.patch` of
`app.chat.client.create_chat_client` therefore does NOT intercept the lifespan
call-site. Injecting a RaisingChatClient requires a mount-time override, which is
what the mini-lifespan below does. DB + cache + source setup mirror the real
lifespan (open_database + init_database + seed_defaults + PriceCache + FakeSource),
so the test exercises a genuine app - only the LLM client is a test double.
The happy-path + history test files use the real full lifespan, so end-to-end
wiring is already covered there.

RaisingChatClient signature (Plan 02): __init__(self, exc: BaseException).
FakeSource signature (Plan 02): __init__(self) -- no args.
Both imports come from backend/tests/chat/conftest.py (Plan 02 Task 1).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.chat import create_chat_router
from app.db import init_database, open_database, seed_defaults
from app.market import PriceCache

# FakeSource and RaisingChatClient come from the Plan 02 conftest.
from tests.chat.conftest import FakeSource, RaisingChatClient

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture(scope="module")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def app_with_raising_client(
    tmp_path_factory,
) -> AsyncIterator[tuple[FastAPI, sqlite3.Connection]]:
    """Mini-lifespan that wires a RaisingChatClient instead of the factory default.

    Mirrors backend/app/lifespan.py's setup (DB + cache + source) but substitutes
    the LLM client at route-mount time. See module docstring for rationale.
    """
    db_path: Path = tmp_path_factory.mktemp("chat_llm_err") / "finally.db"
    app = FastAPI()

    async def _startup():
        with patch.dict(os.environ, {"DB_PATH": str(db_path)}, clear=True):
            conn = open_database(str(db_path))
            init_database(conn)
            seed_defaults(conn)
            cache = PriceCache()
            # FakeSource() takes NO args - it only records add/remove calls.
            # The chat service only calls add_ticker/remove_ticker on source,
            # never enumerates tickers, so a bare FakeSource is sufficient.
            source = FakeSource()
            # RaisingChatClient(exc) REQUIRES an exception - Plan 02 contract.
            client = RaisingChatClient(RuntimeError("simulated LLM failure"))
            app.state.db = conn
            app.state.price_cache = cache
            app.state.market_source = source
            app.state.chat_client = client
            app.include_router(create_chat_router(conn, cache, source, client))

    async def _shutdown():
        app.state.db.close()

    app.router.on_startup.append(_startup)
    app.router.on_shutdown.append(_shutdown)
    async with LifespanManager(app):
        yield app, app.state.db


@pytest_asyncio.fixture(loop_scope="module")
async def client(
    app_with_raising_client: tuple[FastAPI, sqlite3.Connection],
) -> AsyncIterator[httpx.AsyncClient]:
    app, _ = app_with_raising_client
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _chat_row_count(db: sqlite3.Connection, user_id: str = "default") -> int:
    return db.execute(
        "SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)
    ).fetchone()[0]


class TestLLMFailureBoundary:
    async def test_chat_turn_error_maps_to_502_with_error_envelope(
        self,
        client: httpx.AsyncClient,
        app_with_raising_client: tuple[FastAPI, sqlite3.Connection],
    ):
        """RaisingChatClient.complete raises -> POST returns 502 + chat_turn_error."""
        _, db = app_with_raising_client
        before = _chat_row_count(db)
        resp = await client.post("/api/chat", json={"message": "will fail"})
        assert resp.status_code == 502, resp.text
        body = resp.json()
        assert "detail" in body
        detail = body["detail"]
        assert detail["error"] == "chat_turn_error"
        assert isinstance(detail["message"], str) and detail["message"]
        # D-18 invariant: user row written, assistant row NOT written.
        after = _chat_row_count(db)
        assert after == before + 1, (before, after)
        # The single new row is a USER row (role='user'), content echoes the input.
        row = db.execute(
            "SELECT role, content, actions FROM chat_messages "
            "WHERE user_id = 'default' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        assert row is not None
        assert row[0] == "user"
        assert row[1] == "will fail"
        assert row[2] is None  # user rows always have NULL actions
