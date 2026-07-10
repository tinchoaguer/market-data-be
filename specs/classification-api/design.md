# Design

## Amendments (2026-07-09)

> Supersedes outdated paths and types in this document. See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md) and [architecture.md](../../knowledge/architecture.md).

| Spec reference | Current code |
|----------------|--------------|
| `src/application/`, `src/modules/`, `src/infrastructure/` | `src/market_data_be/application/`, `.../modules/`, `.../infrastructure/` |
| `MarketClassification` (application output) | `ClassificationResult` in `modules/classification/models/` |
| Four classifiers injected into `ClassifyMarket` | `MarketClassificationEngine` facade injected into `ClassifyMarket` |
| `application/models/market_classification.py` | **Removed** — output owned by classification domain |

**Current pipeline:** `ClassifyMarket` → `MarketAnalysisEngine.analyze()` → `to_classification_inputs()` → `MarketClassificationEngine.classify()` → `ClassificationResult`.

HTTP feature maps `ClassificationResult` → `MarketClassificationResponse` (DTO name unchanged).

---

## Overview

Add a classification HTTP route under `src/infrastructure/http/` that accepts a hyphen-separated market symbol URL path parameter, validates and converts it to the internal slash-separated format, invokes the existing `ClassifyMarket` use case, maps `MarketClassification` to Pydantic response DTOs, and translates infrastructure errors into HTTP status codes. Introduce a small composition module that wires default development dependencies (`MockMarketDataProvider`, real `MarketAnalysisEngine`, real classifiers) and register the route in `create_app()`. Domain and application layers are consumers only; no behavioral changes to the classification pipeline.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/modules/analysis/` | Unchanged; consumed via `MarketAnalysisEngine` |
| Classification domain | `src/modules/classification/` | Unchanged; consumed via classifier instances |
| Application | `src/application/` | `ClassifyMarket` invoked by infrastructure with slash-separated symbol; **no changes** |
| Infrastructure — market data | `src/infrastructure/market_data/` | `MockMarketDataProvider`, error types reused; **no changes** |
| Infrastructure — HTTP | `src/infrastructure/http/` | Route, DTOs, mapper, URL symbol parsing, composition, exception mapping |

### New components

```
src/infrastructure/http/
├── app.py                              # MODIFY: register classification router + exception handlers
├── composition.py                      # NEW: build ClassifyMarket with default dev wiring
├── dtos/
│   ├── __init__.py
│   └── classification.py               # NEW: Pydantic response DTOs
├── mappers/
│   ├── __init__.py
│   └── classification.py               # NEW: MarketClassification → response DTO
├── routes/
│   └── classification.py               # NEW: GET classification endpoint
└── validation/
    ├── __init__.py
    └── symbol.py                       # NEW: hyphen URL param → internal slash symbol

src/infrastructure/tests/
└── test_classification_route.py          # NEW: TestClient integration tests
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| DTOs in `infrastructure/http/dtos/` | Keeps serialization contracts out of application and domain layers | REQ-005, NFR-002 |
| Mapper in `infrastructure/http/mappers/` | Translation from application output to HTTP contract is an adapter concern | REQ-008 |
| Composition in `infrastructure/http/composition.py` | Centralizes default dependency wiring without polluting `app.py` or application code | REQ-011 |
| URL symbol parsing in infrastructure | Enforces HTTP 422 for malformed path params and converts valid `BASE-QUOTE` to internal `BASE/QUOTE` before use case invocation | REQ-003, REQ-013 |
| Route invokes use case only | Application orchestration remains in `ClassifyMarket`; route is a thin adapter | REQ-004, NFR-005 |
| Response `symbol` uses slash format | Aligns JSON body with domain/application convention while URL uses hyphen format | REQ-009 |

### Out of scope (explicit)

- Authentication and authorization
- Live exchange adapters
- Modifications to `ClassifyMarket`, classifiers, or analysis engine logic
- WebSocket or streaming endpoints
- Changes to `resources/market_data/*.json` fixture content
- Changes to `symbol_to_fixture_filename` in `symbol_resolver.py` (continues to accept slash-separated symbols only)

## Data Flow

### Successful classification request

```
Client
  │
  │  GET /markets/BTC-USDT/classification
  ▼
FastAPI app (create_app)
  │
  ▼
classification router
  │
  ├─► parse_url_symbol("BTC-USDT")  ──► ValueError → HTTP 422
  │         │
  │         └─► returns internal "BTC/USDT"
  │
  ├─► ClassifyMarket.execute("BTC/USDT")
  │         │
  │         ├─► MockMarketDataProvider.get_market_data("BTC/USDT")
  │         ├─► MarketAnalysisEngine.analyze(...)
  │         └─► four classifiers → MarketClassification
  │
  ├─► map_market_classification_to_response(classification)
  │         │
  │         └─► response.symbol = "BTC/USDT"  (slash format in JSON body)
  │
  ▼
HTTP 200 + MarketClassificationResponse JSON
```

### Error paths

```
Invalid URL symbol format (e.g. "BTC", "BTC/USDT", "BTC-USDT-EXTRA")
  → parse_url_symbol raises ValueError
  → route/exception handler → HTTP 422

Symbol not found (e.g. URL "SOL-USDT" → internal "SOL/USDT")
  → ClassifyMarket → MockMarketDataProvider
  → MarketDataNotFoundError
  → exception handler → HTTP 404

Corrupt fixture / deserialization failure
  → MarketDataDeserializationError
  → exception handler → HTTP 500

Any other unhandled Exception
  → exception handler → HTTP 500
```

## Interfaces

### HTTP: `GET /markets/{symbol}/classification`

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path pattern | `/markets/{symbol}/classification` |
| Path parameter `symbol` | Hyphen-separated trading pair `BASE-QUOTE` (for example, `BTC-USDT`); standard FastAPI path segment — no `{symbol:path}` catch-all |
| Auth | None |
| Success status | `200` |
| Response `Content-Type` | `application/json` |
| Router tag | `classification` |

**Example request:**

```http
GET /markets/BTC-USDT/classification HTTP/1.1
Host: localhost:8000
```

**Example success response (HTTP 200):**

```json
{
  "symbol": "BTC/USDT",
  "regime": [
    { "source": "regime", "score": 0.4, "reason": "trend_up" }
  ],
  "risk": [
    { "source": "risk", "score": 0.0, "reason": "example" }
  ],
  "economic": [
    { "source": "economic", "score": 0.0, "reason": "example" }
  ],
  "exposure": [
    { "source": "exposure", "score": 0.0, "reason": "example" }
  ]
}
```

The response `symbol` field uses internal slash-separated format (`BTC/USDT`). The request URL uses hyphen-separated format (`BTC-USDT`). Signal `score` and `reason` values are determined by the existing classifiers and fixtures; tests assert structure and non-emptiness, not fixed score literals unless derived from stable fixture outcomes.

### HTTP error responses

All error responses use FastAPI's default JSON error shape:

```json
{ "detail": "<human-readable message>" }
```

| Condition | HTTP status | Trigger |
|-----------|-------------|---------|
| Malformed URL symbol format | `422` | `parse_url_symbol` raises `ValueError` |
| Market data not found | `404` | `MarketDataNotFoundError` propagated from provider via use case |
| Deserialization / unexpected failure | `500` | `MarketDataDeserializationError` or any other unhandled `Exception` |

### URL symbol parsing and conversion

**Location:** `src/infrastructure/http/validation/symbol.py`

```python
def parse_url_symbol(url_symbol: str) -> str:
    """Validate BASE-QUOTE URL path param and return internal BASE/QUOTE symbol.

    Raises ValueError for invalid format.
    """
    ...
```

**Contract:**

| Input (URL path param) | Result |
|------------------------|--------|
| `BTC-USDT` | Returns internal `BTC/USDT` |
| `btc-usdt` | Returns internal `BTC/USDT` (uppercase base and quote segments) |
| `ETH-USDT` | Returns internal `ETH/USDT` |
| `BTC` | Invalid; `ValueError` (bare symbol, missing quote) |
| `BTC/USDT` | Invalid; `ValueError` (slash-separated, not allowed in URL param) |
| `BTC%2FUSDT` (decoded to `BTC/USDT`) | Invalid; `ValueError` |
| `BTC-USDT-EXTRA` | Invalid; `ValueError` (more than one hyphen separator) |
| Empty or whitespace-only segment | Invalid; `ValueError` |

**Parsing rules:**

1. Trim outer whitespace on the full `url_symbol`.
2. Reject if `/` is present anywhere (slash-separated or URL-decoded slash in a single segment).
3. Split on exactly one `-` separator into `base` and `quote`; reject if split yields other than two non-empty segments.
4. Uppercase `base` and `quote`.
5. Return `{BASE}/{QUOTE}` as the internal symbol passed to `ClassifyMarket.execute()` and `MarketDataProvider`.

This conversion is the sole responsibility of the HTTP validation layer. `ClassifyMarket`, `MarketDataProvider`, and `symbol_to_fixture_filename` continue to operate on slash-separated symbols unchanged.

### HTTP response DTOs

**Location:** `src/infrastructure/http/dtos/classification.py`

```python
from pydantic import BaseModel


class ClassificationSignalResponse(BaseModel):
    source: str
    score: float
    reason: str


class MarketClassificationResponse(BaseModel):
    symbol: str
    regime: list[ClassificationSignalResponse]
    risk: list[ClassificationSignalResponse]
    economic: list[ClassificationSignalResponse]
    exposure: list[ClassificationSignalResponse]
```

| Field | JSON type | Source |
|-------|-----------|--------|
| `symbol` | string | `MarketClassification.symbol` (slash-separated, e.g. `BTC/USDT`) |
| `regime` | array | `MarketClassification.regime` mapped element-wise |
| `risk` | array | `MarketClassification.risk` mapped element-wise |
| `economic` | array | `MarketClassification.economic` mapped element-wise |
| `exposure` | array | `MarketClassification.exposure` mapped element-wise |
| `source` | string | `ClassificationSignal.source` |
| `score` | number | `ClassificationSignal.score` |
| `reason` | string | `ClassificationSignal.reason` |

`response_model=MarketClassificationResponse` on the route handler enforces the outward contract.

### Infrastructure mapper

**Location:** `src/infrastructure/http/mappers/classification.py`

```python
def map_market_classification_to_response(
    classification: MarketClassification,
) -> MarketClassificationResponse:
    ...
```

| Input | Output |
|-------|--------|
| `MarketClassification` (application dataclass) | `MarketClassificationResponse` (Pydantic) |

Maps each `tuple[ClassificationSignal, ...]` to a `list[ClassificationSignalResponse]` preserving order. Passes through `classification.symbol` unchanged (already slash-separated from the pipeline). Does not expose domain or application types on the HTTP boundary.

### Composition / dependency wiring

**Location:** `src/infrastructure/http/composition.py`

```python
def build_classify_market() -> ClassifyMarket:
    return ClassifyMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
        regime_classifier=RegimeClassifier(),
        risk_classifier=RiskClassifier(),
        economic_classifier=EconomicClassifier(),
        exposure_classifier=ExposureClassifier(),
    )
```

| Dependency | Implementation | Notes |
|------------|----------------|-------|
| `provider` | `MockMarketDataProvider()` | Default fixtures directory |
| `engine` | `MarketAnalysisEngine()` | Real analysis pipeline |
| Classifiers | Real domain classifier classes | No stubs in production wiring |

**Route dependency access:** expose a FastAPI dependency callable (for example, `get_classify_market()`) that returns the wired `ClassifyMarket` instance. For this feature, instantiate once per app via `create_app()` (module-level or `app.state`) rather than per-request construction.

### Classification route handler

**Location:** `src/infrastructure/http/routes/classification.py`

```python
router = APIRouter(tags=["classification"])


@router.get(
    "/markets/{symbol}/classification",
    response_model=MarketClassificationResponse,
)
def get_market_classification(
    symbol: str,
    classify_market: ClassifyMarket = Depends(get_classify_market),
) -> MarketClassificationResponse:
    internal_symbol = parse_url_symbol(symbol)
    classification = classify_market.execute(internal_symbol)
    return map_market_classification_to_response(classification)
```

The handler shall not return `MarketClassification` directly. The path uses a standard `{symbol}` segment (not `{symbol:path}`).

### Application factory changes

**Location:** `src/infrastructure/http/app.py`

`create_app()` shall:

1. Instantiate `ClassifyMarket` via `build_classify_market()` and store on `app.state.classify_market` (or equivalent single-instance holder).
2. Register `classification` router.
3. Register exception handlers:
   - `MarketDataNotFoundError` → 404 with `detail` including the symbol
   - `MarketDataDeserializationError` → 500 with generic detail (do not leak internal exception strings to clients in production responses; tests may assert status only)
   - `ValueError` raised from `parse_url_symbol` in the route → 422 (handler scoped to route-level catch or dedicated validation exception type to avoid swallowing unrelated `ValueError` from the pipeline)

**Pipeline `ValueError` policy:** `ValueError` raised inside `ClassifyMarket` or domain code (for example, unknown regime) is not a client validation error; it shall surface as HTTP 500 via the generic exception handler. Only URL symbol-format validation failures map to 422.

## Data Model

### HTTP outward schema

```
MarketClassificationResponse
├── symbol: str                    # slash-separated (e.g. "BTC/USDT")
├── regime: ClassificationSignalResponse[]
├── risk: ClassificationSignalResponse[]
├── economic: ClassificationSignalResponse[]
└── exposure: ClassificationSignalResponse[]

ClassificationSignalResponse
├── source: str
├── score: float
└── reason: str
```

### Internal types (unchanged, not exposed on wire)

```
MarketClassification (application)
├── symbol: str                    # slash-separated (e.g. "BTC/USDT")
├── regime: tuple[ClassificationSignal, ...]
├── risk: tuple[ClassificationSignal, ...]
├── economic: tuple[ClassificationSignal, ...]
└── exposure: tuple[ClassificationSignal, ...]

ClassificationSignal (domain)
├── source: str
├── score: float
└── reason: str
```

### Symbol format boundary

| Context | Format | Example |
|---------|--------|---------|
| URL path parameter | Hyphen-separated `BASE-QUOTE` | `BTC-USDT` |
| Use case / provider input | Slash-separated `BASE/QUOTE` | `BTC/USDT` |
| JSON response `symbol` field | Slash-separated `BASE/QUOTE` | `BTC/USDT` |
| Fixture filename resolution | Via `symbol_to_fixture_filename` on slash symbol | `btc_usdt.json` |

No persistence or state transitions; each request is computed on demand.

## Error Handling

| Scenario | Component | HTTP | Response `detail` (minimum) |
|----------|-----------|------|-----------------------------|
| Missing `-` or multiple `-` segments | `parse_url_symbol` | 422 | Indicates invalid symbol format |
| Slash present in path param | `parse_url_symbol` | 422 | Indicates invalid symbol format |
| Empty base or quote | `parse_url_symbol` | 422 | Indicates invalid symbol format |
| Valid format, no fixture | `MockMarketDataProvider` → `MarketDataNotFoundError` | 404 | Indicates market data not found for symbol |
| Invalid fixture JSON at runtime | `MarketDataDeserializationError` | 500 | Generic server error message |
| Unexpected pipeline/domain error | Unhandled `Exception` | 500 | Generic server error message |
| Successful classification | Mapper + route | 200 | N/A (success body) |

Recovery: no retries, caching, or partial-result responses in this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Route integration (success) | `src/infrastructure/tests/test_classification_route.py` | `TestClient(create_app())` GET `/markets/BTC-USDT/classification` and `/markets/ETH-USDT/classification` → 200; body schema; `symbol` equals `"BTC/USDT"` / `"ETH/USDT"`; non-empty four domains; expected `source` values include `regime`, `risk`, `economic`, `exposure` |
| Route integration (URL conversion) | Same file | Assert `ClassifyMarket.execute` receives `"BTC/USDT"` when URL param is `BTC-USDT` (via spy/stub or indirect assertion through 200 + response `symbol`) |
| Route integration (not found) | Same file | GET `/markets/SOL-USDT/classification` → 404 |
| Route integration (validation) | Same file | GET `/markets/BTC/classification` → 422; GET `/markets/BTC%2FUSDT/classification` → 422 |
| Route integration (server error) | Same file | Patch/stub `ClassifyMarket.execute` to raise `RuntimeError` → 500 |
| DTO boundary | Same file or dedicated mapper test | Assert JSON response keys match DTO fields; response `symbol` uses slash format; no domain type leakage in `response_model` |
| Domain purity guard | Extend existing pattern in `test_health.py` or classification test module | Confirm `src/modules/` and `src/application/` contain no new `fastapi` / `pydantic` imports |

**TestClient path examples:**

```python
client.get("/markets/BTC-USDT/classification")
client.get("/markets/ETH-USDT/classification")
client.get("/markets/SOL-USDT/classification")
client.get("/markets/BTC/classification")
client.get("/markets/BTC%2FUSDT/classification")
```

**Coverage expectations:**

- All acceptance criteria AC-001 through AC-012 have at least one automated test or static guard.
- Success and error paths for 200, 404, 422, and 500 are required.
- URL hyphen param to internal slash conversion is explicitly tested.
- Mapper unit test optional if route tests fully cover field mapping; at minimum one success test asserts per-signal field presence and slash-format `symbol`.

## Package configuration

Update `pyproject.toml` `[tool.setuptools]` package discovery if needed to include new infrastructure subpackages:

- `market_data_be.infrastructure.http.dtos`
- `market_data_be.infrastructure.http.mappers`
- `market_data_be.infrastructure.http.validation`

Follow the existing `market_data_be.infrastructure` package-dir mapping pattern from prior features.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `GET /markets/{symbol}/classification` route in `routes/classification.py` |
| REQ-002 | Path parameter accepts hyphen-separated `BASE-QUOTE` (e.g. `BTC-USDT`) |
| REQ-003 | `parse_url_symbol` validates URL format and returns internal `BASE/QUOTE` |
| REQ-004 | Route handler calls `classify_market.execute(internal_symbol)` with slash-separated symbol |
| REQ-005 | `response_model=MarketClassificationResponse`; handler return type is HTTP DTO |
| REQ-006 | `MarketClassificationResponse` fields: `symbol`, `regime`, `risk`, `economic`, `exposure` |
| REQ-007 | `ClassificationSignalResponse` with `source`, `score`, `reason` |
| REQ-008 | `map_market_classification_to_response` in `mappers/classification.py` |
| REQ-009 | Response `symbol` field uses slash-separated format from `MarketClassification.symbol` |
| REQ-010 | `create_app()` registers classification router |
| REQ-011 | `build_classify_market()` wires `MockMarketDataProvider` + real engine/classifiers |
| REQ-012 | Exception handler for `MarketDataNotFoundError` → 404 |
| REQ-013 | `parse_url_symbol` + 422 mapping for format failures (bare, slash, multi-hyphen) |
| REQ-014 | Handlers for `MarketDataDeserializationError` and generic `Exception` → 500 |
| REQ-015 | Integration tests for `BTC-USDT` and `ETH-USDT` URL paths resolving to fixture symbols |
| NFR-001 | All FastAPI/Pydantic code under `src/infrastructure/http/` only |
| NFR-002 | Application layer unchanged; no HTTP imports added |
| NFR-003 | Tests in `src/infrastructure/tests/test_classification_route.py` using `TestClient` |
| NFR-004 | Typed DTOs, mapper, and route handler signatures |
| NFR-005 | No edits to `classify_market.py`, classifiers, or fixtures |
| NFR-006 | No auth, WebSocket, or live provider adapters |
