# Tasks

## Amendments (2026-07-09)

> Historical tasks below reflect the original implementation. Post-refactor equivalents:

| Original task intent | Current location |
|---------------------|------------------|
| HTTP DTOs / mapper / routes | `src/market_data_be/infrastructure/http/` (unchanged responsibility) |
| `map_*` from `MarketClassification` | Maps from `ClassificationResult` |
| `build_classify_market()` wires four classifiers | Wires `MarketClassificationEngine()` |
| Package discovery via manual `package-dir` | `[tool.setuptools.packages.find] where = ["src"]` |

See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md).

---

## Implementation Tasks



Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.



- [x] Add infrastructure HTTP subpackages (`dtos/`, `mappers/`, `validation/`) with `__init__.py` files; update `pyproject.toml` setuptools discovery if new packages are not auto-discovered (REQ-005, REQ-008, NFR-004)



- [x] Implement `parse_url_symbol` in `src/infrastructure/http/validation/symbol.py` validating hyphen-separated `BASE-QUOTE` URL path format, rejecting slash-separated or bare symbols, normalizing to uppercase, and returning internal slash-separated `BASE/QUOTE` (for example, `BTC-USDT` → `BTC/USDT`); raise `ValueError` for invalid input (REQ-002, REQ-003, REQ-013)



- [x] Implement Pydantic DTOs in `src/infrastructure/http/dtos/classification.py`: `ClassificationSignalResponse` (`source`, `score`, `reason`) and `MarketClassificationResponse` (`symbol`, `regime`, `risk`, `economic`, `exposure`) (REQ-005, REQ-006, REQ-009, NFR-004)



- [x] Implement `map_market_classification_to_response` in `src/infrastructure/http/mappers/classification.py` converting `MarketClassification` and nested `ClassificationSignal` tuples to response DTO lists; pass through slash-separated `symbol` unchanged (REQ-005, REQ-008, REQ-009)



- [x] Implement `build_classify_market()` in `src/infrastructure/http/composition.py` wiring `MockMarketDataProvider`, `MarketAnalysisEngine`, and the four real domain classifiers into `ClassifyMarket` (REQ-004, REQ-011, NFR-005)



- [x] Implement classification router at `src/infrastructure/http/routes/classification.py` with `GET /markets/{symbol}/classification` (standard path segment, no `:path` converter), `response_model=MarketClassificationResponse`, URL symbol parsing via `parse_url_symbol`, use case invocation with internal slash symbol, and mapper call (REQ-001, REQ-002, REQ-003, REQ-004, REQ-006, REQ-007, REQ-008)



- [x] Update `src/infrastructure/http/app.py`: wire `ClassifyMarket` via composition module, register classification router, add exception handlers for `MarketDataNotFoundError` (404), `MarketDataDeserializationError` (500), and scoped validation `ValueError` (422); ensure pipeline `ValueError` maps to 500 (REQ-010, REQ-011, REQ-012, REQ-013, REQ-014)



- [x] Add integration tests at `src/infrastructure/tests/test_classification_route.py` using `TestClient(create_app())` covering: `BTC-USDT` and `ETH-USDT` success (200, schema, response `symbol` in slash format, non-empty domains, expected `source` values); URL-to-internal conversion (`BTC-USDT` → `BTC/USDT`); `SOL-USDT` not found (404); invalid formats `BTC` and `BTC%2FUSDT` (422); stubbed unexpected error (500) (REQ-015, AC-001 through AC-009, AC-011, NFR-003)



- [x] Verify domain and application purity: no new `fastapi` or `pydantic` imports under `src/modules/` or `src/application/`; confirm `ClassifyMarket` and classifier modules were not modified (AC-010, AC-012, NFR-001, NFR-002, NFR-005, NFR-006)



- [x] Run full test suite (`pytest` for `src/`) and fix any import or package resolution issues until all acceptance criteria pass (AC-001 through AC-012)

