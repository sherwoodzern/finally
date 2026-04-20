"""FinAlly FastAPI application entrypoint."""

from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI

from .lifespan import lifespan

# Load .env from CWD upward BEFORE the app is built, so MASSIVE_API_KEY,
# OPENROUTER_API_KEY, and LLM_MOCK are present when the lifespan runs and the
# factory reads them. Silent no-op if .env is absent (matches CONTEXT.md hard
# constraint: missing values must not crash startup).
load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness probe. Returns {"status": "ok"} with HTTP 200."""
    return {"status": "ok"}
