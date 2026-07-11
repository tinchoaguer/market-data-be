# Design

## Overview

Add a market data HTTP route under `src/market_data_be/infrastructure/http/` that accepts a hyphen-separated market symbol URL path parameter, validates and converts it to the internal slash-separated format (reusing existing `parse_url_symbol`), invokes the existing `GetMarketData` use case, maps domain `MarketData` to Pydantic response DTOs, and translates infrastructure errors into HTTP status codes. Extend the composition module to wire `GetMarketData` with `MockMarketDataProvider` and register the route in `create_app()`. Domain and application layers are consumers only; no behavioral changes to retrieval or fixtures.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/market_data_be/modules/analysis/` | Unchanged; `MarketData` graph is the retrieval result type |
| Classification domain | `src/market_data_be/modules/classification/` | Unchanged; not involved |
| Application | `src/market_data_be/application/` | `GetMarketData` invoked by infrastructure with slash-separated symbol; **no changes** |
| Infrastructure — market data | `src/market_data_be/infrastructure/market_data/` | `MockMarketDataProvider`, error types reused; **no changes** |
| Infrastructure — HTTP | `src/market_data_be/infrastructure/http/` | Route, DTOs, mapper, composition extension, exception mapping reuse |

### New / modified components

```
src/market_data_be/infrastructure/http/
├── app.py                              # MODIFY: register market-data router; reuse exception handlers
├── composition.py                      # MODIFY: add build_get_market_data() wiring
├── dtos/
│   └── market_data.py                  # NEW: Pydantic response DTOs for MarketData graph
├── mappers/
│   └── market_data.py                  # NEW: MarketData → response DTO
├── routes/
│   └── market_data.py                  # NEW: GET market-data endpoint
└── validation/
    └── symbol.py                       # REUSE: existing parse_url_symbol (no behavior change)

src/market_data_be/infrastructure/tests/
└── test_market_data_route.py           # NEW: TestClient integration tests
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| DTOs in `infrastructure/http/dtos/` | Keeps serialization contracts out of application and domain layers | REQ-005, NFR-002 |
| Mapper in `infrastructure/http/mappers/` | Translation from domain output to HTTP contract is an adapter concern | REQ-012 |
| Composition extension in `composition.py` | Centralizes default dependency wiring alongside existing `ClassifyMarket` wiring | REQ-015 |
| Reuse `parse_url_symbol` | Same URL symbol contract as classification API; avoids duplicated validation rules | REQ-003, REQ-017, REQ-020 |
| Route invokes use case only | Application orchestration remains in `GetMarketData`; route is a thin adapter | REQ-004, NFR-005 |
| Response `symbol` uses slash format | Aligns JSON body with domain/application convention while URL uses hyphen format | REQ-013 |
| Decimal fields as JSON strings | Matches fixture README serialization and preserves precision | REQ-010 |

### Out of scope (explicit)

- Authentication and authorization
- Live exchange adapters
- Modifications to `GetMarketData`, `MarketDataProvider`, mock provider, deserializer, or domain market models
- WebSocket or streaming endpoints
- Changes to `resources/market_data/*.json` fixture content
- Changes to classification route behavior
- Changes to `symbol_to_fixture_filename` (continues to accept slash-separated symbols only)

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
  "current_price": "65000.00",
  "order_book": {
    "bids": [
      { "price": "64990.00", "quantity": "0.5" }
    ],
    "asks": [
      { "price": "65010.00", "quantity": "0.4" }
    ]
  },
  "series": [
    {
      "timeframe": "15m",
      "candles": [
        {
          "start_time": "2024-06-01T12:00:00Z",
          "end_time": "2024-06-01T12:15:00Z",
          "open": "64900.00",
          "high": "65100.00",
          "low": "64800.00",
          "close": "65000.00",
          "base_volume": "12.5",
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

Numeric literals above are illustrative. Tests assert structure, types (string decimals, ISO datetimes), non-emptiness of `bids`/`asks`/`series`/`candles` for fixture symbols, and response `symbol` slash format — not fixed price literals unless derived from stable fixture outcomes.

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

This conversion remains the sole responsibility of the HTTP validation layer. `GetMarketData`, `MarketDataProvider`, and `symbol_to_fixture_filename` continue to operate on slash-separated symbols unchanged.

### HTTP response DTOs

**Location:** `src/market_data_be/infrastructure/http/dtos/market_data.py`

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
| `price` / `quantity` | string | `str(OrderLevel.price)` / `str(OrderLevel.quantity)` |
| `series[].timeframe` | string | `Timeframe` enum value (e.g. `"15m"`) |
| `series[].candles[]` | array | Mapped from `Candle` fields |
| candle decimals | string | `str(Decimal)` |
| candle datetimes | string | ISO 8601 UTC |
| optional candle fields | string / int / null | Pass through mapped optional values |

`response_model=MarketDataResponse` on the route handler enforces the outward contract.

### Infrastructure mapper

**Location:** `src/market_data_be/infrastructure/http/mappers/market_data.py`

```python
def map_market_data_to_response(market_data: MarketData) -> MarketDataResponse:
    ...
```

| Input | Output |
|-------|--------|
| `MarketData` (domain dataclass) | `MarketDataResponse` (Pydantic) |

Maps nested `OrderBook`, `OrderLevel`, `CandleSeries`, and `Candle` values to DTO lists/objects. Serializes `Decimal` via `str(...)`. Serializes candle `datetime` values to ISO 8601 UTC strings (prefer `Z` suffix for UTC). Passes through `market_data.symbol` unchanged. Does not expose domain types on the HTTP boundary.

### Composition / dependency wiring

**Location:** `src/market_data_be/infrastructure/http/composition.py`

```python
def build_get_market_data() -> GetMarketData:
    return GetMarketData(
        provider=MockMarketDataProvider(),
    )
```

| Dependency | Implementation | Notes |
|------------|----------------|-------|
| `provider` | `MockMarketDataProvider()` | Default fixtures directory |

Existing `build_classify_market()` remains unchanged. Both use cases may share the same provider instance if composition already holds one; either shared or separately constructed `MockMarketDataProvider()` is acceptable for this feature as long as default fixtures resolve.

**Route dependency access:** expose a FastAPI dependency callable (for example, `get_get_market_data()` or `get_market_data_use_case()`) that returns the wired `GetMarketData` instance. Instantiate once per app via `create_app()` (module-level or `app.state`) rather than per-request construction.

### Market data route handler

**Location:** `src/market_data_be/infrastructure/http/routes/market_data.py`

```python
router = APIRouter(tags=["market-data"])


@router.get(
    "/markets/{symbol}/market-data",
    response_model=MarketDataResponse,
)
def get_market_data(
    symbol: str,
    use_case: GetMarketData = Depends(get_market_data_use_case),
) -> MarketDataResponse:
    internal_symbol = parse_url_symbol(symbol)
    market_data = use_case.execute(internal_symbol)
    return map_market_data_to_response(market_data)
```

The handler shall not return domain `MarketData` directly. The path uses a standard `{symbol}` segment (not `{symbol:path}`).

### Application factory changes

**Location:** `src/market_data_be/infrastructure/http/app.py`

`create_app()` shall:

1. Instantiate `GetMarketData` via `build_get_market_data()` and store on `app.state` (or equivalent single-instance holder), alongside existing classification wiring.
2. Register the market-data router.
3. Reuse existing exception handlers where already registered:
   - `MarketDataNotFoundError` → 404
   - `MarketDataDeserializationError` → 500
   - Scoped URL validation `ValueError` → 422
   - Generic unhandled `Exception` → 500

If classification already registered these handlers globally, market-data routes inherit them; do not duplicate conflicting handlers. Ensure market-data route validation failures still map to 422 with the same policy as classification: only URL symbol-format validation failures map to 422; unexpected `ValueError` from deeper layers maps to 500.

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
        ├── open/high/low/close/base_volume: str
        └── optional volume / trade_count fields
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
| Unexpected retrieval/domain error | Unhandled `Exception` | 500 | Generic server error message |
| Successful retrieval | Mapper + route | 200 | N/A (success body) |

Recovery: no retries, caching, or partial-result responses in this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Route integration (success) | `src/market_data_be/infrastructure/tests/test_market_data_route.py` | `TestClient(create_app())` GET `/markets/BTC-USDT/market-data` and `/markets/ETH-USDT/market-data` → 200; body schema; `symbol` equals `"BTC/USDT"` / `"ETH/USDT"`; non-empty order book and series; decimal fields are strings; datetimes are ISO strings |
| Route integration (URL conversion) | Same file | Assert `GetMarketData.execute` receives `"BTC/USDT"` when URL param is `BTC-USDT` (via spy/stub or indirect assertion through 200 + response `symbol`) |
| Route integration (not found) | Same file | GET `/markets/SOL-USDT/market-data` → 404 |
| Route integration (validation) | Same file | GET `/markets/BTC/market-data` → 422; GET `/markets/BTC%2FUSDT/market-data` → 422 |
| Route integration (server error) | Same file | Patch/stub `GetMarketData.execute` to raise `RuntimeError` → 500 |
| DTO boundary | Same file or dedicated mapper test | Assert JSON response keys match DTO fields; response `symbol` uses slash format; no domain type leakage in `response_model` |
| Domain purity guard | Extend existing pattern | Confirm `src/market_data_be/modules/` and `src/market_data_be/application/` contain no new `fastapi` / `pydantic` imports |

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
- Mapper unit test optional if route tests fully cover field mapping; at minimum one success test asserts decimal-as-string and ISO datetime serialization.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `GET /markets/{symbol}/market-data` route in `routes/market_data.py` |
| REQ-002 | Path parameter accepts hyphen-separated `BASE-QUOTE` (e.g. `BTC-USDT`) |
| REQ-003 | Reuse `parse_url_symbol` to validate URL format and return internal `BASE/QUOTE` |
| REQ-004 | Route handler calls `GetMarketData.execute(internal_symbol)` with slash-separated symbol |
| REQ-005 | `response_model=MarketDataResponse`; handler return type is HTTP DTO |
| REQ-006 | `MarketDataResponse` fields: `symbol`, `current_price`, `order_book`, `series` |
| REQ-007 | `OrderBookResponse` / `OrderLevelResponse` with string `price` and `quantity` |
| REQ-008 | `CandleSeriesResponse` with `timeframe` and `candles` |
| REQ-009 | `CandleResponse` required and optional fields |
| REQ-010 | Mapper serializes `Decimal` fields as strings |
| REQ-011 | Mapper serializes candle datetimes as ISO 8601 UTC strings |
| REQ-012 | `map_market_data_to_response` in `mappers/market_data.py` |
| REQ-013 | Response `symbol` field uses slash-separated format from `MarketData.symbol` |
| REQ-014 | `create_app()` registers market-data router |
| REQ-015 | `build_get_market_data()` wires `MockMarketDataProvider` into `GetMarketData` |
| REQ-016 | Exception handler for `MarketDataNotFoundError` → 404 |
| REQ-017 | `parse_url_symbol` + 422 mapping for format failures |
| REQ-018 | Handlers for `MarketDataDeserializationError` and generic `Exception` → 500 |
| REQ-019 | Integration tests for `BTC-USDT` and `ETH-USDT` URL paths resolving to fixture symbols |
| REQ-020 | Reuse existing `parse_url_symbol` without duplicating validation rules |
| NFR-001 | All FastAPI/Pydantic code under `src/market_data_be/infrastructure/http/` only |
| NFR-002 | Application layer unchanged; no HTTP imports added |
| NFR-003 | Tests in `src/market_data_be/infrastructure/tests/test_market_data_route.py` using `TestClient` |
| NFR-004 | Typed DTOs, mapper, and route handler signatures |
| NFR-005 | No edits to `get_market_data.py`, provider, domain models, or fixtures |
| NFR-006 | No auth, WebSocket, or live provider adapters |
| NFR-007 | Paths under `src/market_data_be/` per ADR-0001 |
