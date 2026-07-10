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

- `src/application/models/market_classification.py` — `MarketClassification` output aggregate
- `src/application/mappers/assessment_to_classification.py` — repaired domain-to-domain mapper
- `src/application/use_cases/classify_market.py` — pipeline orchestration use case
- `src/application/tests/test_assessment_to_classification.py` — mapper unit tests
- `src/application/tests/test_classify_market.py` — use case unit + integration tests

## Review

**Decision:** APPROVED

All 17 requirements, 7 NFRs, and 8 acceptance criteria passed. 81/81 tests green. Domain modules remain decoupled.

## Usage

```python
from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.classification.classifiers.regime import RegimeClassifier
from market_data_be.modules.classification.classifiers.risk import RiskClassifier
from market_data_be.modules.classification.classifiers.economic import EconomicClassifier
from market_data_be.modules.classification.classifiers.exposure import ExposureClassifier

use_case = ClassifyMarket(
    provider=MockMarketDataProvider(),
    engine=MarketAnalysisEngine(),
    regime_classifier=RegimeClassifier(),
    risk_classifier=RiskClassifier(),
    economic_classifier=EconomicClassifier(),
    exposure_classifier=ExposureClassifier(),
)
result = use_case.execute("BTC/USDT")
```
