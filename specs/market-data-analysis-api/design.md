# Design

## Overview

Add a market analysis HTTP route under `src/market_data_be/infrastructure/http/` that accepts a hyphen-separated market symbol URL path parameter, validates and converts it to the internal slash-separated format (reusing existing `parse_url_symbol`), invokes a new `AnalyzeMarket` application use case, maps domain `AnalysisResult` to Pydantic response DTOs, and translates infrastructure errors into HTTP status codes. Extend composition to wire `AnalyzeMarket` with `MockMarketDataProvider` and `MarketAnalysisEngine`, and register the route in `create_app()`. Domain analysis algorithms remain unchanged; the application layer gains a thin orchestration use case parallel to `GetMarketData` and `ClassifyMarket`.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/market_data_be/modules/analysis/` | Unchanged; `MarketAnalysisEngine.analyze` produces `AnalysisResult` |
| Classification domain | `src/market_data_be/modules/classification/` | Unchanged; not involved |
| Application | `src/market_data_be/application/` | **NEW** `AnalyzeMarket` use case: provider + analysis engine → `AnalysisResult` |
| Infrastructure — market data | `src/market_data_be/infrastructure/market_data/` | `MockMarketDataProvider`, error types reused; **no changes** |
| Infrastructure — HTTP | `src/market_data_be/infrastructure/http/` | Route, DTOs, mapper, composition extension, exception mapping reuse |

### New / modified components

```
src/market_data_be/application/
├── use_cases/
│   └── analyze_market.py               # NEW: AnalyzeMarket use case
└── tests/
    └── test_analyze_market.py          # NEW: use case unit tests

src/market_data_be/infrastructure/http/
├── app.py                              # MODIFY: register analysis router; reuse exception handlers
├── composition.py                      # MODIFY: add build_analyze_market() wiring
├── dtos/
│   └── analysis.py                     # NEW: Pydantic response DTOs for AnalysisResult graph
├── mappers/
│   └── analysis.py                     # NEW: AnalysisResult → response DTO
├── routes/
│   └── analysis.py                     # NEW: GET analysis endpoint
└── validation/
    └── symbol.py                       # REUSE: existing parse_url_symbol (no behavior change)

src/market_data_be/infrastructure/tests/
└── test_analysis_route.py              # NEW: TestClient integration tests
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| New `AnalyzeMarket` use case | No existing use case returns `AnalysisResult`; HTTP routes must not orchestrate provider + domain facade directly | REQ-004, REQ-005, NFR-002 |
| DTOs in `infrastructure/http/dtos/` | Keeps serialization contracts out of application and domain layers | REQ-006, NFR-002 |
| Mapper in `infrastructure/http/mappers/` | Translation from domain output to HTTP contract is an adapter concern | REQ-009 |
| Composition extension in `composition.py` | Centralizes default dependency wiring alongside existing use case builders | REQ-012 |
| Reuse `parse_url_symbol` | Same URL symbol contract as classification and market-data APIs | REQ-003, REQ-014, REQ-017 |
| Route invokes use case only | Application orchestration remains in `AnalyzeMarket`; route is a thin adapter | REQ-005, NFR-005 |
| Response `symbol` uses slash format | Aligns JSON body with domain/application convention while URL uses hyphen format | REQ-010 |
| Default portfolio state | Acceptance criteria do not require portfolio input; engine default matches `ClassifyMarket` behavior | REQ-018, NFR-006 |
| Field-for-field DTO mirroring | `AnalysisResult` and nested assessments already define the analysis contract; DTOs mirror public domain fields without inventing a reduced subset | REQ-007, REQ-008 |

### Out of scope (explicit)

- Authentication and authorization
- Live exchange adapters
- Modifications to `MarketAnalysisEngine` algorithms, analyzers, or synthesis
- Modifications to `MarketDataProvider`, mock provider, deserializer, or domain analysis model definitions
- WebSocket or streaming endpoints
- Changes to `resources/market_data/*.json` fixture content
- Changes to classification or market-data route behavior
- Request parameters for `PortfolioState`
- Changes to `ClassifyMarket` or `GetMarketData`

## Data Flow

### Successful analysis request

```
Client
  │
  │  GET /markets/BTC-USDT/analysis
  ▼
FastAPI app (create_app)
  │
  ▼
analysis router
  │
  ├─► parse_url_symbol("BTC-USDT")  ──► ValueError → HTTP 422
  │         │
  │         └─► returns internal "BTC/USDT"
  │
  ├─► AnalyzeMarket.execute("BTC/USDT")
  │         │
  │         ├─► MockMarketDataProvider.get_market_data("BTC/USDT")
  │         │         │
  │         │         └─► MarketData (domain)
  │         │
  │         └─► MarketAnalysisEngine.analyze(market_data)  # default portfolio
  │                   │
  │                   └─► AnalysisResult (domain)
  │
  ├─► map_analysis_result_to_response(analysis_result)
  │         │
  │         └─► response.symbol = "BTC/USDT"  (slash format in JSON body)
  │
  ▼
HTTP 200 + MarketAnalysisResponse JSON
```

### Error paths

```
Invalid URL symbol format (e.g. "BTC", "BTC/USDT", "BTC-USDT-EXTRA")
  → parse_url_symbol raises ValueError
  → route/exception handler → HTTP 422

Symbol not found (e.g. URL "SOL-USDT" → internal "SOL/USDT")
  → AnalyzeMarket → MockMarketDataProvider
  → MarketDataNotFoundError
  → exception handler → HTTP 404

Corrupt fixture / deserialization failure
  → MarketDataDeserializationError
  → exception handler → HTTP 500

Any other unhandled Exception (including unexpected analysis errors)
  → exception handler → HTTP 500
```

## Interfaces

### HTTP: `GET /markets/{symbol}/analysis`

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path pattern | `/markets/{symbol}/analysis` |
| Path parameter `symbol` | Hyphen-separated trading pair `BASE-QUOTE` (for example, `BTC-USDT`); standard FastAPI path segment — no `{symbol:path}` catch-all |
| Auth | None |
| Success status | `200` |
| Response `Content-Type` | `application/json` |
| Router tag | `analysis` |

**Example request:**

```http
GET /markets/BTC-USDT/analysis HTTP/1.1
Host: localhost:8000
```

**Example success response (HTTP 200, illustrative shape):**

```json
{
  "symbol": "BTC/USDT",
  "regime": {
    "regime": "trend_up",
    "insufficient_data": false
  },
  "risk": {
    "score": 0.0,
    "insufficient_data": false
  },
  "economic": {
    "edge": 0.0,
    "insufficient_data": false
  },
  "exposure": {
    "available_capacity_pct": 0.0
  },
  "catalog": {}
}
```

Nested field names and additional public attributes (for example, `reasons`, `components`, or catalog entries) must match the public fields of the corresponding domain dataclasses in `modules/analysis/`. The example above is illustrative of top-level shape and serialization style; tests assert presence of required top-level keys, slash-format `symbol`, enum-as-string encoding, and that nested objects are JSON objects — not fixed assessment literals unless derived from stable fixture outcomes.

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

**Location:** `src/market_data_be/infrastructure/http/validation/symbol.py` (existing)

Reuse `parse_url_symbol` without behavioral changes:

| Input (URL path param) | Result |
|------------------------|--------|
| `BTC-USDT` | Returns internal `BTC/USDT` |
| `btc-usdt` | Returns internal `BTC/USDT` (uppercase base and quote segments) |
| `ETH-USDT` | Returns internal `ETH/USDT` |
| `BTC` | Invalid; `ValueError` |
| `BTC/USDT` | Invalid; `ValueError` |
| `BTC%2FUSDT` (decoded to `BTC/USDT`) | Invalid; `ValueError` |
| `BTC-USDT-EXTRA` | Invalid; `ValueError` |

This conversion remains the sole responsibility of the HTTP validation layer. `AnalyzeMarket`, `MarketDataProvider`, and `symbol_to_fixture_filename` continue to operate on slash-separated symbols unchanged.

### Application use case: `AnalyzeMarket`

**Location:** `src/market_data_be/application/use_cases/analyze_market.py`

```python
class AnalyzeMarket:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        engine: MarketAnalysisEngine,
    ) -> None:
        ...

    def execute(self, symbol: str) -> AnalysisResult:
        market_data = self._provider.get_market_data(symbol)
        return self._engine.analyze(market_data)
```

| Attribute | Value |
|-----------|-------|
| Constructor dependencies | `MarketDataProvider`, `MarketAnalysisEngine` |
| Primary method | `execute(symbol: str) -> AnalysisResult` |
| Data resolution | Always via `provider.get_market_data(symbol)` |
| Analysis | `engine.analyze(market_data)` with no explicit `portfolio_state` (engine default) |
| Return type | Domain `AnalysisResult` (not an HTTP DTO) |
| Infrastructure imports | **None** (provider is port Protocol only) |

Optional `market_data` override (as in `ClassifyMarket`) is **not** required for this feature.

### HTTP response DTOs

**Location:** `src/market_data_be/infrastructure/http/dtos/analysis.py`

Define Pydantic models that mirror the public structure of domain `AnalysisResult`:

```python
from pydantic import BaseModel


class RegimeAssessmentResponse(BaseModel):
    # Public fields of RegimeAssessment (e.g. regime: str, insufficient_data: bool, ...)
    ...


class RiskAssessmentResponse(BaseModel):
    # Public fields of RiskAssessment (e.g. score: float, insufficient_data: bool, ...)
    ...


class EconomicAssessmentResponse(BaseModel):
    # Public fields of EconomicAssessment (e.g. edge: float, insufficient_data: bool, ...)
    ...


class ExposureProfileResponse(BaseModel):
    # Public fields of ExposureProfile (e.g. available_capacity_pct: float, ...)
    ...


class CatalogResultResponse(BaseModel):
    # Public fields of CatalogResult
    ...


class MarketAnalysisResponse(BaseModel):
    symbol: str
    regime: RegimeAssessmentResponse
    risk: RiskAssessmentResponse
    economic: EconomicAssessmentResponse
    exposure: ExposureProfileResponse
    catalog: CatalogResultResponse
```

**Mirroring rule:** Each nested DTO shall declare every public attribute of the corresponding frozen domain dataclass. Nested enums become `str` (use the enum `.value`). Nested tuples/lists become JSON arrays. Nested dataclasses become nested Pydantic models. Booleans and floats remain JSON booleans and numbers. Do not omit `catalog` even though classification does not consume it.

**Minimum known fields from prior feature documentation (must be present; domain may have additional public fields that must also be mirrored):**

| Domain type | Documented fields |
|-------------|-------------------|
| `AnalysisResult` | `symbol`, `regime`, `risk`, `economic`, `exposure`, `catalog` |
| `RegimeAssessment` | `regime` (`MarketRegime` → string) |
| `RiskAssessment` | `score` |
| `EconomicAssessment` | `edge` |
| `ExposureProfile` | `available_capacity_pct` |

`response_model=MarketAnalysisResponse` on the route handler enforces the outward contract.

### Infrastructure mapper

**Location:** `src/market_data_be/infrastructure/http/mappers/analysis.py`

```python
def map_analysis_result_to_response(
    analysis_result: AnalysisResult,
) -> MarketAnalysisResponse:
    ...
```

| Input | Output |
|-------|--------|
| `AnalysisResult` (domain dataclass) | `MarketAnalysisResponse` (Pydantic) |

Maps nested assessments and catalog to DTO objects. Passes through `analysis_result.symbol` unchanged (slash-separated). Converts enums via `.value`. Does not expose domain types on the HTTP boundary.

### Composition / dependency wiring

**Location:** `src/market_data_be/infrastructure/http/composition.py`

```python
def build_analyze_market() -> AnalyzeMarket:
    return AnalyzeMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
    )
```

| Dependency | Implementation | Notes |
|------------|----------------|-------|
| `provider` | `MockMarketDataProvider()` | Default fixtures directory |
| `engine` | `MarketAnalysisEngine()` | Real analysis pipeline; no stubs in production wiring |

Existing `build_classify_market()` and `build_get_market_data()` remain unchanged. Sharing a provider instance across builders is acceptable if composition already holds one.

**Route dependency access:** expose a FastAPI dependency callable (for example, `get_analyze_market()`) that returns the wired `AnalyzeMarket` instance. Instantiate once per app via `create_app()` (module-level or `app.state`) rather than per-request construction.

### Analysis route handler

**Location:** `src/market_data_be/infrastructure/http/routes/analysis.py`

```python
router = APIRouter(tags=["analysis"])


@router.get(
    "/markets/{symbol}/analysis",
    response_model=MarketAnalysisResponse,
)
def get_market_analysis(
    symbol: str,
    use_case: AnalyzeMarket = Depends(get_analyze_market),
) -> MarketAnalysisResponse:
    internal_symbol = parse_url_symbol(symbol)
    analysis_result = use_case.execute(internal_symbol)
    return map_analysis_result_to_response(analysis_result)
```

The handler shall not return domain `AnalysisResult` directly. The path uses a standard `{symbol}` segment (not `{symbol:path}`).

### Application factory changes

**Location:** `src/market_data_be/infrastructure/http/app.py`

`create_app()` shall:

1. Instantiate `AnalyzeMarket` via `build_analyze_market()` and store on `app.state` (or equivalent single-instance holder), alongside existing use case wiring.
2. Register the analysis router.
3. Reuse existing exception handlers where already registered:
   - `MarketDataNotFoundError` → 404
   - `MarketDataDeserializationError` → 500
   - Scoped URL validation `ValueError` → 422
   - Generic unhandled `Exception` → 500

If prior API features already registered these handlers globally, analysis routes inherit them; do not duplicate conflicting handlers. Ensure analysis route validation failures still map to 422 with the same policy: only URL symbol-format validation failures map to 422; unexpected `ValueError` from deeper layers maps to 500.

## Data Model

### HTTP outward schema

```
MarketAnalysisResponse
├── symbol: str                         # slash-separated (e.g. "BTC/USDT")
├── regime: RegimeAssessmentResponse    # mirrors RegimeAssessment
├── risk: RiskAssessmentResponse        # mirrors RiskAssessment
├── economic: EconomicAssessmentResponse
├── exposure: ExposureProfileResponse
└── catalog: CatalogResultResponse      # mirrors CatalogResult
```

### Internal types (unchanged domain models, not exposed on wire)

```
AnalysisResult (domain)
├── symbol: str
├── regime: RegimeAssessment
├── risk: RiskAssessment
├── economic: EconomicAssessment
├── exposure: ExposureProfile
└── catalog: CatalogResult
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
| Unexpected analysis/domain error | Unhandled `Exception` | 500 | Generic server error message |
| Successful analysis | Mapper + route | 200 | N/A (success body) |

Recovery: no retries, caching, or partial-result responses in this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Use case unit (delegation) | `src/market_data_be/application/tests/test_analyze_market.py` | Fake provider + stub engine: `execute` calls `get_market_data(symbol)` then `analyze(market_data)` with no portfolio argument; returns engine result |
| Use case integration | Same file | `MockMarketDataProvider` + real `MarketAnalysisEngine` for `BTC/USDT` and `ETH/USDT` → `AnalysisResult.symbol` matches; assessments present |
| Route integration (success) | `src/market_data_be/infrastructure/tests/test_analysis_route.py` | `TestClient(create_app())` GET `/markets/BTC-USDT/analysis` and `/markets/ETH-USDT/analysis` → 200; body has top-level keys; `symbol` equals `"BTC/USDT"` / `"ETH/USDT"`; assessment objects present; enums serialized as strings |
| Route integration (URL conversion) | Same file | Assert `AnalyzeMarket.execute` receives `"BTC/USDT"` when URL param is `BTC-USDT` (via spy/stub or indirect assertion through 200 + response `symbol`) |
| Route integration (not found) | Same file | GET `/markets/SOL-USDT/analysis` → 404 |
| Route integration (validation) | Same file | GET `/markets/BTC/analysis` → 422; GET `/markets/BTC%2FUSDT/analysis` → 422 |
| Route integration (server error) | Same file | Patch/stub `AnalyzeMarket.execute` to raise `RuntimeError` → 500 |
| DTO boundary | Same file or dedicated mapper test | Assert JSON response keys match DTO fields; response `symbol` uses slash format; no domain type leakage in `response_model` |
| Domain purity guard | Extend existing pattern | Confirm `src/market_data_be/modules/` contains no new `fastapi` / `pydantic` imports; application has no FastAPI/Pydantic HTTP DTO imports |

**TestClient path examples:**

```python
client.get("/markets/BTC-USDT/analysis")
client.get("/markets/ETH-USDT/analysis")
client.get("/markets/SOL-USDT/analysis")
client.get("/markets/BTC/analysis")
client.get("/markets/BTC%2FUSDT/analysis")
```

**Coverage expectations:**

- All acceptance criteria AC-001 through AC-012 have at least one automated test or static guard.
- Success and error paths for 200, 404, 422, and 500 are required.
- URL hyphen param to internal slash conversion is explicitly tested.
- Mapper unit test optional if route tests fully cover field mapping; at minimum one success test asserts top-level schema and slash-format `symbol`.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `GET /markets/{symbol}/analysis` route in `routes/analysis.py` |
| REQ-002 | Path parameter accepts hyphen-separated `BASE-QUOTE` (e.g. `BTC-USDT`) |
| REQ-003 | Reuse `parse_url_symbol` to validate URL format and return internal `BASE/QUOTE` |
| REQ-004 | `AnalyzeMarket` use case: provider + `MarketAnalysisEngine` → `AnalysisResult` |
| REQ-005 | Route handler calls `AnalyzeMarket.execute(internal_symbol)` with slash-separated symbol |
| REQ-006 | `response_model=MarketAnalysisResponse`; handler return type is HTTP DTO |
| REQ-007 | `MarketAnalysisResponse` fields: `symbol`, `regime`, `risk`, `economic`, `exposure`, `catalog` |
| REQ-008 | Nested DTOs mirror public domain assessment/catalog fields; enums as strings |
| REQ-009 | `map_analysis_result_to_response` in `mappers/analysis.py` |
| REQ-010 | Response `symbol` field uses slash-separated format from `AnalysisResult.symbol` |
| REQ-011 | `create_app()` registers analysis router |
| REQ-012 | `build_analyze_market()` wires `MockMarketDataProvider` + `MarketAnalysisEngine` |
| REQ-013 | Exception handler for `MarketDataNotFoundError` → 404 |
| REQ-014 | `parse_url_symbol` + 422 mapping for format failures |
| REQ-015 | Handlers for `MarketDataDeserializationError` and generic `Exception` → 500 |
| REQ-016 | Integration tests for `BTC-USDT` and `ETH-USDT` URL paths resolving to fixture symbols |
| REQ-017 | Reuse existing `parse_url_symbol` without duplicating validation rules |
| REQ-018 | `AnalyzeMarket` calls `engine.analyze(market_data)` without explicit portfolio state |
| NFR-001 | All FastAPI/Pydantic HTTP code under `src/market_data_be/infrastructure/http/` only |
| NFR-002 | Application exposes use case + `AnalysisResult`; no HTTP DTOs in application |
| NFR-003 | Route tests in `src/market_data_be/infrastructure/tests/test_analysis_route.py` using `TestClient` |
| NFR-004 | Typed DTOs, mapper, and route handler signatures |
| NFR-005 | No edits to analysis engine algorithms, provider, domain model definitions, or fixtures |
| NFR-006 | No auth, WebSocket, live provider, or portfolio query parameters |
| NFR-007 | Paths under `src/market_data_be/` per ADR-0001 |
| NFR-008 | Use case tests under `src/market_data_be/application/tests/test_analyze_market.py` |
