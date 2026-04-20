"""HTTP-level tests for the FastAPI app shell - /api/health and end-to-end SSE.

The SSE tests use a real uvicorn server on 127.0.0.1:<random_port> rather than
httpx.ASGITransport. ASGITransport awaits the full ASGI app call before
returning a Response and buffers body chunks in memory, so it cannot drain an
infinite SSE generator (the server-side `while True` loop in
app/market/stream.py never signals more_body=False). A real server + real
socket exposes chunks as they are emitted, which is what an EventSource client
actually sees. This is a Rule 1 deviation from the plan's prescribed
ASGITransport+client.stream pattern (documented in the plan's SUMMARY).

Each test builds a fresh FastAPI(lifespan=lifespan) via _build_app() instead of
importing the module-level app.main.app. Reason: app/market/stream.py holds a
module-level APIRouter that accumulates /prices routes across create_stream_router
calls, so running the shared app's lifespan twice leaves stale /api/stream/prices
routes wired to a torn-down PriceCache - the second streaming request then gets
served by the stale route whose cache version never advances, causing a 5s read
timeout. Fresh app per test sidesteps that shared-state bug (same pattern
test_lifespan.py already uses). Also pulls in the one inline /api/health route
from app.main so TestHealth exercises the production wiring.
"""

from __future__ import annotations

import asyncio
import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest
import uvicorn
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.lifespan import lifespan


def _build_app() -> FastAPI:
    """Build a fresh FastAPI app bound to the production lifespan.

    Mirrors the /api/health route from app.main so these tests exercise the
    same wiring the real server uses without depending on the module-level app
    singleton (see module docstring for why shared-app causes failures).
    """
    test_app = FastAPI(lifespan=lifespan)

    @test_app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return test_app


def _free_port() -> int:
    """Bind to port 0 to let the OS pick a free port, then release it."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@asynccontextmanager
async def _run_uvicorn(app_: FastAPI, port: int) -> AsyncIterator[None]:
    """Run uvicorn.Server in-process on 127.0.0.1:<port> for the duration of the block.

    Uses loop='asyncio' so the server shares the pytest-asyncio event loop.
    Waits up to ~5s for Server.started to flip True before yielding.
    Signals shutdown via should_exit and awaits the serve() task on exit.
    """
    config = uvicorn.Config(
        app_, host="127.0.0.1", port=port, log_level="warning", loop="asyncio"
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(100):
        if server.started:
            break
        await asyncio.sleep(0.05)
    assert server.started, "uvicorn server did not start within 5s"
    try:
        yield
    finally:
        server.should_exit = True
        await task


@pytest.mark.asyncio
class TestHealth:
    """GET /api/health - the one inline route in main.py (D-04)."""

    async def test_health_returns_ok(self):
        """Returns HTTP 200 with body {'status': 'ok'}.

        Uses ASGITransport for speed - /api/health is a finite response so the
        transport's buffer-until-complete semantics are fine here.
        """
        app = _build_app()
        with patch.dict(os.environ, {}, clear=True):
            async with LifespanManager(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
class TestSSEStream:
    """End-to-end proof of APP-04: a real EventSource-equivalent client receives
    ticks from the lifespan-mounted /api/stream/prices."""

    async def test_sse_emits_at_least_one_data_frame(self):
        """A streaming GET on /api/stream/prices yields >= 1 'data:' frame within 5s.

        Proves the full Phase 1 wiring end-to-end: lifespan started, PriceCache
        constructed, simulator producing ticks, SSE router mounted,
        /api/stream/prices reachable over a real TCP socket, and the existing
        version-gated emit loop pushing data.
        """
        app = _build_app()
        port = _free_port()
        with patch.dict(os.environ, {}, clear=True):
            async with _run_uvicorn(app, port):
                async with httpx.AsyncClient(
                    base_url=f"http://127.0.0.1:{port}", timeout=5.0
                ) as client:
                    async with client.stream("GET", "/api/stream/prices") as resp:
                        assert resp.status_code == 200
                        saw_data = False
                        async for line in resp.aiter_lines():
                            if line.startswith("data:"):
                                saw_data = True
                                break
        assert saw_data, "no 'data:' frame received within 5s"

    async def test_sse_continues_emitting_as_cache_version_advances(self):
        """The stream keeps emitting as the simulator advances the cache version.

        Mirrors backend/tests/market/test_simulator_source.py::test_prices_update_over_time
        but at the HTTP boundary - closes APP-04 with continuity, not just first-frame.
        """
        app = _build_app()
        port = _free_port()
        with patch.dict(os.environ, {}, clear=True):
            async with _run_uvicorn(app, port):
                async with httpx.AsyncClient(
                    base_url=f"http://127.0.0.1:{port}", timeout=5.0
                ) as client:
                    async with client.stream("GET", "/api/stream/prices") as resp:
                        assert resp.status_code == 200
                        data_frames = 0
                        async for line in resp.aiter_lines():
                            if line.startswith("data:"):
                                data_frames += 1
                                if data_frames >= 2:
                                    break
        assert data_frames >= 2, f"expected >= 2 data frames, got {data_frames}"
