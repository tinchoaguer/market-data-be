# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Implement `AnalyzeMarket` use case in `src/market_data_be/application/use_cases/analyze_market.py`: constructor-inject `MarketDataProvider` and `MarketAnalysisEngine`; `execute(symbol)` retrieves market data then calls `engine.analyze(market_data)` without an explicit portfolio state; return domain `AnalysisResult` (REQ-004, REQ-005, REQ-018, NFR-002, NFR-005)

- [x] Add application unit/integration tests in `src/market_data_be/application/tests/test_analyze_market.py` covering provider→engine delegation (stub/fake doubles) and real `MockMarketDataProvider` + `MarketAnalysisEngine` success for `BTC/USDT` and `ETH/USDT` (REQ-004, REQ-016, REQ-018, NFR-008, AC-005, AC-011)

- [x] Implement Pydantic DTOs in `src/market_data_be/infrastructure/http/dtos/analysis.py`: nested assessment/catalog response models mirroring public domain fields, plus `MarketAnalysisResponse` with `symbol`, `regime`, `risk`, `economic`, `exposure`, and `catalog` (REQ-006, REQ-007, REQ-008, REQ-010, NFR-004)

- [x] Implement `map_analysis_result_to_response` in `src/market_data_be/infrastructure/http/mappers/analysis.py` converting domain `AnalysisResult` (and nested assessments/catalog) to response DTOs; serialize enums via `.value`; pass through slash-separated `symbol` unchanged (REQ-006, REQ-008, REQ-009, REQ-010)

- [x] Add `build_analyze_market()` in `src/market_data_be/infrastructure/http/composition.py` wiring `MockMarketDataProvider` and `MarketAnalysisEngine` into `AnalyzeMarket`; expose a FastAPI dependency accessor for the use case instance (REQ-005, REQ-012, NFR-005)

- [x] Implement analysis router at `src/market_data_be/infrastructure/http/routes/analysis.py` with `GET /markets/{symbol}/analysis` (standard path segment, no `:path` converter), `response_model=MarketAnalysisResponse`, URL symbol parsing via existing `parse_url_symbol`, use case invocation with internal slash symbol, and mapper call (REQ-001, REQ-002, REQ-003, REQ-005, REQ-007, REQ-009, REQ-017)

- [x] Update `src/market_data_be/infrastructure/http/app.py`: wire `AnalyzeMarket` via composition, register analysis router, and ensure existing exception handlers cover `MarketDataNotFoundError` (404), `MarketDataDeserializationError` (500), scoped validation `ValueError` (422), and generic failures (500) for the new route (REQ-011, REQ-012, REQ-013, REQ-014, REQ-015)

- [x] Add integration tests at `src/market_data_be/infrastructure/tests/test_analysis_route.py` using `TestClient(create_app())` covering: `BTC-USDT` and `ETH-USDT` success (200, schema, slash-format `symbol`, present assessments/catalog, enum-as-string); URL-to-internal conversion (`BTC-USDT` → `BTC/USDT`); `SOL-USDT` not found (404); invalid formats `BTC` and `BTC%2FUSDT` (422); stubbed unexpected error (500) (REQ-016, AC-001 through AC-009, AC-011, NFR-003)

- [x] Verify domain and application purity: no new `fastapi` or `pydantic` imports under `src/market_data_be/modules/`; no FastAPI/Pydantic HTTP DTO imports in application; confirm `MarketAnalysisEngine` algorithms, provider/port modules, domain analysis model definitions, and fixture JSON files were not modified (AC-010, AC-012, NFR-001, NFR-002, NFR-005, NFR-006, NFR-007)

- [x] Run full test suite (`pytest`) and fix any import or package resolution issues until all acceptance criteria pass (AC-001 through AC-012)
