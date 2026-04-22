"""Deterministic keyword-scripted chat client for LLM_MOCK=true (D-06)."""

from __future__ import annotations

import re

from .models import StructuredResponse, TradeAction, WatchlistAction

_TICKER = r"[A-Z][A-Z0-9.]{0,9}"
_QTY = r"\d+(?:\.\d+)?"

_BUY = re.compile(rf"\bbuy\s+({_TICKER})\s+({_QTY})\b", re.IGNORECASE)
_SELL = re.compile(rf"\bsell\s+({_TICKER})\s+({_QTY})\b", re.IGNORECASE)
_ADD = re.compile(rf"\badd\s+({_TICKER})\b", re.IGNORECASE)
_REMOVE = re.compile(rf"\b(?:remove|drop)\s+({_TICKER})\b", re.IGNORECASE)


class MockChatClient:
    """Keyword-scripted deterministic ChatClient (D-06). Never calls an LLM."""

    async def complete(self, messages: list[dict]) -> StructuredResponse:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )

        trades: list[TradeAction] = []
        for m in _BUY.finditer(last_user):
            trades.append(
                TradeAction(ticker=m.group(1), side="buy", quantity=float(m.group(2)))
            )
        for m in _SELL.finditer(last_user):
            trades.append(
                TradeAction(ticker=m.group(1), side="sell", quantity=float(m.group(2)))
            )

        watchlist: list[WatchlistAction] = []
        for m in _ADD.finditer(last_user):
            watchlist.append(WatchlistAction(ticker=m.group(1), action="add"))
        for m in _REMOVE.finditer(last_user):
            watchlist.append(WatchlistAction(ticker=m.group(1), action="remove"))

        if not trades and not watchlist:
            return StructuredResponse(
                message="mock response", trades=[], watchlist_changes=[]
            )

        parts = [f"{t.side} {t.ticker} {t.quantity}" for t in trades] + [
            f"{w.action} {w.ticker}" for w in watchlist
        ]
        return StructuredResponse(
            message=f"Mock: executing {', '.join(parts)}",
            trades=trades,
            watchlist_changes=watchlist,
        )
