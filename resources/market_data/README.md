# Market Data Fixtures

Static JSON snapshots of `MarketData` for local development, integration tests, and API demos. Files are version-controlled resources on disk; no loader or provider ships in this directory.

## Directory layout

| File | Symbol |
|------|--------|
| `btc_usdt.json` | `BTC/USDT` |
| `eth_usdt.json` | `ETH/USDT` |

## Filename convention

- Lowercase base and quote separated by underscore: `{base}_{quote}.json`
- The slash in the trading pair appears only in the JSON `symbol` field, not in the filename.

## Root document (`MarketData`)

| JSON field | Domain type | Serialization |
|------------|-------------|---------------|
| `symbol` | `str` | Plain JSON string (e.g. `"BTC/USDT"`) |
| `current_price` | `Decimal` | JSON string |
| `order_book` | `OrderBook` | JSON object (see below) |
| `series` | `tuple[CandleSeries, ...]` | JSON array of `CandleSeries` objects |

## `order_book`

| JSON field | Domain type | Serialization |
|------------|-------------|---------------|
| `bids` | `tuple[OrderLevel, ...]` | JSON array; best bid first (highest price) |
| `asks` | `tuple[OrderLevel, ...]` | JSON array; best ask first (lowest price) |

### `OrderLevel` (elements of `bids` / `asks`)

| JSON field | Domain type | Serialization |
|------------|-------------|---------------|
| `price` | `Decimal` | JSON string |
| `quantity` | `Decimal` | JSON string |

## `CandleSeries` (elements of `series`)

| JSON field | Domain type | Serialization |
|------------|-------------|---------------|
| `timeframe` | `Timeframe` | JSON string enum value |
| `candles` | `tuple[Candle, ...]` | JSON array of `Candle` objects |

### `Timeframe` enum values

| Enum member | JSON value |
|-------------|------------|
| `M15` | `"15m"` |
| `H1` | `"1h"` |
| `H4` | `"4h"` |
| `D1` | `"1d"` |

Fixtures in this directory include at least one series with `timeframe: "15m"` and at least 30 contiguous candles.

## `Candle` (elements of `candles`)

| JSON field | Domain type | Required | Serialization |
|------------|-------------|----------|---------------|
| `start_time` | `datetime` | Yes | ISO 8601 UTC (`Z` suffix or `+00:00`) |
| `end_time` | `datetime` | Yes | ISO 8601 UTC |
| `open` | `Decimal` | Yes | JSON string |
| `high` | `Decimal` | Yes | JSON string |
| `low` | `Decimal` | Yes | JSON string |
| `close` | `Decimal` | Yes | JSON string |
| `base_volume` | `Decimal` | Yes | JSON string |
| `quote_volume` | `Decimal \| None` | No | JSON string or `null` |
| `trade_count` | `int \| None` | No | JSON integer or `null` |
| `buy_volume` | `Decimal \| None` | No | JSON string or `null` |
| `buy_quote_volume` | `Decimal \| None` | No | JSON string or `null` |

## Serialization rules

1. **Decimals** — All domain `Decimal` fields (`current_price`, OHLCV, order book levels, optional volume fields) must be JSON strings, not JSON numbers, to preserve precision.
2. **Datetimes** — Candle `start_time` and `end_time` use ISO 8601 with UTC timezone (e.g. `"2024-06-01T12:00:00Z"`).
3. **Order book ordering** — Bid prices decrease from best bid; ask prices increase from best ask.
4. **Price consistency** — `current_price` equals the last M15 candle `close` and lies strictly between the best bid and best ask.

## Deserialization mapping

```python
from datetime import datetime
from decimal import Decimal

from market_data_be.modules.analysis.models import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    OrderLevel,
    Timeframe,
)


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_optional_decimal(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def candle_from_dict(data: dict) -> Candle:
    return Candle(
        start_time=parse_datetime(data["start_time"]),
        end_time=parse_datetime(data["end_time"]),
        open=Decimal(data["open"]),
        high=Decimal(data["high"]),
        low=Decimal(data["low"]),
        close=Decimal(data["close"]),
        base_volume=Decimal(data["base_volume"]),
        quote_volume=parse_optional_decimal(data.get("quote_volume")),
        trade_count=data.get("trade_count"),
        buy_volume=parse_optional_decimal(data.get("buy_volume")),
        buy_quote_volume=parse_optional_decimal(data.get("buy_quote_volume")),
    )


def market_data_from_dict(data: dict) -> MarketData:
    return MarketData(
        symbol=data["symbol"],
        current_price=Decimal(data["current_price"]),
        order_book=OrderBook(
            bids=tuple(
                OrderLevel(Decimal(level["price"]), Decimal(level["quantity"]))
                for level in data["order_book"]["bids"]
            ),
            asks=tuple(
                OrderLevel(Decimal(level["price"]), Decimal(level["quantity"]))
                for level in data["order_book"]["asks"]
            ),
        ),
        series=tuple(
            CandleSeries(
                timeframe=Timeframe(series["timeframe"]),
                candles=tuple(candle_from_dict(candle) for candle in series["candles"]),
            )
            for series in data["series"]
        ),
    )
```

Load a fixture with stdlib `json`:

```python
import json
from pathlib import Path

fixture_path = Path("resources/market_data/btc_usdt.json")
payload = json.loads(fixture_path.read_text(encoding="utf-8"))
market_data = market_data_from_dict(payload)
```
