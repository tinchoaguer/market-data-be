# Requirements

## Amendments (2026-07-09)

> See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md).

- REQ-013 / AC-006: aggregated output is `ClassificationResult` under `modules/classification/models/`, not `MarketClassification` under `application/models/`.
- REQ-011 / AC-001: `ClassifyMarket` injects `MarketClassificationEngine`, not four classifier instances.
- All `src/application/` and `src/modules/` paths → `src/market_data_be/...`.

---

## Overview

Connect the deterministic analysis module (`MarketAnalysisEngine`) with the classification module through an application-layer orchestration use case. Analysis produces domain assessments; the existing `assessment_to_classification` mapper translates those assessments into classification `*ClassifierInput` DTOs; classifiers consume only those DTOs and emit `ClassificationSignal` instances. The analysis and classification bounded contexts remain decoupled — neither imports the other.

## Goals

- Orchestrate end-to-end flow: retrieve `MarketData` (via port or direct injection), run analysis, map assessments, invoke all four classifiers.
- Repair and clarify `src/application/mappers/assessment_to_classification.py` so it maps analysis domain assessment types directly to classification input DTOs (no intermediate `application.models` layer).
- Introduce an application-level aggregated output type for combined classification signals (not a REST DTO).
- Demonstrate constructor-based dependency injection for the analysis engine, classifiers, and optional market data provider.
- Enable unit testing with mock provider, fixture `MarketData`, and test doubles without modifying domain module algorithms.

## Functional Requirements

```text
REQ-001

The system shall provide an application use case that orchestrates market data retrieval (when not supplied directly), deterministic analysis, assessment mapping, and classification into a single pipeline entry point.
```

```text
REQ-002

The pipeline use case shall accept a trading `symbol` string (slash-separated pair notation, e.g., `BTC/USDT`) as its primary input.
```

```text
REQ-003

When `MarketData` is not supplied by the caller, the pipeline use case shall retrieve `MarketData` for the given symbol by delegating to an injected `MarketDataProvider` port.
```

```text
REQ-004

When `MarketData` is supplied by the caller, the pipeline use case shall use the supplied instance and shall not call the `MarketDataProvider` port.
```

```text
REQ-005

The pipeline use case shall invoke `MarketAnalysisEngine.analyze(market_data, portfolio_state)` using the existing analysis engine without modifying analyzer or synthesis algorithms.
```

```text
REQ-006

The pipeline use case shall accept an optional `PortfolioState`; when omitted, the engine shall apply its existing default portfolio state behavior.
```

```text
REQ-007

The system shall provide mapper functions in `src/application/mappers/assessment_to_classification.py` that transform analysis domain assessments into classification `*ClassifierInput` DTOs.
```

```text
REQ-008

The mapper shall accept `RegimeAssessment`, `RiskAssessment`, `EconomicAssessment`, and `ExposureProfile` from `market_data_be.modules.analysis.models.assessments` and produce `RegimeClassifierInput`, `RiskClassifierInput`, `EconomicClassifierInput`, and `ExposureClassifierInput` from `market_data_be.modules.classification.models.inputs` respectively.
```

```text
REQ-009

The mapper shall translate analysis `MarketRegime` enum values to classification `RegimeLabel` enum values by matching their string values (e.g., `MarketRegime.TREND_UP` → `RegimeLabel.TREND_UP`).
```

```text
REQ-010

The mapper shall map `RegimeAssessment.regime` to `RegimeClassifierInput.regime`, `RiskAssessment.score` to `RiskClassifierInput.score`, `EconomicAssessment.edge` to `EconomicClassifierInput.edge`, and `ExposureProfile.available_capacity_pct` to `ExposureClassifierInput.available_capacity_pct`.
```

```text
REQ-011

The pipeline use case shall invoke `RegimeClassifier`, `RiskClassifier`, `EconomicClassifier`, and `ExposureClassifier` with only the mapped `*ClassifierInput` instances — never with raw analysis assessment types.
```

```text
REQ-012

The pipeline use case shall not pass `AnalysisResult.catalog` or other analysis-only artifacts to any classifier.
```

```text
REQ-013

The system shall define an application-level output type that aggregates classification results for a symbol, including per-domain signal tuples (`regime`, `risk`, `economic`, `exposure`) composed of `ClassificationSignal` instances from the classification domain.
```

```text
REQ-014

The pipeline use case `execute` method shall return the application-level aggregated output type containing the requested symbol and all classifier signal tuples produced by the pipeline.
```

```text
REQ-015

The pipeline use case shall depend on `MarketAnalysisEngine`, the four classifier instances, and `MarketDataProvider` exclusively through constructor injection.
```

```text
REQ-016

When executed with `MockMarketDataProvider` and fixture data for `BTC/USDT`, the pipeline shall complete without error and return a `MarketClassification` (or equivalent application output) whose `symbol` equals `BTC/USDT` with non-empty signal tuples for all four domains.
```

```text
REQ-017

When executed with `MockMarketDataProvider` and fixture data for `ETH/USDT`, the pipeline shall complete without error and return aggregated classification output whose `symbol` equals `ETH/USDT`.
```

## Non-Functional Requirements

```text
NFR-001

The analysis module (`src/modules/analysis/`) shall not import any symbol from the classification module or from classification mapper output types.
```

```text
NFR-002

The classification module (`src/modules/classification/`) shall not import any symbol from the analysis module.
```

```text
NFR-003

Domain modules under `src/modules/analysis/` and `src/modules/classification/` shall remain stdlib-only; no Pydantic, FastAPI, SQLAlchemy, or other third-party libraries inside domain code.
```

```text
NFR-004

Public application contracts (use case, mapper functions, application output type) shall use strict typing with no `Any` in public method signatures or return types.
```

```text
NFR-005

Unit tests for the mapper and pipeline use case shall reside under `src/application/tests/` and run with pytest.
```

```text
NFR-006

Naming shall follow project conventions: responsibility-driven names; forbidden suffixes include Manager, Helper, Processor, Engine, and Utils (existing `MarketAnalysisEngine` in the analysis domain is unchanged).
```

```text
NFR-007

The feature shall not expose REST API endpoints or HTTP routes; API exposure is deferred to feature 5 (`classification-api`).
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001, REQ-002, REQ-014, REQ-015):** A `ClassifyMarket` use case exists under `src/application/use_cases/` with constructor-injected `MarketDataProvider`, `MarketAnalysisEngine`, and four classifiers; `execute(symbol, ...)` returns the application aggregated output type.
- [ ] **AC-002 (REQ-003, REQ-004):** Unit tests verify the use case retrieves data via the provider when `market_data` is omitted, and skips the provider when `market_data` is supplied directly.
- [ ] **AC-003 (REQ-005, REQ-006):** Unit tests verify the use case calls `MarketAnalysisEngine.analyze` with the resolved `MarketData` and optional `PortfolioState`.
- [ ] **AC-004 (REQ-007, REQ-008, REQ-009, REQ-010):** `assessment_to_classification.py` imports analysis assessment types and classification input DTOs from domain modules only (no `market_data_be.application.models.*` imports); mapper unit tests cover all four mapping functions including regime enum translation.
- [ ] **AC-005 (REQ-011, REQ-012, NFR-001, NFR-002):** Classifiers receive only `*ClassifierInput` types; `src/modules/analysis/` and `src/modules/classification/` contain no cross-module imports.
- [ ] **AC-006 (REQ-013):** Application output type (e.g., `MarketClassification`) exists under `src/application/models/` with `symbol` and per-domain `tuple[ClassificationSignal, ...]` fields.
- [ ] **AC-007 (REQ-016, REQ-017):** Integration-style application tests using `MockMarketDataProvider` and real fixtures succeed for `BTC/USDT` and `ETH/USDT`.
- [ ] **AC-008 (NFR-003, NFR-004, NFR-006, NFR-007):** Domain modules remain stdlib-only; public APIs are strictly typed; no new HTTP endpoints; naming avoids forbidden suffixes.
