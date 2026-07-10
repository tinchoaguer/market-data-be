# Requirements

## Amendments (2026-07-09)

> See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md).

- Paths `src/infrastructure/`, `src/application/`, `src/modules/` → prefix with `src/market_data_be/`.
- Domain pipeline output is `ClassificationResult`, not application `MarketClassification`.
- `ClassifyMarket` returns `ClassificationResult`; HTTP mapper converts it to `MarketClassificationResponse`.
- Composition wires `MarketClassificationEngine()`, not four individual classifiers.

---

## Overview

Expose market classification results over HTTP by adding a read-only REST endpoint to the existing FastAPI application. The endpoint accepts a trading-pair symbol as a hyphen-separated URL path parameter (for example, `BTC-USDT`), converts it to the internal slash-separated format (`BTC/USDT`), runs the existing `ClassifyMarket` application use case, and returns a JSON response built from infrastructure-layer DTOs. Domain types (`ClassificationSignal`, `MarketClassification`) and application orchestration logic remain unchanged; URL symbol parsing, HTTP serialization, and error mapping are infrastructure concerns only.

## Goals

- Provide a stable HTTP contract for querying current classification signals for a market symbol.
- Use URL-safe hyphen-separated path parameters (`BASE-QUOTE`) while preserving the internal slash-separated symbol convention (`BASE/QUOTE`) used by `ClassifyMarket` and `MarketDataProvider`.
- Keep FastAPI, Pydantic, and HTTP DTOs confined to `src/infrastructure/http/`.
- Reuse the completed analysis-to-classification pipeline (`ClassifyMarket`) without modifying its behavior.
- Return deterministic, testable HTTP status codes for valid requests, client errors, and server failures.
- Support at minimum the existing mock fixture symbols `BTC/USDT` and `ETH/USDT` via URL paths `BTC-USDT` and `ETH-USDT`.

## Functional Requirements

```text
REQ-001

The system shall expose an HTTP GET endpoint that returns the current market classification for a given trading-pair symbol.
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

When a classification request is received, the system shall invoke the existing `ClassifyMarket.execute(symbol)` use case with the converted internal slash-separated symbol from the infrastructure route handler.
```

```text
REQ-005

The system shall return HTTP response bodies composed exclusively of infrastructure HTTP DTOs; domain `ClassificationSignal` and application `MarketClassification` types shall not be serialized directly as API response models.
```

```text
REQ-006

When classification succeeds, the system shall return HTTP 200 with a JSON body containing the resolved symbol and four per-domain signal collections named `regime`, `risk`, `economic`, and `exposure`.
```

```text
REQ-007

Each signal in the HTTP response shall expose the fields `source` (string), `score` (number), and `reason` (string), corresponding to the underlying classification signal values.
```

```text
REQ-008

The system shall map `MarketClassification` application output to the HTTP response DTO in the infrastructure layer before returning the response.
```

```text
REQ-009

The `symbol` field in the HTTP 200 response body shall use the internal slash-separated format `BASE/QUOTE` (for example, `BTC/USDT`), matching the domain and application convention.
```

```text
REQ-010

The system shall register the classification route on the FastAPI application created by `create_app()`.
```

```text
REQ-011

The system shall wire default development dependencies for `ClassifyMarket` (including `MockMarketDataProvider`, `MarketAnalysisEngine`, and the four domain classifiers) during application composition so the endpoint is operational without additional caller setup.
```

```text
REQ-012

When the requested symbol has no available market data, the system shall respond with HTTP 404.
```

```text
REQ-013

When the URL path symbol does not conform to the required hyphen-separated pair format, or contains a slash-separated pair (including URL-encoded slash), the system shall respond with HTTP 422 before invoking the use case.
```

```text
REQ-014

When an unexpected error occurs during request handling that is not a not-found or validation failure defined by this feature, the system shall respond with HTTP 500.
```

```text
REQ-015

The system shall successfully return classification results for URL paths `BTC-USDT` and `ETH-USDT`, resolving to internal symbols `BTC/USDT` and `ETH/USDT` using the existing mock market data fixtures.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/modules/` shall remain free of FastAPI, Pydantic, and other HTTP framework dependencies.
```

```text
NFR-002

The application layer (`src/application/`) shall not import FastAPI or define HTTP DTOs; it continues to expose `ClassifyMarket` and `MarketClassification` only.
```

```text
NFR-003

HTTP integration tests shall use FastAPI `TestClient` and reside under `src/infrastructure/tests/`.
```

```text
NFR-004

The HTTP layer shall use strict typing on public DTOs, route handlers, and mapper functions; public contracts shall avoid `Any`.
```

```text
NFR-005

The feature shall not modify `ClassifyMarket` orchestration logic, domain classifier implementations, or mock fixture file contents.
```

```text
NFR-006

The feature shall not introduce authentication, authorization, WebSocket streaming, or live exchange data retrieval.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-010):** `create_app()` serves a GET classification endpoint discoverable via `TestClient` without additional manual wiring beyond factory instantiation.
- [ ] **AC-002 (REQ-002, REQ-003, REQ-006, REQ-009):** A valid request to `/markets/BTC-USDT/classification` returns HTTP 200 with JSON containing `symbol` equal to `"BTC/USDT"`, plus `regime`, `risk`, `economic`, and `exposure` keys.
- [ ] **AC-003 (REQ-007):** Each signal object in the response contains `source`, `score`, and `reason` with JSON types string, number, and string respectively.
- [ ] **AC-004 (REQ-005, REQ-008):** Response models are Pydantic types defined under `src/infrastructure/http/`; route handler return type is an HTTP DTO, not `MarketClassification` or `ClassificationSignal`.
- [ ] **AC-005 (REQ-004, REQ-011):** The route handler delegates to `ClassifyMarket.execute("BTC/USDT")` (internal slash format) when the URL path parameter is `BTC-USDT`, using dependencies composed with `MockMarketDataProvider` and real analysis/classification components.
- [ ] **AC-006 (REQ-015):** Requests to `/markets/BTC-USDT/classification` and `/markets/ETH-USDT/classification` both return HTTP 200 with non-empty signal arrays in all four domains and response `symbol` values `"BTC/USDT"` and `"ETH/USDT"` respectively.
- [ ] **AC-007 (REQ-012):** A request for a well-formed but unsupported symbol (for example, `/markets/SOL-USDT/classification`) returns HTTP 404.
- [ ] **AC-008 (REQ-013):** Requests with invalid symbol formats return HTTP 422, including bare symbol `/markets/BTC/classification`, slash-separated path `/markets/BTC/USDT/classification` (wrong path shape), and URL-encoded slash `/markets/BTC%2FUSDT/classification`.
- [ ] **AC-009 (REQ-014):** A simulated unexpected failure during classification handling returns HTTP 500.
- [ ] **AC-010 (NFR-001, NFR-002):** No new FastAPI or Pydantic imports appear under `src/modules/` or `src/application/`.
- [ ] **AC-011 (NFR-003):** `src/infrastructure/tests/` contains automated tests covering success, not-found, validation, URL-to-internal conversion, and server-error paths.
- [ ] **AC-012 (NFR-005, NFR-006):** `ClassifyMarket`, domain classifiers, and fixture JSON files are unchanged by this feature.
