# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Implement Pydantic DTOs in `src/infrastructure/http/dtos/market_data.py`: `OrderLevelResponse`, `OrderBookResponse`, `CandleResponse`, `CandleSeriesResponse`, and `MarketDataResponse` with decimal fields as `str` and optional candle fields as nullable (REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, NFR-004)

- [x] Implement `map_market_data_to_response` in `src/infrastructure/http/mappers/market_data.py` converting domain `MarketData` and nested types to response DTOs; serialize `Decimal` via `str(...)`, datetimes as ISO 8601 UTC, and pass through slash-separated `symbol` unchanged (REQ-005, REQ-009, REQ-010, REQ-011)

- [x] Extend `src/infrastructure/http/composition.py` with `build_get_market_data()` wiring `MockMarketDataProvider` into `GetMarketData`; expose a FastAPI dependency accessor for the use case (REQ-004, REQ-013, NFR-005)

- [x] Implement market-data router at `src/infrastructure/http/routes/market_data.py` with `GET /markets/{symbol}/market-data` (standard path segment, no `:path` converter), `response_model=MarketDataResponse`, URL symbol parsing via existing `parse_url_symbol`, use case invocation with internal slash symbol, and mapper call (REQ-001, REQ-002, REQ-003, REQ-004, REQ-006, REQ-010, NFR-007)

- [x] Update `src/infrastructure/http/app.py`: wire `GetMarketData` via composition module, register market-data router, and ensure existing exception handlers cover `MarketDataNotFoundError` (404), `MarketDataDeserializationError` (500), scoped validation `ValueError` (422), and generic `Exception` (500) for this route (REQ-012, REQ-013, REQ-014, REQ-015, REQ-016)

- [x] Add integration tests at `src/infrastructure/tests/test_market_data_route.py` using `TestClient(create_app())` covering: `BTC-USDT` and `ETH-USDT` success (200, schema, response `symbol` in slash format, non-empty order book and series, decimal-as-string and ISO datetime fields); URL-to-internal conversion (`BTC-USDT` → `BTC/USDT`); `SOL-USDT` not found (404); invalid formats `BTC` and `BTC%2FUSDT` (422); stubbed unexpected error (500) (REQ-017, AC-001 through AC-009, AC-011, NFR-003)

- [x] Verify domain and application purity: no new `fastapi` or `pydantic` imports under `src/modules/` or `src/application/`; confirm `GetMarketData`, provider/port modules, domain models, and fixture JSON were not modified; confirm `parse_url_symbol` is reused (not duplicated) (AC-010, AC-012, NFR-001, NFR-002, NFR-005, NFR-006, NFR-007)

- [x] Run full test suite (`pytest` for `src/`) and fix any import or package resolution issues until all acceptance criteria pass (AC-001 through AC-012)
