# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Update `pyproject.toml` setuptools package discovery to include `market_data_be.application.contracts`, `market_data_be.application.use_cases`, `market_data_be.application.tests`, and `market_data_be.infrastructure.market_data` (REQ-001, REQ-003, REQ-006, NFR-005)

- [x] Create application contracts package: `src/application/contracts/__init__.py` and `market_data_provider.py` defining the `MarketDataProvider` Protocol with `get_market_data(self, symbol: str) -> MarketData` (REQ-001, REQ-002, NFR-002)

- [x] Create infrastructure market data package skeleton: `src/infrastructure/market_data/__init__.py` and `errors.py` with `MarketDataNotFoundError` and `MarketDataDeserializationError` (REQ-012, REQ-013)

- [x] Implement `symbol_to_fixture_filename` in `src/infrastructure/market_data/symbol_resolver.py` mapping slash-separated symbols to `{base}_{quote}.json` per README convention; raise `ValueError` on invalid format (REQ-004)

- [x] Implement shared JSON deserializer in `src/infrastructure/market_data/deserializer.py` with public `market_data_from_dict` and helpers (`parse_datetime`, `parse_optional_decimal`, `candle_from_dict`) matching `resources/market_data/README.md` (REQ-006, REQ-007, NFR-003)

- [x] Implement `MockMarketDataProvider` in `src/infrastructure/market_data/mock_provider.py`: resolve symbol, read UTF-8 JSON from configurable `fixtures_dir` (default `resources/market_data/`), deserialize via shared module, implement port structurally (REQ-003, REQ-005, REQ-008, REQ-010, REQ-011)

- [x] Implement `GetMarketData` use case in `src/application/use_cases/get_market_data.py` accepting `MarketDataProvider` via constructor injection; `execute(symbol)` delegates to provider (REQ-009, NFR-001, NFR-004)

- [x] Add infrastructure unit tests at `src/infrastructure/tests/test_symbol_resolver.py` for valid (`BTC/USDT`, `ETH/USDT`) and invalid symbol formats (REQ-004, NFR-005)

- [x] Add infrastructure unit tests at `src/infrastructure/tests/test_deserializer.py` loading fixture JSON and asserting `MarketData` structure and types (REQ-006, REQ-007, NFR-005)

- [x] Add infrastructure unit tests at `src/infrastructure/tests/test_mock_provider.py` covering: successful `BTC/USDT` and `ETH/USDT` retrieval; `MarketDataNotFoundError` for missing/unsupported symbols; `MarketDataDeserializationError` for malformed fixture content (REQ-010, REQ-011, REQ-012, REQ-013, NFR-005)

- [x] Add application unit tests at `src/application/tests/test_get_market_data.py` using a `FakeMarketDataProvider` test double to verify delegation and substitution without infrastructure imports (REQ-009, NFR-004, AC-007)

- [x] Refactor `resources/tests/test_market_data_fixtures.py` to import `market_data_from_dict` from the shared infrastructure deserializer; remove duplicate local mapping functions (REQ-014)

- [x] Verify domain purity: confirm `src/modules/analysis/` and `src/modules/classification/` contain no imports of `market_data_be.infrastructure`, `MockMarketDataProvider`, or `market_data_be.application.contracts` (NFR-001, AC-005)

- [x] Run full test suite (`pytest` for `src/` and `resources/tests/`) and fix any package import or path resolution issues until all acceptance criteria pass (AC-001 through AC-008)
