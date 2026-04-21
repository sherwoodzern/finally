"""Pydantic v2 request/response schemas + ticker normalization for the watchlist API."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")


def normalize_ticker(value: str) -> str:
    """Strip + uppercase + regex-validate a ticker symbol.

    Raises ValueError if the normalized form does not match ^[A-Z][A-Z0-9.]{0,9}$.
    The regex (1) forces a leading alpha, (2) allows digits/dot for classes like
    BRK.B, and (3) caps total length at 10 chars so SQL injection surfaces stay
    narrow (D-04).
    """
    v = value.strip().upper()
    if not _TICKER_RE.fullmatch(v):
        raise ValueError(f"invalid ticker: {value!r}")
    return v


class WatchlistAddRequest(BaseModel):
    """Request body for POST /api/watchlist (D-03, D-04).

    extra='forbid' rejects unknown keys with 422. The before-mode validator
    normalizes the ticker before the regex enforces shape; downstream handlers
    can trust `request.ticker` is already uppercase and valid.
    """

    model_config = ConfigDict(extra="forbid")

    ticker: str

    @field_validator("ticker", mode="before")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return normalize_ticker(v)


class WatchlistItem(BaseModel):
    """One row in GET /api/watchlist response.

    Price fields are Optional because the price cache may be cold for newly
    added tickers (D-05). `direction` uses the same literal vocabulary as
    PriceUpdate.direction to prevent drift (Pitfall 1).
    """

    ticker: str
    added_at: str
    price: float | None
    previous_price: float | None
    change_percent: float | None
    direction: Literal["up", "down", "flat"] | None
    timestamp: float | None


class WatchlistResponse(BaseModel):
    """Response for GET /api/watchlist."""

    items: list[WatchlistItem]


class WatchlistMutationResponse(BaseModel):
    """Response for POST /api/watchlist and DELETE /api/watchlist/{ticker} (D-06).

    `status` is a four-way literal because idempotent no-ops are always 200 OK
    with a status discriminator, never 409/404 (SC#4).
    """

    ticker: str
    status: Literal["added", "exists", "removed", "not_present"]
