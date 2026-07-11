# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Implement Pydantic DTOs in `src/market_data_be/infrastructure/http/dtos/market_data.py`: `OrderLevelResponse`, `OrderBookResponse`, `CandleResponse`, `CandleSeriesResponse`, and `MarketDataResponse` with decimal fields as `str` and optional candle fields nullable (REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-013, NFR-004)

- [x] Implement `map_market_data_to_response` in `src/market_data_be/infrastructure/http/mappers/market_data.py` converting domain `MarketData` (and nested order book / series / candles) to response DTOs; serialize `Decimal` via `str(...)`, datetimes as ISO 8601 UTC, and pass through slash-separated `symbol` unchanged (REQ-005, REQ-010, REQ-011, REQ-012, REQ-013)

- [x] Add `build_get_market_data()` in `src/market_data_be/infrastructure/http/composition.py` wiring `MockMarketDataProvider` into `GetMarketData`; expose a FastAPI dependency accessor for the use case instance (REQ-004, REQ-015, NFR-005)

- [x] Implement market-data router at `src/market_data_be/infrastructure/http/routes/market_data.py` with `GET /markets/{symbol}/market-data` (standard path segment, no `:path` converter), `response_model=MarketDataResponse`, URL symbol parsing via existing `parse_url_symbol`, use case invocation with internal slash symbol, and mapper call (REQ-001, REQ-002, REQ-003, REQ-004, REQ-006, REQ-012, REQ-020)

- [x] Update `src/market_data_be/infrastructure/http/app.py`: wire `GetMarketData` via composition, register market-data router, and ensure existing exception handlers cover `MarketDataNotFoundError` (404), `MarketDataDeserializationError` (500), scoped validation `ValueError` (422), and generic failures (500) for the new route (REQ-014, REQ-015, REQ-016, REQ-017, REQ-018)

- [x] Add integration tests at `src/market_data_be/infrastructure/tests/test_market_data_route.py` using `TestClient(create_app())` covering: `BTC-USDT` and `ETH-USDT` success (200, schema, slash-format `symbol`, string decimals, ISO datetimes, non-empty order book/series); URL-to-internal conversion (`BTC-USDT` → `BTC/USDT`); `SOL-USDT` not found (404); invalid formats `BTC` and `BTC%2FUSDT` (422); stubbed unexpected error (500) (REQ-019, AC-001 through AC-009, AC-011, NFR-003)

- [x] Verify domain and application purity: no new `fastapi` or `pydantic` imports under `src/market_data_be/modules/` or `src/market_data_be/application/`; confirm `GetMarketData`, provider/port modules, domain market models, and fixture JSON files were not modified (AC-010, AC-012, NFR-001, NFR-002, NFR-005, NFR-006, NFR-007)

- [x] Run full test suite (`pytest`) and fix any import or package resolution issues until all acceptance criteria pass (AC-001 through AC-012)
