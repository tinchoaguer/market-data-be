# Requirements

## Overview

Expose current market data over HTTP by adding a read-only REST endpoint to the existing FastAPI application. The endpoint accepts a trading-pair symbol as a hyphen-separated URL path parameter (for example, `BTC-USDT`), converts it to the internal slash-separated format (`BTC/USDT`), runs the existing `GetMarketData` application use case, and returns a JSON response built from infrastructure-layer DTOs. Domain types (`MarketData`, `OrderBook`, `CandleSeries`, `Candle`, and related models) and application orchestration logic remain unchanged; URL symbol parsing, HTTP serialization, and error mapping are infrastructure concerns only.

## Goals

- Provide a stable HTTP contract for querying the current market data snapshot for a market symbol.
- Use URL-safe hyphen-separated path parameters (`BASE-QUOTE`) while preserving the internal slash-separated symbol convention (`BASE/QUOTE`) used by `GetMarketData` and `MarketDataProvider`.
- Keep FastAPI, Pydantic, and HTTP DTOs confined to `src/market_data_be/infrastructure/http/`.
- Reuse the completed `GetMarketData` use case and `MockMarketDataProvider` without modifying their behavior.
- Return deterministic, testable HTTP status codes for valid requests, client errors, and server failures.
- Support at minimum the existing mock fixture symbols `BTC/USDT` and `ETH/USDT` via URL paths `BTC-USDT` and `ETH-USDT`.
- Align JSON serialization of decimal and datetime fields with the fixture contract in `resources/market_data/README.md` (decimals as strings; datetimes as ISO 8601 UTC).

## Functional Requirements

```text
REQ-001

The system shall expose an HTTP GET endpoint that returns the current market data for a given trading-pair symbol.
```

```text
REQ-002

The system shall accept the market symbol as a hyphen-separated trading pair in the URL path parameter in the form `BASE-QUOTE` (for example, `BTC-USDT`).
```

```text
REQ-003

Before invoking the use case, the system shall validate the URL path symbol format and convert a valid `BASE-QUOTE` parameter to the internal slash-separated form `BASE/QUOTE` (for example, `BTC-USDT` → `BTC/USDT`) consistent with the `MarketDataProvider` contract.
```

```text
REQ-004

When a market data request is received, the system shall invoke the existing `GetMarketData.execute(symbol)` use case with the converted internal slash-separated symbol from the infrastructure route handler.
```

```text
REQ-005

The system shall return HTTP response bodies composed exclusively of infrastructure HTTP DTOs; domain `MarketData` and nested domain types shall not be serialized directly as API response models.
```

```text
REQ-006

When market data retrieval succeeds, the system shall return HTTP 200 with a JSON body containing `symbol`, `current_price`, `order_book`, and `series`.
```

```text
REQ-007

The HTTP response `order_book` shall expose `bids` and `asks` arrays; each level shall expose `price` and `quantity` as JSON strings.
```

```text
REQ-008

The HTTP response `series` shall be an array of candle series objects; each series shall expose `timeframe` (string) and `candles` (array).
```

```text
REQ-009

Each candle in the HTTP response shall expose required fields `start_time`, `end_time`, `open`, `high`, `low`, `close`, and `base_volume`, and may expose optional fields `quote_volume`, `trade_count`, `buy_volume`, and `buy_quote_volume`.
```

```text
REQ-010

Decimal-valued fields in the HTTP response (`current_price`, order-book levels, candle OHLCV and optional volume fields) shall be serialized as JSON strings, not JSON numbers.
```

```text
REQ-011

Candle datetime fields (`start_time`, `end_time`) in the HTTP response shall be serialized as ISO 8601 UTC strings.
```

```text
REQ-012

The system shall map domain `MarketData` output to the HTTP response DTO in the infrastructure layer before returning the response.
```

```text
REQ-013

The `symbol` field in the HTTP 200 response body shall use the internal slash-separated format `BASE/QUOTE` (for example, `BTC/USDT`), matching the domain and application convention.
```

```text
REQ-014

The system shall register the market data route on the FastAPI application created by `create_app()`.
```

```text
REQ-015

The system shall wire default development dependencies for `GetMarketData` (including `MockMarketDataProvider`) during application composition so the endpoint is operational without additional caller setup.
```

```text
REQ-016

When the requested symbol has no available market data, the system shall respond with HTTP 404.
```

```text
REQ-017

When the URL path symbol does not conform to the required hyphen-separated pair format, or contains a slash-separated pair (including URL-encoded slash), the system shall respond with HTTP 422 before invoking the use case.
```

```text
REQ-018

When an unexpected error occurs during request handling that is not a not-found or validation failure defined by this feature, the system shall respond with HTTP 500.
```

```text
REQ-019

The system shall successfully return market data for URL paths `BTC-USDT` and `ETH-USDT`, resolving to internal symbols `BTC/USDT` and `ETH/USDT` using the existing mock market data fixtures.
```

```text
REQ-020

URL symbol validation and conversion shall reuse the existing infrastructure `parse_url_symbol` behavior established by the classification API (hyphen URL param → internal slash symbol).
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/market_data_be/modules/` shall remain free of FastAPI, Pydantic, and other HTTP framework dependencies.
```

```text
NFR-002

The application layer (`src/market_data_be/application/`) shall not import FastAPI or define HTTP DTOs; it continues to expose `GetMarketData` and domain `MarketData` only.
```

```text
NFR-003

HTTP integration tests shall use FastAPI `TestClient` and reside under `src/market_data_be/infrastructure/tests/`.
```

```text
NFR-004

The HTTP layer shall use strict typing on public DTOs, route handlers, and mapper functions; public contracts shall avoid `Any`.
```

```text
NFR-005

The feature shall not modify `GetMarketData` orchestration logic, `MarketDataProvider` port behavior, mock provider implementation, domain market models, or mock fixture file contents.
```

```text
NFR-006

The feature shall not introduce authentication, authorization, WebSocket streaming, or live exchange data retrieval.
```

```text
NFR-007

Paths and package layout shall follow ADR-0001: installable code under `src/market_data_be/`.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-014):** `create_app()` serves a GET market data endpoint discoverable via `TestClient` without additional manual wiring beyond factory instantiation.
- [ ] **AC-002 (REQ-002, REQ-003, REQ-006, REQ-013):** A valid request to `/markets/BTC-USDT/market-data` returns HTTP 200 with JSON containing `symbol` equal to `"BTC/USDT"`, plus `current_price`, `order_book`, and `series` keys.
- [ ] **AC-003 (REQ-007, REQ-008, REQ-009, REQ-010, REQ-011):** Response body includes order-book levels with string `price`/`quantity`, at least one series with `timeframe` and `candles`, required candle fields present, decimal fields as JSON strings, and candle datetimes as ISO 8601 UTC strings.
- [ ] **AC-004 (REQ-005, REQ-012):** Response models are Pydantic types defined under `src/market_data_be/infrastructure/http/`; route handler return type is an HTTP DTO, not domain `MarketData`.
- [ ] **AC-005 (REQ-004, REQ-015):** The route handler delegates to `GetMarketData.execute("BTC/USDT")` (internal slash format) when the URL path parameter is `BTC-USDT`, using dependencies composed with `MockMarketDataProvider`.
- [ ] **AC-006 (REQ-019):** Requests to `/markets/BTC-USDT/market-data` and `/markets/ETH-USDT/market-data` both return HTTP 200 with response `symbol` values `"BTC/USDT"` and `"ETH/USDT"` respectively and non-empty `order_book` / `series`.
- [ ] **AC-007 (REQ-016):** A request for a well-formed but unsupported symbol (for example, `/markets/SOL-USDT/market-data`) returns HTTP 404.
- [ ] **AC-008 (REQ-017, REQ-020):** Requests with invalid symbol formats return HTTP 422, including bare symbol `/markets/BTC/market-data`, slash-separated path `/markets/BTC/USDT/market-data` (wrong path shape), and URL-encoded slash `/markets/BTC%2FUSDT/market-data`.
- [ ] **AC-009 (REQ-018):** A simulated unexpected failure during market data handling returns HTTP 500.
- [ ] **AC-010 (NFR-001, NFR-002):** No new FastAPI or Pydantic imports appear under `src/market_data_be/modules/` or `src/market_data_be/application/`.
- [ ] **AC-011 (NFR-003):** `src/market_data_be/infrastructure/tests/` contains automated tests covering success, not-found, validation, URL-to-internal conversion, and server-error paths for the market data endpoint.
- [ ] **AC-012 (NFR-005, NFR-006):** `GetMarketData`, provider/port modules, domain market models, and fixture JSON files are unchanged by this feature.
