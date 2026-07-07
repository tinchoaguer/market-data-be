# Requirements

## Overview

Provide static JSON fixture files that represent realistic market snapshots for **BTC/USDT** and **ETH/USDT**, structured to deserialize into the `MarketData` domain model (`market_data_be.modules.analysis.models.market.MarketData`). Fixtures live in a dedicated project-level resources directory and are ready for downstream consumers (e.g., the mock market data provider in feature 3) without requiring new domain code or changes to existing analysis modules.

## Goals

- Supply reproducible, version-controlled market data fixtures for local development, integration tests, and API demos.
- Align fixture structure exactly with the frozen `MarketData` dataclass graph (`Candle`, `CandleSeries`, `OrderBook`, `OrderLevel`, `Timeframe`).
- Keep domain bounded contexts pure (stdlib-only); fixtures are infrastructure resources, not domain code.
- Enable future loading via a provider adapter without modifying fixture files when that provider is implemented.

## Functional Requirements

```text
REQ-001

The system shall store mock market data fixtures under a dedicated directory at `resources/market_data/` relative to the project root.
```

```text
REQ-002

The system shall provide a JSON fixture file named `btc_usdt.json` under `resources/market_data/` representing a BTC/USDT market snapshot.
```

```text
REQ-003

The system shall provide a JSON fixture file named `eth_usdt.json` under `resources/market_data/` representing an ETH/USDT market snapshot.
```

```text
REQ-004

Each fixture JSON document shall contain top-level fields that map one-to-one to `MarketData` attributes: `symbol`, `current_price`, `order_book`, and `series`.
```

```text
REQ-005

Each fixture `symbol` field shall use slash-separated pair notation: `BTC/USDT` for `btc_usdt.json` and `ETH/USDT` for `eth_usdt.json`.
```

```text
REQ-006

Each fixture `order_book` shall contain `bids` and `asks` arrays; each element shall map to `OrderLevel` with string-encoded `price` and `quantity` values (Decimal serialization).
```

```text
REQ-007

Each fixture `series` array shall contain at least one `CandleSeries` object with `timeframe` set to the `Timeframe.M15` enum value (`"15m"`) and a `candles` array.
```

```text
REQ-008

Each fixture M15 `candles` array shall contain at least 30 candles so downstream analysis components that require `MIN_KLINES = 30` can operate without insufficient-data fallbacks.
```

```text
REQ-009

Each candle object shall include required fields `start_time`, `end_time`, `open`, `high`, `low`, `close`, and `base_volume`, and may include optional fields `quote_volume`, `trade_count`, `buy_volume`, and `buy_quote_volume` as defined by the `Candle` dataclass.
```

```text
REQ-010

Datetime fields in candles (`start_time`, `end_time`) shall be ISO 8601 strings with UTC timezone (suffix `Z` or explicit `+00:00`).
```

```text
REQ-011

Numeric fields that are `Decimal` in the domain model (`current_price`, candle OHLCV fields, order book levels, optional volume fields) shall be serialized as JSON strings, not JSON numbers, to preserve precision.
```

```text
REQ-012

Each fixture shall include order book depth of at least 5 bid levels and 5 ask levels with monotonically decreasing bid prices and monotonically increasing ask prices relative to the mid price.
```

```text
REQ-013

Each fixture `current_price` shall be consistent with the latest M15 candle `close` price (equal when expressed as `Decimal`) and shall fall within the best bid and best ask spread implied by the order book.
```

```text
REQ-014

Fixture candle OHLC values shall satisfy domain invariants: `low <= open <= high`, `low <= close <= high`, and `low <= high`.
```

```text
REQ-015

The system shall document the JSON field mapping and serialization conventions in `resources/market_data/README.md` so consumers can deserialize fixtures without inferring schema from code.
```

```text
REQ-016

When this feature is complete, fixture files shall be consumable as static resources on disk without requiring new Python loader, provider, or API code in this feature.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/modules/` shall not be modified to introduce JSON parsing, file I/O, or third-party serialization dependencies.
```

```text
NFR-002

Fixture files shall be valid UTF-8 JSON and committed as static artifacts (not generated at runtime).
```

```text
NFR-003

Fixture market values shall be realistic for the symbol (BTC/USDT price magnitude in tens of thousands USD; ETH/USDT in thousands USD) with plausible volumes and spreads, not placeholder constants such as uniform `100` prices across all fields.
```

```text
NFR-004

Fixture timestamps shall form a contiguous M15 sequence (each candle `start_time` equals the previous candle `end_time`) covering at least 30 consecutive 15-minute intervals.
```

```text
NFR-005

Specifications and fixture documentation shall be written in English per project conventions.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001):** Directory `resources/market_data/` exists at the project root.
- [ ] **AC-002 (REQ-002, REQ-005):** `resources/market_data/btc_usdt.json` exists and contains `"symbol": "BTC/USDT"`.
- [ ] **AC-003 (REQ-003, REQ-005):** `resources/market_data/eth_usdt.json` exists and contains `"symbol": "ETH/USDT"`.
- [ ] **AC-004 (REQ-004, REQ-006, REQ-007, REQ-009, REQ-010, REQ-011):** Both JSON documents deserialize to `MarketData` instances when mapped per `resources/market_data/README.md` without missing required fields or type coercion errors.
- [ ] **AC-005 (REQ-008, NFR-004):** Each fixture includes an M15 `CandleSeries` with at least 30 contiguous candles.
- [ ] **AC-006 (REQ-012, REQ-013, NFR-003):** Each fixture order book has ≥5 bids and ≥5 asks; `current_price` aligns with the last M15 close and lies inside the best bid/ask range.
- [ ] **AC-007 (REQ-014):** All candles in both fixtures satisfy OHLC invariant checks.
- [ ] **AC-008 (REQ-015):** `resources/market_data/README.md` documents the JSON schema, filename convention, and Decimal/datetime serialization rules.
- [ ] **AC-009 (REQ-016, NFR-001):** No new provider, loader, or domain module code is introduced; only resource files and schema documentation are added under `resources/market_data/` (plus specification-mandated conformance tests).
