# Massive API (formerly Polygon.io)

Polygon.io rebranded to Massive.com on 2025-10-30. Existing API keys, SDKs, and
endpoints continue to work. The canonical host is now `api.massive.com`
(`api.polygon.io` still resolves). Docs live at `https://massive.com/docs`.

This project uses Massive only when `MASSIVE_API_KEY` is set in `.env`.
Otherwise the in-process simulator is used (see `MARKET_SIMULATOR.md`).

## Authentication

All REST requests require the API key. Two equivalent forms:

- Header: `Authorization: Bearer $MASSIVE_API_KEY`
- Query string: `?apiKey=$MASSIVE_API_KEY`

The official Python client (`massive`) also reads `MASSIVE_API_KEY` from the
environment automatically.

## Endpoints we use

FinAlly only needs two pieces of data:

1. Current/near-real-time price for the union of watchlist tickers (polled).
2. End-of-day close per ticker (optional; used to seed "previous close" for
   the daily-change calculation).

### 1. Snapshot — multiple tickers (realtime-ish)

```
GET https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers
    ?tickers=AAPL,GOOGL,MSFT
    &apiKey=$MASSIVE_API_KEY
```

Query parameters:

| Param         | Type    | Notes                                               |
|---------------|---------|-----------------------------------------------------|
| `tickers`     | csv     | Case-sensitive list. Omit to get every US ticker.   |
| `include_otc` | boolean | Default `false`.                                    |

Response shape (abridged):

```json
{
  "status": "OK",
  "tickers": [
    {
      "ticker": "AAPL",
      "todaysChange": 1.23,
      "todaysChangePerc": 0.65,
      "updated": 1739563200000000000,
      "day":    {"o": 189.1, "h": 191.0, "l": 188.5, "c": 190.4, "v": 52000000},
      "min":    {"o": 190.3, "h": 190.5, "l": 190.2, "c": 190.4, "v": 15000, "t": 1739563140000},
      "prevDay":{"o": 188.0, "h": 189.9, "l": 187.5, "c": 189.2, "v": 48000000},
      "lastTrade":{"p": 190.42, "s": 100, "t": 1739563199500000000},
      "lastQuote":{"bp": 190.40, "ap": 190.44, "bs": 2, "as": 5, "t": 1739563199500000000}
    }
  ]
}
```

Price we use: `lastTrade.p` when present, falling back to `min.c`, then
`day.c`. Previous close for daily-change: `prevDay.c`.

### 2. Grouped Daily (EOD) Bars

```
GET https://api.massive.com/v2/aggs/grouped/locale/us/market/stocks/{YYYY-MM-DD}
    ?adjusted=true
    &apiKey=$MASSIVE_API_KEY
```

Returns one OHLCV row per ticker for the given date:

```json
{
  "status": "OK",
  "queryCount": 10000,
  "resultsCount": 10000,
  "adjusted": true,
  "results": [
    {"T": "AAPL", "o": 188.0, "h": 189.9, "l": 187.5, "c": 189.2, "v": 48000000, "vw": 188.7, "t": 1739491200000, "n": 420000}
  ]
}
```

Use the most recent trading day's response to seed `previous_close` for every
watchlist ticker at startup.

## Rate limits

Massive tiers determine call budget. FinAlly assumes the Starter/Free tier:

| Tier      | Requests/min | Suggested poll interval                |
|-----------|--------------|----------------------------------------|
| Free      | 5            | 15 s (one multi-ticker snapshot call)  |
| Starter   | 100          | 2–5 s                                  |
| Developer | unlimited*   | 2 s (our floor)                        |

A single multi-ticker snapshot call covers the entire watchlist, so one
request per poll is enough regardless of watchlist size.

## Python client

Installed via `uv add massive`. Usage:

```python
import os
from massive import RESTClient

client = RESTClient(os.environ["MASSIVE_API_KEY"])

# Multi-ticker snapshot
snap = client.get_snapshot_all(
    market_type="stocks",
    tickers=["AAPL", "GOOGL", "MSFT"],
)
for t in snap:
    print(t.ticker, t.last_trade.price if t.last_trade else t.min.close)

# Grouped daily bars for 2026-04-13
bars = client.get_grouped_daily_aggs(date="2026-04-13", adjusted=True)
for b in bars:
    print(b.ticker, b.close)
```

We also fall back to plain `httpx` for endpoints not covered by the SDK, or
when we want full control over timeouts and retries:

```python
import httpx, os

API = "https://api.massive.com"
KEY = os.environ["MASSIVE_API_KEY"]

async def snapshot(tickers: list[str]) -> list[dict]:
    url = f"{API}/v2/snapshot/locale/us/markets/stocks/tickers"
    params = {"tickers": ",".join(tickers), "apiKey": KEY}
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get(url, params=params)
        r.raise_for_status()
        return r.json()["tickers"]
```

## Error handling

- `401` — invalid/missing key. Log and fall back to simulator for the process
  lifetime (don't spam retries).
- `429` — rate limited. Back off: double the poll interval for the next two
  polls, then reset.
- `5xx` / network error — log, reuse the last cached price, retry next tick.
- Empty `tickers` array in response — treat as "no update", keep cache.

## References

- [Full Market Snapshot](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)
- [Unified Snapshot](https://massive.com/docs/rest/stocks/snapshots/unified-snapshot)
- [Grouped Daily (EOD) Bars](https://massive.com/docs/rest/stocks/aggregates/daily-market-summary)
- [Python client](https://github.com/massive-com/client-python)
