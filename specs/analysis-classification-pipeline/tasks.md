# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Update `pyproject.toml` setuptools package discovery to include `market_data_be.application.models` (REQ-013, NFR-005)

- [x] Create application models package: `src/application/models/__init__.py` and `market_classification.py` defining frozen `MarketClassification` dataclass with `symbol` and four per-domain `tuple[ClassificationSignal, ...]` fields (REQ-013, NFR-004)

- [x] Repair `src/application/mappers/assessment_to_classification.py`: replace broken `market_data_be.application.models.*` imports with analysis assessment types (`RegimeAssessment`, `RiskAssessment`, `EconomicAssessment`, `ExposureProfile`) and classification `*ClassifierInput` / `RegimeLabel` types; preserve the four public mapper function signatures and field mappings (REQ-007, REQ-008, REQ-009, REQ-010)

- [x] Add mapper unit tests at `src/application/tests/test_assessment_to_classification.py` covering all four `to_*` functions, including regime enum translation for every `MarketRegime` value (REQ-007, REQ-009, REQ-010, NFR-005)

- [x] Implement `ClassifyMarket` use case in `src/application/use_cases/classify_market.py`: constructor-inject `MarketDataProvider`, `MarketAnalysisEngine`, and four classifiers; `execute(symbol, *, market_data=None, portfolio_state=None)` resolves data, runs analysis, maps assessments, invokes classifiers, returns `MarketClassification`; do not pass `catalog` to classifiers (REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-011, REQ-012, REQ-014, REQ-015, NFR-001, NFR-004)

- [x] Add use case unit tests at `src/application/tests/test_classify_market.py` with stub engine and recording classifiers: verify provider delegation, direct `market_data` bypass, `analyze` call arguments, and that classifiers receive `*ClassifierInput` instances only (REQ-003, REQ-004, REQ-005, REQ-006, REQ-011, REQ-015, NFR-005)

- [x] Add use case integration tests in `test_classify_market.py` wiring `MockMarketDataProvider`, real `MarketAnalysisEngine`, and real classifiers for `BTC/USDT` and `ETH/USDT` fixtures; assert `MarketClassification.symbol` and non-empty per-domain signal tuples with expected `source` values (`regime`, `risk`, `economic`, `exposure`) (REQ-016, REQ-017, AC-007)

- [x] Verify domain purity: confirm `src/modules/analysis/` contains no imports from `market_data_be.modules.classification` and `src/modules/classification/` contains no imports from `market_data_be.modules.analysis` (NFR-001, NFR-002, AC-005)

- [x] Verify no REST endpoints were added and domain modules remain stdlib-only (NFR-003, NFR-007, AC-008)

- [x] Run full test suite (`pytest` for `src/`) and fix any import or package resolution issues until all acceptance criteria pass (AC-001 through AC-008)
