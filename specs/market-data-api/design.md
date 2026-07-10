# Design

## Overview

Add a market data HTTP route under `src/infrastructure/http/` that accepts a hyphen-separated market symbol URL path parameter, validates and converts it to the internal slash-separated format via the existing `parse_url_symbol`, invokes the existing `GetMarketData` use case, maps domain `MarketData` to Pydantic response DTOs, and translates infrastructure errors into HTTP status codes. Extend the composition module to wire `GetMarketData` with `MockMarketDataProvider` and register the route in `create_app()`. Domain and application layers are consumers only; no behavioral changes to retrieval or fixtures.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/modules/analysis/` | Unchanged; `MarketData` types consumed as use-case output only |
| Application | `src/application/` | `GetMarketData` invoked by infrastructure with slash-separated symbol; **no changes** |
| Infrastructure — market data | `src/infrastructure/market_data/` | `MockMarketDataProvider`, error types reused; **no changes** |
| Infrastructure — HTTP | `src/infrastructure/http/` | Route, DTOs, mapper, composition extension, exception mapping reuse |

### New and modified components

```
src/infrastructure/http/
├── app.py                              # MODIFY: register market-data router; reuse existing exception handlers
├── composition.py                      # MODIFY: add build_get_market_data() wiring
├── dtos/
│   └── market_data.py                  # NEW: Pydantic response DTOs
├── mappers/
│   └── market_data.py                  # NEW: MarketData → response DTO
├── routes/
│   └── market_data.py                  # NEW: GET market-data endpoint
└── validation/
    └── symbol.py                       # REUSE: parse_url_symbol (no changes)

src/infrastructure/tests/
└── test_market_data_route.py           # NEW: TestClient integration tests
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| DTOs in `infrastructure/http/dtos/` | Keeps serialization contracts out of application and domain layers | REQ-005, NFR-002 |
| Mapper in `infrastructure/http/mappers/` | Translation from domain output to HTTP contract is an adapter concern | REQ-010 |
| Composition extension in `composition.py` | Centralizes default dependency wiring alongside existing classification composition | REQ-013 |
| Reuse `parse_url_symbol` | Same URL contract as classification API; avoids duplicate validation logic | REQ-003, REQ-015, NFR-007 |
| Route invokes use case only | Application orchestration remains in `GetMarketData`; route is a thin adapter | REQ-004, NFR-005 |
| Response `symbol` uses slash format | Aligns JSON body with domain/application convention while URL uses hyphen format | REQ-011 |
| Decimal as JSON string | Matches fixture serialization contract and preserves precision | REQ-009 |

### Out of scope (explicit)

- Authentication and authorization
- Live exchange adapters
- Modifications to `GetMarketData`, `MarketDataProvider`, `MockMarketDataProvider`, or domain models
- WebSocket or streaming endpoints
- Changes to `resources/market_data/*.json` fixture content
- Changes to `parse_url_symbol` behavior (reuse as-is)
- Changes to classification route or classification DTOs

## Data Flow

### Successful market data request

```
Client
  │
  │  GET /markets/BTC-USDT/market-data
  ▼
FastAPI app (create_app)
  │
  ▼
market_data router
  │
  ├─► parse_url_symbol("BTC-USDT")  ──► ValueError → HTTP 422
  │         │
  │         └─► returns internal "BTC/USDT"
  │
  ├─► GetMarketData.execute("BTC/USDT")
  │         │
  │         └─► MockMarketDataProvider.get_market_data("BTC/USDT")
  │                   │
  │                   └─► MarketData (domain)
  │
  ├─► map_market_data_to_response(market_data)
  │         │
  │         └─► response.symbol = "BTC/USDT"  (slash format in JSON body)
  │
  ▼
HTTP 200 + MarketDataResponse JSON
```

### Error paths

```
Invalid URL symbol format (e.g. "BTC", "BTC/USDT", "BTC-USDT-EXTRA")
  → parse_url_symbol raises ValueError
  → route/exception handler → HTTP 422

Symbol not found (e.g. URL "SOL-USDT" → internal "SOL/USDT")
  → GetMarketData → MockMarketDataProvider
  → MarketDataNotFoundError
  → exception handler → HTTP 404

Corrupt fixture / deserialization failure
  → MarketDataDeserializationError
  → exception handler → HTTP 500

Any other unhandled Exception
  → exception handler → HTTP 500
```

## Interfaces

### HTTP: `GET /markets/{symbol}/market-data`

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path pattern | `/markets/{symbol}/market-data` |
| Path parameter `symbol` | Hyphen-separated trading pair `BASE-QUOTE` (for example, `BTC-USDT`); standard FastAPI path segment — no `{symbol:path}` catch-all |
| Auth | None |
| Success status | `200` |
| Response `Content-Type` | `application/json` |
| Router tag | `market-data` |

**Example request:**

```http
GET /markets/BTC-USDT/market-data HTTP/1.1
Host: localhost:8000
```

**Example success response (HTTP 200, truncated):**

```json
{
  "symbol": "BTC/USDT",
  "current_price": "67234.50",
  "order_book": {
    "bids": [
      { "price": "67234.00", "quantity": "1.250" }
    ],
    "asks": [
      { "price": "67235.00", "quantity": "0.980" }
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
          "quote_volume": null,
          "trade_count": null,
          "buy_volume": null,
          "buy_quote_volume": null
        }
      ]
    }
  ]
}
```

The response `symbol` field uses internal slash-separated format (`BTC/USDT`). The request URL uses hyphen-separated format (`BTC-USDT`). Exact numeric and candle values are determined by existing fixtures; tests assert structure, types, and non-emptiness, not fixed literals unless derived from stable fixture outcomes.

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

**Location:** `src/infrastructure/http/validation/symbol.py` (existing; **reuse unchanged**)

```python
def parse_url_symbol(url_symbol: str) -> str:
    """Validate BASE-QUOTE URL path param and return internal BASE/QUOTE symbol.

    Raises ValueError for invalid format.
    """
    ...
```

**Contract (unchanged from classification API):**

| Input (URL path param) | Result |
|------------------------|--------|
| `BTC-USDT` | Returns internal `BTC/USDT` |
| `btc-usdt` | Returns internal `BTC/USDT` (uppercase base and quote segments) |
| `ETH-USDT` | Returns internal `ETH/USDT` |
| `BTC` | Invalid; `ValueError` |
| `BTC/USDT` | Invalid; `ValueError` |
| `BTC%2FUSDT` (decoded to `BTC/USDT`) | Invalid; `ValueError` |
| `BTC-USDT-EXTRA` | Invalid; `ValueError` |
| Empty or whitespace-only segment | Invalid; `ValueError` |

This conversion remains the sole responsibility of the HTTP validation layer. `GetMarketData`, `MarketDataProvider`, and `symbol_to_fixture_filename` continue to operate on slash-separated symbols unchanged.

### HTTP response DTOs

**Location:** `src/infrastructure/http/dtos/market_data.py`

```python
from pydantic import BaseModel


class OrderLevelResponse(BaseModel):
    price: str
    quantity: str


class OrderBookResponse(BaseModel):
    bids: list[OrderLevelResponse]
    asks: list[OrderLevelResponse]


class CandleResponse(BaseModel):
    start_time: str
    end_time: str
    open: str
    high: str
    low: str
    close: str
    base_volume: str
    quote_volume: str | None = None
    trade_count: int | None = None
    buy_volume: str | None = None
    buy_quote_volume: str | None = None


class CandleSeriesResponse(BaseModel):
    timeframe: str
    candles: list[CandleResponse]


class MarketDataResponse(BaseModel):
    symbol: str
    current_price: str
    order_book: OrderBookResponse
    series: list[CandleSeriesResponse]
```

| Field | JSON type | Source |
|-------|-----------|--------|
| `symbol` | string | `MarketData.symbol` (slash-separated) |
| `current_price` | string | `str(MarketData.current_price)` |
| `order_book.bids` / `asks` | array | Mapped from `OrderBook` levels |
| `price` / `quantity` | string | `str(Decimal)` |
| `series[].timeframe` | string | `Timeframe` enum value (e.g. `"15m"`) |
| `candles[].start_time` / `end_time` | string | ISO 8601 UTC |
| OHLC / volume decimals | string | `str(Decimal)` |
| Optional candle fields | string / int / null | Pass through; `None` → JSON `null` |

`response_model=MarketDataResponse` on the route handler enforces the outward contract.

### Infrastructure mapper

**Location:** `src/infrastructure/http/mappers/market_data.py`

```python
def map_market_data_to_response(market_data: MarketData) -> MarketDataResponse:
    ...
```

| Input | Output |
|-------|--------|
| `MarketData` (domain dataclass) | `MarketDataResponse` (Pydantic) |

Maps nested `OrderBook`, `OrderLevel`, `CandleSeries`, and `Candle` values to response DTOs. Converts `Decimal` fields with `str(...)`. Formats datetimes as ISO 8601 UTC ending in `Z` (or equivalent UTC offset form consistent with fixture convention). Passes through `market_data.symbol` unchanged. Does not expose domain types on the HTTP boundary.

### Composition / dependency wiring

**Location:** `src/infrastructure/http/composition.py` (extend existing module)

```python
def build_get_market_data() -> GetMarketData:
    return GetMarketData(
        provider=MockMarketDataProvider(),
    )
```

| Dependency | Implementation | Notes |
|------------|----------------|-------|
| `provider` | `MockMarketDataProvider()` | Default fixtures directory |

**Route dependency access:** expose a FastAPI dependency callable (for example, `get_get_market_data()` or `get_market_data_use_case()`) that returns the wired `GetMarketData` instance. Instantiate once per app via `create_app()` (module-level or `app.state`) rather than per-request construction. Existing `build_classify_market()` remains unchanged.

### Market data route handler

**Location:** `src/infrastructure/http/routes/market_data.py`

```python
router = APIRouter(tags=["market-data"])


@router.get(
    "/markets/{symbol}/market-data",
    response_model=MarketDataResponse,
)
def get_market_data(
    symbol: str,
    get_market_data_uc: GetMarketData = Depends(get_market_data_use_case),
) -> MarketDataResponse:
    internal_symbol = parse_url_symbol(symbol)
    market_data = get_market_data_uc.execute(internal_symbol)
    return map_market_data_to_response(market_data)
```

The handler shall not return domain `MarketData` directly. The path uses a standard `{symbol}` segment (not `{symbol:path}`).

### Application factory changes

**Location:** `src/infrastructure/http/app.py`

`create_app()` shall:

1. Instantiate `GetMarketData` via `build_get_market_data()` and store on `app.state` (or equivalent single-instance holder).
2. Register the market-data router.
3. Reuse existing exception handlers already registered for classification:
   - `MarketDataNotFoundError` → 404
   - `MarketDataDeserializationError` → 500
   - Scoped URL validation `ValueError` → 422
   - Generic unhandled `Exception` → 500

If classification handlers already cover these exception types globally, do not duplicate registrations; ensure the market-data route benefits from the same handlers. If validation `ValueError` handling is route-scoped only for classification, apply the same pattern to the market-data route (dedicated validation exception type or route-level catch) so pipeline/domain `ValueError` still maps to 500.

**Pipeline `ValueError` policy:** `ValueError` raised inside `GetMarketData` or provider internals that is not URL-format validation shall surface as HTTP 500. Only URL symbol-format validation failures map to 422.

## Data Model

### HTTP outward schema

```
MarketDataResponse
├── symbol: str                         # slash-separated (e.g. "BTC/USDT")
├── current_price: str                  # Decimal as string
├── order_book: OrderBookResponse
│   ├── bids: OrderLevelResponse[]
│   └── asks: OrderLevelResponse[]
└── series: CandleSeriesResponse[]
    ├── timeframe: str
    └── candles: CandleResponse[]
        ├── start_time / end_time: str  # ISO 8601 UTC
        ├── open / high / low / close / base_volume: str
        └── optional: quote_volume, trade_count, buy_volume, buy_quote_volume
```

### Internal types (unchanged, not exposed on wire)

```
MarketData (domain)
├── symbol: str
├── current_price: Decimal
├── order_book: OrderBook
└── series: tuple[CandleSeries, ...]
```

### Symbol format boundary

| Context | Format | Example |
|---------|--------|---------|
| URL path parameter | Hyphen-separated `BASE-QUOTE` | `BTC-USDT` |
| Use case / provider input | Slash-separated `BASE/QUOTE` | `BTC/USDT` |
| JSON response `symbol` field | Slash-separated `BASE/QUOTE` | `BTC/USDT` |
| Fixture filename resolution | Via `symbol_to_fixture_filename` on slash symbol | `btc_usdt.json` |

No persistence or state transitions; each request is retrieved on demand.

## Error Handling

| Scenario | Component | HTTP | Response `detail` (minimum) |
|----------|-----------|------|-----------------------------|
| Missing `-` or multiple `-` segments | `parse_url_symbol` | 422 | Indicates invalid symbol format |
| Slash present in path param | `parse_url_symbol` | 422 | Indicates invalid symbol format |
| Empty base or quote | `parse_url_symbol` | 422 | Indicates invalid symbol format |
| Valid format, no fixture | `MockMarketDataProvider` → `MarketDataNotFoundError` | 404 | Indicates market data not found for symbol |
| Invalid fixture JSON at runtime | `MarketDataDeserializationError` | 500 | Generic server error message |
| Unexpected provider/use-case error | Unhandled `Exception` | 500 | Generic server error message |
| Successful retrieval | Mapper + route | 200 | N/A (success body) |

Recovery: no retries, caching, or partial-result responses in this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Route integration (success) | `src/infrastructure/tests/test_market_data_route.py` | `TestClient(create_app())` GET `/markets/BTC-USDT/market-data` and `/markets/ETH-USDT/market-data` → 200; body schema; `symbol` equals `"BTC/USDT"` / `"ETH/USDT"`; non-empty bids/asks/series; decimal fields are strings; datetimes are ISO strings |
| Route integration (URL conversion) | Same file | Assert `GetMarketData.execute` receives `"BTC/USDT"` when URL param is `BTC-USDT` (via spy/stub or indirect assertion through 200 + response `symbol`) |
| Route integration (not found) | Same file | GET `/markets/SOL-USDT/market-data` → 404 |
| Route integration (validation) | Same file | GET `/markets/BTC/market-data` → 422; GET `/markets/BTC%2FUSDT/market-data` → 422 |
| Route integration (server error) | Same file | Patch/stub `GetMarketData.execute` to raise `RuntimeError` → 500 |
| DTO boundary | Same file or dedicated mapper test | Assert JSON response keys match DTO fields; response `symbol` uses slash format; no domain type leakage in `response_model` |
| Domain purity guard | Extend existing pattern | Confirm `src/modules/` and `src/application/` contain no new `fastapi` / `pydantic` imports; confirm `parse_url_symbol` is imported from existing validation module (not duplicated) |

**TestClient path examples:**

```python
client.get("/markets/BTC-USDT/market-data")
client.get("/markets/ETH-USDT/market-data")
client.get("/markets/SOL-USDT/market-data")
client.get("/markets/BTC/market-data")
client.get("/markets/BTC%2FUSDT/market-data")
```

**Coverage expectations:**

- All acceptance criteria AC-001 through AC-012 have at least one automated test or static guard.
- Success and error paths for 200, 404, 422, and 500 are required.
- URL hyphen param to internal slash conversion is explicitly tested.
- Mapper unit test optional if route tests fully cover field mapping; at minimum one success test asserts decimal-as-string, ISO datetime, and slash-format `symbol`.

## Package configuration

Update `pyproject.toml` `[tool.setuptools]` package discovery if needed to include any new modules under existing packages. Prefer placing new modules inside already-discovered packages (`market_data_be.infrastructure.http.dtos`, `.mappers`, `.routes`) so no discovery change is required.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `GET /markets/{symbol}/market-data` route in `routes/market_data.py` |
| REQ-002 | Path parameter accepts hyphen-separated `BASE-QUOTE` (e.g. `BTC-USDT`) |
| REQ-003 | Reuse `parse_url_symbol` to validate URL format and return internal `BASE/QUOTE` |
| REQ-004 | Route handler calls `get_market_data_uc.execute(internal_symbol)` with slash-separated symbol |
| REQ-005 | `response_model=MarketDataResponse`; handler return type is HTTP DTO |
| REQ-006 | `MarketDataResponse` fields: `symbol`, `current_price`, `order_book`, `series` |
| REQ-007 | `OrderBookResponse` / `OrderLevelResponse` with string `price` and `quantity` |
| REQ-008 | `CandleSeriesResponse` / `CandleResponse` with required candle fields |
| REQ-009 | Mapper serializes `Decimal` as `str` and datetimes as ISO 8601 UTC |
| REQ-010 | `map_market_data_to_response` in `mappers/market_data.py` |
| REQ-011 | Response `symbol` field uses slash-separated format from `MarketData.symbol` |
| REQ-012 | `create_app()` registers market-data router |
| REQ-013 | `build_get_market_data()` wires `MockMarketDataProvider` into `GetMarketData` |
| REQ-014 | Exception handler for `MarketDataNotFoundError` → 404 |
| REQ-015 | `parse_url_symbol` + 422 mapping for format failures |
| REQ-016 | Handlers for `MarketDataDeserializationError` and generic `Exception` → 500 |
| REQ-017 | Integration tests for `BTC-USDT` and `ETH-USDT` URL paths resolving to fixture symbols |
| NFR-001 | All FastAPI/Pydantic code under `src/infrastructure/http/` only |
| NFR-002 | Application layer unchanged; no HTTP imports added |
| NFR-003 | Tests in `src/infrastructure/tests/test_market_data_route.py` using `TestClient` |
| NFR-004 | Typed DTOs, mapper, and route handler signatures |
| NFR-005 | No edits to `get_market_data.py`, provider, domain models, or fixtures |
| NFR-006 | No auth, WebSocket, or live provider adapters |
| NFR-007 | Import and reuse existing `parse_url_symbol`; do not add a second parser |
