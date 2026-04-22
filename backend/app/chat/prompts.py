"""Prompt assembly for the chat subsystem: system prompt, portfolio context, history window (D-15..D-17)."""

from __future__ import annotations

import json
import sqlite3

from app.market import PriceCache
from app.portfolio.service import get_portfolio
from app.watchlist.service import get_watchlist

CHAT_HISTORY_WINDOW = 20
DEFAULT_USER_ID = "default"

SYSTEM_PROMPT = (
    "You are FinAlly, an AI trading assistant embedded in a single-user "
    "trading workstation. Analyze the user's portfolio composition, risk, "
    "and P&L. Suggest trades with clear reasoning, auto-execute trades the "
    "user asks for (no confirmation needed), and manage the watchlist. Be "
    "concise and data-driven. Always respond with valid structured JSON "
    "matching the required schema: message (str), trades (list of "
    "{ticker, side, quantity}), watchlist_changes (list of {ticker, action})."
)


def build_portfolio_context(
    conn: sqlite3.Connection, cache: PriceCache
) -> dict:
    """Return a token-efficient dict of the user's current state (D-16).

    Reuses portfolio.service.get_portfolio + watchlist.service.get_watchlist so
    SQL lives in exactly one place per concept.
    """
    portfolio = get_portfolio(conn, cache)
    watchlist = get_watchlist(conn, cache)
    return {
        "cash_balance": portfolio.cash_balance,
        "total_value": portfolio.total_value,
        "positions": [p.model_dump(mode="json") for p in portfolio.positions],
        "watchlist": [
            {
                "ticker": w.ticker,
                "price": w.price,
                "change_percent": w.change_percent,
            }
            for w in watchlist.items
        ],
    }


def build_messages(
    conn: sqlite3.Connection, cache: PriceCache, user_message: str
) -> list[dict]:
    """Assemble the messages[] list for LiteLLM completion (D-15..D-17).

    Order: [system(SYSTEM_PROMPT), system(portfolio-json), *history_asc, user(user_message)]
    History: most-recent CHAT_HISTORY_WINDOW rows from chat_messages filtered by
    DEFAULT_USER_ID, still ordered ASC via the two-level subquery (Pitfall 8).
    """
    ctx = build_portfolio_context(conn, cache)
    rows = conn.execute(
        "SELECT role, content FROM ("
        "  SELECT role, content, created_at FROM chat_messages "
        "  WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        ") ORDER BY created_at ASC",
        (DEFAULT_USER_ID, CHAT_HISTORY_WINDOW),
    ).fetchall()

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": "# Current portfolio state\n" + json.dumps(ctx),
        },
    ]
    messages.extend(
        {"role": row["role"], "content": row["content"]} for row in rows
    )
    messages.append({"role": "user", "content": user_message})
    return messages
