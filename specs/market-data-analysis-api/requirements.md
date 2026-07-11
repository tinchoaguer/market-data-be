# Requirements

## Overview

Expose current market data analysis over HTTP by adding a read-only REST endpoint to the existing FastAPI application. The endpoint accepts a trading-pair symbol as a hyphen-separated URL path parameter (for example, `BTC-USDT`), converts it to the internal slash-separated format (`BTC/USDT`), runs an application use case that retrieves market data and invokes `MarketAnalysisEngine.analyze`, and returns a JSON response built from infrastructure-layer DTOs. Domain types (`AnalysisResult`, assessment models, and nested analysis models) are not serialized directly; URL symbol parsing, HTTP serialization, and error mapping are infrastructure concerns only.

## Goals

- Provide a stable HTTP contract for querying the current market analysis result for a market symbol.
- Use URL-safe hyphen-separated path parameters (`BASE-QUOTE`) while preserving the internal slash-separated symbol convention (`BASE/QUOTE`) used by `MarketDataProvider` and the analysis engine.
- Keep FastAPI, Pydantic, and HTTP DTOs confined to `src/market_data_be/infrastructure/http/`.
- Introduce a thin application use case that orchestrates market data retrieval and analysis without modifying `MarketAnalysisEngine` algorithms.
- Return deterministic, testable HTTP status codes for valid requests, client errors, and server failures.
- Support at minimum the existing mock fixture symbols `BTC/USDT` and `ETH/USDT` via URL paths `BTC-USDT` and `ETH-USDT`.
- Reuse the existing infrastructure `parse_url_symbol` behavior established by prior API features.

## Functional Requirements

```text
REQ-001

The system shall expose an HTTP GET endpoint that returns the current market data analysis for a given trading-pair symbol.
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

The system shall provide an application use case that retrieves `MarketData` for the given symbol via `MarketDataProvider` and invokes `MarketAnalysisEngine.analyze` to produce an `AnalysisResult`.
```

```text
REQ-005

When a market analysis request is received, the system shall invoke the analysis use case `execute(symbol)` with the converted internal slash-separated symbol from the infrastructure route handler.
```

```text
REQ-006

The system shall return HTTP response bodies composed exclusively of infrastructure HTTP DTOs; domain `AnalysisResult` and nested analysis domain types shall not be serialized directly as API response models.
```

```text
REQ-007

When market analysis succeeds, the system shall return HTTP 200 with a JSON body containing `symbol`, `regime`, `risk`, `economic`, `exposure`, and `catalog`.
```

```text
REQ-008

The HTTP response assessment objects (`regime`, `risk`, `economic`, `exposure`) and `catalog` shall expose the public fields of the corresponding analysis domain types, serialized for JSON (enums as strings; boolean and numeric scalars as JSON booleans and numbers; nested collections as JSON arrays/objects).
```

```text
REQ-009

The system shall map domain `AnalysisResult` output to the HTTP response DTO in the infrastructure layer before returning the response.
```

```text
REQ-010

The `symbol` field in the HTTP 200 response body shall use the internal slash-separated format `BASE/QUOTE` (for example, `BTC/USDT`), matching the domain and application convention.
```

```text
REQ-011

The system shall register the market analysis route on the FastAPI application created by `create_app()`.
```

```text
REQ-012

The system shall wire default development dependencies for the analysis use case (including `MockMarketDataProvider` and `MarketAnalysisEngine`) during application composition so the endpoint is operational without additional caller setup.
```

```text
REQ-013

When the requested symbol has no available market data, the system shall respond with HTTP 404.
```

```text
REQ-014

When the URL path symbol does not conform to the required hyphen-separated pair format, or contains a slash-separated pair (including URL-encoded slash), the system shall respond with HTTP 422 before invoking the use case.
```

```text
REQ-015

When an unexpected error occurs during request handling that is not a not-found or validation failure defined by this feature, the system shall respond with HTTP 500.
```

```text
REQ-016

The system shall successfully return market analysis results for URL paths `BTC-USDT` and `ETH-USDT`, resolving to internal symbols `BTC/USDT` and `ETH/USDT` using the existing mock market data fixtures.
```

```text
REQ-017

URL symbol validation and conversion shall reuse the existing infrastructure `parse_url_symbol` behavior established by prior API features (hyphen URL param → internal slash symbol).
```

```text
REQ-018

The analysis use case shall invoke `MarketAnalysisEngine.analyze` with the retrieved `MarketData` and without supplying an explicit portfolio state, so the engine applies its existing default portfolio state behavior.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/market_data_be/modules/` shall remain free of FastAPI, Pydantic, and other HTTP framework dependencies.
```

```text
NFR-002

The application layer (`src/market_data_be/application/`) shall not import FastAPI or define HTTP DTOs; it exposes the analysis use case and returns domain `AnalysisResult` only.
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

The feature shall not modify `MarketAnalysisEngine` analyzer or synthesis algorithms, `MarketDataProvider` port behavior, mock provider implementation, domain analysis model definitions, or mock fixture file contents.
```

```text
NFR-006

The feature shall not introduce authentication, authorization, WebSocket streaming, live exchange data retrieval, or portfolio-state request parameters.
```

```text
NFR-007

Paths and package layout shall follow ADR-0001: installable code under `src/market_data_be/`.
```

```text
NFR-008

Application use case unit tests shall reside under `src/market_data_be/application/tests/` and run with pytest.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-011):** `create_app()` serves a GET market analysis endpoint discoverable via `TestClient` without additional manual wiring beyond factory instantiation.
- [ ] **AC-002 (REQ-002, REQ-003, REQ-007, REQ-010):** A valid request to `/markets/BTC-USDT/analysis` returns HTTP 200 with JSON containing `symbol` equal to `"BTC/USDT"`, plus `regime`, `risk`, `economic`, `exposure`, and `catalog` keys.
- [ ] **AC-003 (REQ-008):** Response body assessment and catalog objects expose domain public fields with enums as strings and scalar types matching JSON boolean/number/string conventions defined in the design.
- [ ] **AC-004 (REQ-006, REQ-009):** Response models are Pydantic types defined under `src/market_data_be/infrastructure/http/`; route handler return type is an HTTP DTO, not domain `AnalysisResult`.
- [ ] **AC-005 (REQ-004, REQ-005, REQ-012, REQ-018):** The route handler delegates to the analysis use case `execute("BTC/USDT")` (internal slash format) when the URL path parameter is `BTC-USDT`, using dependencies composed with `MockMarketDataProvider` and `MarketAnalysisEngine`.
- [ ] **AC-006 (REQ-016):** Requests to `/markets/BTC-USDT/analysis` and `/markets/ETH-USDT/analysis` both return HTTP 200 with response `symbol` values `"BTC/USDT"` and `"ETH/USDT"` respectively and present assessment objects for all four domains.
- [ ] **AC-007 (REQ-013):** A request for a well-formed but unsupported symbol (for example, `/markets/SOL-USDT/analysis`) returns HTTP 404.
- [ ] **AC-008 (REQ-014, REQ-017):** Requests with invalid symbol formats return HTTP 422, including bare symbol `/markets/BTC/analysis`, slash-separated path `/markets/BTC/USDT/analysis` (wrong path shape), and URL-encoded slash `/markets/BTC%2FUSDT/analysis`.
- [ ] **AC-009 (REQ-015):** A simulated unexpected failure during analysis handling returns HTTP 500.
- [ ] **AC-010 (NFR-001, NFR-002):** No new FastAPI or Pydantic imports appear under `src/market_data_be/modules/`; application layer has no FastAPI/Pydantic HTTP DTO imports.
- [ ] **AC-011 (NFR-003, NFR-008):** Automated tests cover the analysis use case and HTTP success, not-found, validation, URL-to-internal conversion, and server-error paths for the analysis endpoint.
- [ ] **AC-012 (NFR-005, NFR-006):** `MarketAnalysisEngine` algorithms, provider/port modules, domain analysis model definitions, and fixture JSON files are unchanged by this feature; no auth, WebSocket, live provider, or portfolio query parameters are introduced.
