"""Chat subsystem for FinAlly: LLM-driven auto-exec chat endpoint.

Public API:
    Models: ChatRequest, ChatResponse, StructuredResponse, TradeAction,
            WatchlistAction, TradeActionResult, WatchlistActionResult,
            ChatMessageOut, HistoryResponse
    Client: (added in Task 3)
    Prompts: (added in Task 4)
"""

from __future__ import annotations

from .models import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    HistoryResponse,
    StructuredResponse,
    TradeAction,
    TradeActionResult,
    WatchlistAction,
    WatchlistActionResult,
)

__all__ = [
    "ChatMessageOut",
    "ChatRequest",
    "ChatResponse",
    "HistoryResponse",
    "StructuredResponse",
    "TradeAction",
    "TradeActionResult",
    "WatchlistAction",
    "WatchlistActionResult",
]
