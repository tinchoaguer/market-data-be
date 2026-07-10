# Feature History: analysis-classification-pipeline

```yaml
history:
  - date: 2026-07-08
    feature:
      id: 4
      slug: analysis-classification-pipeline
    workflow_stage: Completed
```

## Summary

Connected the deterministic analysis module with the classification module via application-layer orchestration. The `ClassifyMarket` use case runs the full pipeline from market data retrieval through analysis, assessment mapping, and classification.

## Deliverables

- `src/market_data_be/application/mappers/assessment_to_classification.py` — domain-to-domain mapper (+ `to_classification_inputs`)
- `src/market_data_be/application/use_cases/classify_market.py` — pipeline orchestration use case
- `src/market_data_be/application/tests/test_assessment_to_classification.py` — mapper unit tests
- `src/market_data_be/application/tests/test_classify_market.py` — use case unit + integration tests

> **2026-07-09 refactor:** `MarketClassification` moved to `ClassificationResult` in the classification domain. Added `MarketClassificationEngine` facade. See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md).

## Review

**Decision:** APPROVED

All 17 requirements, 7 NFRs, and 8 acceptance criteria passed. 81/81 tests green. Domain modules remain decoupled.

## Usage

```python
from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.classification.market_classification_engine import (
    MarketClassificationEngine,
)

use_case = ClassifyMarket(
    provider=MockMarketDataProvider(),
    engine=MarketAnalysisEngine(),
    classification_engine=MarketClassificationEngine(),
)
result = use_case.execute("BTC/USDT")  # ClassificationResult
```
