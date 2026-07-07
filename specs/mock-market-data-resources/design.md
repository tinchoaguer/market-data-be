# Design

## Overview

Add two static JSON fixture files and a schema README under `resources/market_data/` at the project root. Each file is a serialized `MarketData` snapshot for one trading pair. No Python loader or provider is introduced in this feature; conformance is verified by tests that map JSON to existing domain dataclasses using the documented field contract. Domain modules remain unchanged.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|----------------------------------|
| Domain | `src/modules/analysis/models/` | Defines `MarketData` and related types; **read-only reference**, no changes |
| Resources (infrastructure) | `resources/market_data/` | Static JSON fixtures and schema documentation |
| Tests | `resources/tests/` or `src/infrastructure/tests/` | JSON-to-`MarketData` conformance validation |

### Directory layout

```
resources/
└── market_data/
    ├── README.md           # Schema contract and filename convention
    ├── btc_usdt.json       # BTC/USDT MarketData snapshot
    └── eth_usdt.json       # ETH/USDT MarketData snapshot
```

### Filename convention

| Symbol | Filename |
|--------|----------|
| `BTC/USDT` | `btc_usdt.json` |
| `ETH/USDT` | `eth_usdt.json` |

Rules: lowercase, base and quote separated by underscore, `.json` extension. The slash in the symbol appears only in the JSON `symbol` field, not in the filename.

### Out of scope (deferred to feature 3: market-data-provider)

- `MarketDataProvider` interface or mock provider implementation
- Application-layer wiring or HTTP endpoints
- Packaging fixtures inside the `market_data_be` Python package (files remain on disk at `resources/market_data/`)

## Data Flow

```
resources/market_data/{btc_usdt,eth_usdt}.json
        │
        │  (future) market-data-provider reads file bytes
        ▼
JSON parse + field mapping (infrastructure / provider — not this feature)
        │
        ▼
MarketData domain instance
        │
        ▼
analysis pipeline (MarketAnalysisEngine, analyzers)
```

For this feature, the terminal verification path is:

```
Fixture JSON  →  conformance test mapper  →  MarketData  →  invariant assertions
```

## Interfaces

### File resource contract

| Attribute | Value |
|-----------|-------|
| Location | `{PROJECT_ROOT}/resources/market_data/` |
| Encoding | UTF-8 |
| Format | JSON object (single root document per file) |
| Mutability | Static; version-controlled |

### JSON root document (`MarketData` mapping)

| JSON field | Domain type | Serialization rule |
|------------|-------------|-------------------|
| `symbol` | `str` | Plain JSON string |
| `current_price` | `Decimal` | JSON string (e.g., `"67234.50"`) |
| `order_book` | `OrderBook` | JSON object (see below) |
| `series` | `tuple[CandleSeries, ...]` | JSON array of `CandleSeries` objects |

### `order_book` object

| JSON field | Domain type | Serialization rule |
|------------|-------------|-------------------|
| `bids` | `tuple[OrderLevel, ...]` | JSON array, best bid first (highest price) |
| `asks` | `tuple[OrderLevel, ...]` | JSON array, best ask first (lowest price) |

### `OrderLevel` object (elements of `bids` / `asks`)

| JSON field | Domain type | Serialization rule |
|------------|-------------|-------------------|
| `price` | `Decimal` | JSON string |
| `quantity` | `Decimal` | JSON string |

### `CandleSeries` object (elements of `series`)

| JSON field | Domain type | Serialization rule |
|------------|-------------|-------------------|
| `timeframe` | `Timeframe` | JSON string enum value: `"15m"`, `"1h"`, `"4h"`, or `"1d"` |
| `candles` | `tuple[Candle, ...]` | JSON array of `Candle` objects |

**Required series for this feature:** at least one entry with `timeframe: "15m"`. Additional timeframes are optional and not required for acceptance.

### `Candle` object

| JSON field | Domain type | Required | Serialization rule |
|------------|-------------|----------|-------------------|
| `start_time` | `datetime` | Yes | ISO 8601 UTC (e.g., `"2024-06-01T12:00:00Z"`) |
| `end_time` | `datetime` | Yes | ISO 8601 UTC |
| `open` | `Decimal` | Yes | JSON string |
| `high` | `Decimal` | Yes | JSON string |
| `low` | `Decimal` | Yes | JSON string |
| `close` | `Decimal` | Yes | JSON string |
| `base_volume` | `Decimal` | Yes | JSON string |
| `quote_volume` | `Decimal \| None` | No | JSON string or JSON `null` |
| `trade_count` | `int \| None` | No | JSON integer or `null` |
| `buy_volume` | `Decimal \| None` | No | JSON string or `null` |
| `buy_quote_volume` | `Decimal \| None` | No | JSON string or `null` |

### Example document shape (truncated)

```json
{
  "symbol": "BTC/USDT",
  "current_price": "67234.50",
  "order_book": {
    "bids": [
      { "price": "67234.00", "quantity": "1.250" },
      { "price": "67233.50", "quantity": "2.100" }
    ],
    "asks": [
      { "price": "67235.00", "quantity": "0.980" },
      { "price": "67235.50", "quantity": "1.450" }
    ]
  },
  "series": [
    {
      "timeframe": "15m",
      "candles": [
        {
          "start_time": "2024-06-01T12:00:00Z",
          "end_time": "2024-06-01T12:15:00Z",
          "open": "67100.00",
          "high": "67200.00",
          "low": "67050.00",
          "close": "67180.00",
          "base_volume": "125.432",
          "quote_volume": "8420123.45",
          "trade_count": 1842,
          "buy_volume": "62.100",
          "buy_quote_volume": "4165234.10"
        }
      ]
    }
  ]
}
```

### Deserialization mapping (for tests and future provider)

```python
# Pseudocode — lives in test helper or future provider, not domain
MarketData(
    symbol=data["symbol"],
    current_price=Decimal(data["current_price"]),
    order_book=OrderBook(
        bids=tuple(OrderLevel(Decimal(l["price"]), Decimal(l["quantity"])) for l in data["order_book"]["bids"]),
        asks=tuple(OrderLevel(Decimal(l["price"]), Decimal(l["quantity"])) for l in data["order_book"]["asks"]),
    ),
    series=tuple(
        CandleSeries(
            timeframe=Timeframe(s["timeframe"]),
            candles=tuple(/* map each candle dict to Candle */),
        )
        for s in data["series"]
    ),
)
```

## Data Model

### Entity graph (existing domain — unchanged)

```
MarketData
├── symbol: str
├── current_price: Decimal
├── order_book: OrderBook
│   ├── bids: tuple[OrderLevel, ...]
│   └── asks: tuple[OrderLevel, ...]
└── series: tuple[CandleSeries, ...]
    └── CandleSeries
        ├── timeframe: Timeframe
        └── candles: tuple[Candle, ...]
            └── Candle (OHLCV + optional fields)
```

### Realistic data parameters

| Parameter | BTC/USDT guidance | ETH/USDT guidance |
|-----------|-------------------|-------------------|
| Price magnitude | ~60,000–75,000 USDT | ~3,000–4,500 USDT |
| M15 candle count | ≥ 30 (≥ 7.5 hours) | ≥ 30 |
| Order book levels | ≥ 5 bids, ≥ 5 asks | ≥ 5 bids, ≥ 5 asks |
| Spread | Tight relative to price (e.g., 0.01–5 USDT for BTC) | Proportionally tight for ETH |
| Volumes | Non-zero `base_volume`; optional fields populated on most candles | Same |

### Temporal sequencing

- Anchor `start_time` of the first M15 candle to a fixed UTC datetime (e.g., `2024-06-01T00:00:00Z`).
- Each subsequent candle: `start_time` = previous `end_time`, `end_time` = `start_time` + 15 minutes.
- Candles should exhibit modest price variation (not flat identical OHLC across all 30+ bars) so regime and risk analyzers receive meaningful input.

### Consistency rules

| Rule | Validation |
|------|------------|
| `current_price` == last M15 `close` | Decimal equality after parsing |
| Best bid < `current_price` < best ask | Strict inequality unless spread is zero (zero spread discouraged) |
| Bid prices descending | `bids[i].price > bids[i+1].price` |
| Ask prices ascending | `asks[i].price < asks[i+1].price` |
| OHLC invariants | `low <= open, close <= high` and `low <= high` |

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Missing fixture file | Conformance tests fail at setup; future provider should raise a clear file-not-found error (feature 3) |
| Invalid JSON syntax | `json.loads` fails; tests fail with parse error |
| Missing required field | Deserialization test fails with explicit assertion |
| Decimal as JSON number | Rejected by conformance tests (must be string per contract) |
| Invalid `timeframe` value | `Timeframe(...)` raises `ValueError`; tests fail |
| Fewer than 30 M15 candles | AC-005 fails |
| OHLC invariant violation | AC-007 fails |

No runtime recovery logic is required in this feature; invalid fixtures are caught by tests before merge.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Fixture existence | `resources/tests/test_market_data_fixtures.py` (recommended) | Assert `btc_usdt.json` and `eth_usdt.json` exist under `resources/market_data/` |
| Schema conformance | Same module | Load JSON, map to `MarketData`, assert no mapping errors |
| Candle count | Same module | M15 series length ≥ 30 |
| Order book depth | Same module | ≥ 5 bids and ≥ 5 asks per fixture |
| Price consistency | Same module | `current_price` equals last M15 close; within bid/ask bounds |
| OHLC invariants | Same module | All candles satisfy low/high constraints |
| Decimal encoding | Same module | All Decimal fields are JSON strings |
| README presence | Same module or manual review | `resources/market_data/README.md` exists |

**Coverage expectations:**

- Both fixture files are exercised by automated tests.
- Tests use stdlib `json`, `decimal`, `datetime` and import domain models from `market_data_be.modules.analysis.models` only for type construction and assertions.
- Tests do not require FastAPI, Pydantic, or a provider implementation.
- Domain module source files under `src/modules/` are not modified.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `resources/market_data/` directory at project root |
| REQ-002 | `btc_usdt.json` filename and location |
| REQ-003 | `eth_usdt.json` filename and location |
| REQ-004 | Root JSON object maps to `MarketData` fields |
| REQ-005 | `symbol` values `BTC/USDT` / `ETH/USDT` |
| REQ-006 | `order_book.bids` / `order_book.asks` arrays of `{price, quantity}` strings |
| REQ-007 | `series` includes `timeframe: "15m"` entry |
| REQ-008 | ≥ 30 candles in M15 series |
| REQ-009 | Full `Candle` field set per dataclass |
| REQ-010 | ISO 8601 UTC datetime strings |
| REQ-011 | Decimal fields as JSON strings |
| REQ-012 | ≥ 5 levels per order book side with sorted prices |
| REQ-013 | `current_price` aligned with last close and spread |
| REQ-014 | OHLC invariant enforcement in test assertions |
| REQ-015 | `resources/market_data/README.md` schema documentation |
| REQ-016 | Static files only; no loader/provider in this feature |
| NFR-001 | No changes under `src/modules/` |
| NFR-002 | UTF-8 static JSON committed to repo |
| NFR-003 | Realistic BTC/ETH price magnitudes and volumes |
| NFR-004 | Contiguous 15-minute candle timestamps |
| NFR-005 | English README and spec artifacts |
