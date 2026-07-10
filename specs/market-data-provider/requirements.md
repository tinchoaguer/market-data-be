# Requirements

## Overview

Introduce a `MarketDataProvider` port and a `MockMarketDataProvider` infrastructure adapter so the application layer can obtain `MarketData` domain instances without coupling to a specific data source. The mock adapter loads static JSON fixtures from `resources/market_data/` per the schema contract established in feature 2. Domain bounded contexts (`src/modules/analysis/`, `src/modules/classification/`) remain stdlib-only and do not participate in retrieval; they continue to accept `MarketData` as input only.

## Goals

- Decouple market data retrieval from application orchestration via a typed port (Protocol).
- Deliver a mock JSON-file adapter for local development and tests using existing fixtures (`btc_usdt.json`, `eth_usdt.json`).
- Centralize JSON-to-`MarketData` deserialization in infrastructure so fixture conformance tests and the mock provider share one mapping implementation.
- Enable future adapters (e.g., live exchange APIs) without modifying application or domain code.
- Demonstrate port-based dependency through a minimal application use case (not a full analysis pipeline).

## Functional Requirements

```text
REQ-001

The system shall define a `MarketDataProvider` port in the application layer that specifies the contract for retrieving `MarketData` by trading symbol.
```

```text
REQ-002

The `MarketDataProvider` port shall expose a single retrieval operation that accepts a `symbol` string (slash-separated pair notation, e.g., `BTC/USDT`) and returns a `MarketData` instance from `market_data_be.modules.analysis.models.market`.
```

```text
REQ-003

The system shall implement a `MockMarketDataProvider` adapter in the infrastructure layer that satisfies the `MarketDataProvider` port.
```

```text
REQ-004

The `MockMarketDataProvider` shall resolve a requested symbol to a fixture filename using the convention documented in `resources/market_data/README.md`: lowercase base and quote separated by underscore with a `.json` extension (e.g., `BTC/USDT` → `btc_usdt.json`).
```

```text
REQ-005

The `MockMarketDataProvider` shall load fixture files from `{PROJECT_ROOT}/resources/market_data/` using UTF-8 encoding and stdlib `json` parsing.
```

```text
REQ-006

The system shall provide a shared JSON-to-`MarketData` deserializer in the infrastructure layer that maps fixture documents to domain `MarketData` objects according to the field contract in `resources/market_data/README.md`.
```

```text
REQ-007

The deserializer shall map all required `MarketData` fields (`symbol`, `current_price`, `order_book`, `series`) and nested types (`OrderBook`, `OrderLevel`, `CandleSeries`, `Candle`, `Timeframe`) without modifying domain module source code.
```

```text
REQ-008

The `MockMarketDataProvider` shall use the shared deserializer to produce `MarketData` instances from loaded JSON payloads.
```

```text
REQ-009

The system shall provide a minimal application use case (or equivalent orchestration entry point) that depends on the `MarketDataProvider` port via constructor injection and delegates retrieval to the injected provider without importing infrastructure adapter types.
```

```text
REQ-010

When the `MockMarketDataProvider` is configured with the default fixtures directory, a request for symbol `BTC/USDT` shall return `MarketData` whose `symbol` field equals `BTC/USDT`.
```

```text
REQ-011

When the `MockMarketDataProvider` is configured with the default fixtures directory, a request for symbol `ETH/USDT` shall return `MarketData` whose `symbol` field equals `ETH/USDT`.
```

```text
REQ-012

When a requested symbol cannot be resolved to a fixture file (unsupported symbol format, missing file, or symbol with no corresponding fixture), the provider shall raise a dedicated, distinguishable error indicating market data was not found for that symbol.
```

```text
REQ-013

When a fixture file exists but its JSON payload cannot be deserialized into `MarketData` (malformed JSON, missing required fields, or invalid enum values), the provider shall raise a dedicated, distinguishable error indicating deserialization failure.
```

```text
REQ-014

Conformance tests in `resources/tests/test_market_data_fixtures.py` shall reuse the shared infrastructure deserializer instead of maintaining a duplicate `market_data_from_dict` implementation.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/modules/analysis/` and `src/modules/classification/` shall not import the `MarketDataProvider` port, infrastructure adapters, or JSON deserialization code.
```

```text
NFR-002

The `MarketDataProvider` port public contract shall use strict typing with no `Any` in method signatures or return types.
```

```text
NFR-003

Infrastructure deserialization code may use stdlib modules (`json`, `decimal`, `datetime`, `pathlib`) and import domain models for construction only; it shall not introduce FastAPI, Pydantic, SQLAlchemy, or other third-party serialization frameworks.
```

```text
NFR-004

New `MarketDataProvider` adapter implementations shall be addable under `src/infrastructure/` without modifying application use-case logic or domain module code.
```

```text
NFR-005

Unit tests for the mock provider, deserializer, and application use case shall reside under the infrastructure and application test directories respectively and run with pytest.
```

```text
NFR-006

Naming shall follow project conventions: responsibility-driven names; forbidden suffixes include Manager, Helper, Processor, Engine, and Utils.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-002):** A `MarketDataProvider` Protocol exists under `src/application/` with a typed retrieval method returning `MarketData`.
- [ ] **AC-002 (REQ-003, REQ-005, REQ-008):** `MockMarketDataProvider` in `src/infrastructure/` implements the port and loads JSON from `resources/market_data/`.
- [ ] **AC-003 (REQ-004, REQ-010, REQ-011):** `MockMarketDataProvider.get_market_data("BTC/USDT")` and `get_market_data("ETH/USDT")` return valid `MarketData` instances matching fixture symbols.
- [ ] **AC-004 (REQ-006, REQ-007, REQ-014):** Shared deserializer in infrastructure maps fixture JSON to `MarketData`; `resources/tests/test_market_data_fixtures.py` imports it (no duplicate mapping logic).
- [ ] **AC-005 (REQ-009, NFR-001):** An application use case accepts `MarketDataProvider` via injection and contains no infrastructure imports; domain modules contain no provider or deserializer imports.
- [ ] **AC-006 (REQ-012, REQ-013):** Unit tests verify not-found and deserialization-error paths raise the dedicated error types.
- [ ] **AC-007 (NFR-004):** A second stub/fake `MarketDataProvider` used in application use-case tests demonstrates substitution without changing use-case source.
- [ ] **AC-008 (NFR-002, NFR-003, NFR-006):** Public port and adapter APIs use strict types; domain modules remain stdlib-only; naming avoids forbidden suffixes.
