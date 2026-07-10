# Design

## Amendments (2026-07-09)

> Supersedes outdated paths and types. See [ADR-0001](../../knowledge/adr/0001-package-layout-and-domain-facades.md).

| Spec reference | Current code |
|----------------|--------------|
| `src/application/`, `src/modules/` | `src/market_data_be/application/`, `src/market_data_be/modules/` |
| `MarketClassification` in `application/models/` | `ClassificationResult` in `modules/classification/models/` |
| `ClassificationInputs` bundles mapper output | `to_classification_inputs(analysis)` in application mapper |
| Four classifiers in `ClassifyMarket` | `MarketClassificationEngine` facade |
| Individual classifier injection rationale | Facade mirrors `MarketAnalysisEngine`; classifiers are internal to classification module |

**New classification module files:** `market_classification_engine.py`, `models/classification_inputs.py`, `models/classification_result.py`, `tests/test_market_classification_engine.py`.

---

## Overview

Add a `ClassifyMarket` application use case that wires together existing components: `MarketDataProvider` (feature 3), `MarketAnalysisEngine` (analysis domain), `assessment_to_classification` mapper (application layer, repaired imports), and the four classification domain classifiers. Introduce `MarketClassification` as the application-level output aggregating per-domain `ClassificationSignal` tuples. Domain modules are unchanged in behavior; only application orchestration and mapper corrections are in scope.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility in this feature |
|-------|------|--------------------------------|
| Analysis domain | `src/modules/analysis/` | `MarketAnalysisEngine.analyze()` produces `AnalysisResult`; **no changes** to algorithms |
| Classification domain | `src/modules/classification/` | Classifiers consume `*ClassifierInput`, emit `ClassificationSignal`; **no changes** |
| Application | `src/application/` | Mapper repair, output model, `ClassifyMarket` use case |
| Infrastructure | `src/infrastructure/market_data/` | `MockMarketDataProvider` reused for tests; **no changes** |

### New and modified components

```
src/
├── application/
│   ├── models/
│   │   ├── __init__.py
│   │   └── market_classification.py     # MarketClassification output type
│   ├── mappers/
│   │   └── assessment_to_classification.py  # FIX imports; domain-to-domain mapping
│   ├── use_cases/
│   │   └── classify_market.py           # ClassifyMarket pipeline use case
│   └── tests/
│       ├── test_assessment_to_classification.py
│       └── test_classify_market.py
```

### Placement rationale

| Decision | Rationale | Requirements |
|----------|-----------|--------------|
| Use case `ClassifyMarket` in `src/application/use_cases/` | Follows `GetMarketData` pattern; orchestration belongs in application layer | REQ-001, REQ-015 |
| Mapper in `src/application/mappers/` | Bridges two isolated bounded contexts without coupling them | REQ-007, NFR-001, NFR-002 |
| Output type in `src/application/models/` | Application-level aggregate distinct from domain `ClassificationSignal` and future REST DTOs (feature 5) | REQ-013, NFR-007 |
| No `application.models.assessment` or `application.models.classification` | Eliminates broken intermediate layer; mapper reads/writes domain types directly | REQ-008 |
| Individual classifier injection | Mirrors `MarketAnalysisEngine` optional sub-component pattern; enables test doubles per classifier | REQ-011, REQ-015 |

### Out of scope (deferred)

- REST API endpoints and HTTP DTO serialization (feature 5: `classification-api`)
- Modifications to analysis analyzers, synthesis, or classification algorithms
- New market data sources beyond existing `MarketDataProvider` adapters
- Wiring the pipeline into FastAPI dependency injection (feature 5)

## Data Flow

### End-to-end pipeline

```
Caller
  │
  │  execute(symbol, market_data?, portfolio_state?)
  ▼
ClassifyMarket (application use case)
  │
  ├─► [if market_data is None] MarketDataProvider.get_market_data(symbol)
  │         │
  │         ▼
  │     MarketData
  │
  ├─► MarketAnalysisEngine.analyze(market_data, portfolio_state)
  │         │
  │         ▼
  │     AnalysisResult
  │       ├── regime: RegimeAssessment
  │       ├── risk: RiskAssessment
  │       ├── economic: EconomicAssessment
  │       ├── exposure: ExposureProfile
  │       └── catalog: CatalogResult  ──► NOT passed to classifiers
  │
  ├─► assessment_to_classification mapper
  │       ├── to_regime_classifier_input(regime)
  │       ├── to_risk_classifier_input(risk)
  │       ├── to_economic_classifier_input(economic)
  │       └── to_exposure_classifier_input(exposure)
  │         │
  │         ▼
  │     RegimeClassifierInput, RiskClassifierInput,
  │     EconomicClassifierInput, ExposureClassifierInput
  │
  ├─► RegimeClassifier.classify(regime_input)    ──► tuple[ClassificationSignal, ...]
  ├─► RiskClassifier.classify(risk_input)      ──► tuple[ClassificationSignal, ...]
  ├─► EconomicClassifier.classify(econ_input)  ──► tuple[ClassificationSignal, ...]
  └─► ExposureClassifier.classify(exp_input)   ──► tuple[ClassificationSignal, ...]
          │
          ▼
      MarketClassification(symbol, regime_signals, risk_signals, ...)
          │
          ▼
      returned to caller
```

### Module isolation (enforced)

```
src/modules/analysis/          src/modules/classification/
        │                                │
        │  no imports                    │  no imports
        ▼                                ▼
        └──────────► src/application/ ◄──┘
                     (mapper + use case)
```

## Interfaces

### `assessment_to_classification` mapper

**Location:** `src/application/mappers/assessment_to_classification.py`

**Import correction:** Replace all `market_data_be.application.models.*` imports with:

| Source module | Types imported |
|---------------|----------------|
| `market_data_be.modules.analysis.models.assessments` | `RegimeAssessment`, `RiskAssessment`, `EconomicAssessment`, `ExposureProfile` |
| `market_data_be.modules.classification.models.inputs.regime` | `RegimeClassifierInput`, `RegimeLabel` |
| `market_data_be.modules.classification.models.inputs.risk` | `RiskClassifierInput` |
| `market_data_be.modules.classification.models.inputs.economic` | `EconomicClassifierInput` |
| `market_data_be.modules.classification.models.inputs.exposure` | `ExposureClassifierInput` |

**Public functions (unchanged signatures, corrected types):**

```python
def to_regime_classifier_input(assessment: RegimeAssessment) -> RegimeClassifierInput:
    return RegimeClassifierInput(regime=RegimeLabel(assessment.regime.value))


def to_risk_classifier_input(assessment: RiskAssessment) -> RiskClassifierInput:
    return RiskClassifierInput(score=assessment.score)


def to_economic_classifier_input(assessment: EconomicAssessment) -> EconomicClassifierInput:
    return EconomicClassifierInput(edge=assessment.edge)


def to_exposure_classifier_input(profile: ExposureProfile) -> ExposureClassifierInput:
    return ExposureClassifierInput(available_capacity_pct=profile.available_capacity_pct)
```

| Function | Input field used | Output field | Enum translation |
|----------|------------------|--------------|------------------|
| `to_regime_classifier_input` | `assessment.regime` (`MarketRegime`) | `RegimeClassifierInput.regime` (`RegimeLabel`) | `RegimeLabel(assessment.regime.value)` — both enums share identical string values |
| `to_risk_classifier_input` | `assessment.score` | `RiskClassifierInput.score` | Direct |
| `to_economic_classifier_input` | `assessment.edge` | `EconomicClassifierInput.edge` | Direct |
| `to_exposure_classifier_input` | `profile.available_capacity_pct` | `ExposureClassifierInput.available_capacity_pct` | Direct |

Fields not mapped (e.g., `reasons`, `components`, `insufficient_data`) are intentionally excluded — classifiers operate on the minimal input DTO contract only.

### `MarketClassification` application output

**Location:** `src/application/models/market_classification.py`

```python
from dataclasses import dataclass

from market_data_be.modules.classification.models.signal import ClassificationSignal


@dataclass(frozen=True, slots=True)
class MarketClassification:
    symbol: str
    regime: tuple[ClassificationSignal, ...]
    risk: tuple[ClassificationSignal, ...]
    economic: tuple[ClassificationSignal, ...]
    exposure: tuple[ClassificationSignal, ...]
```

| Attribute | Type | Source |
|-----------|------|--------|
| `symbol` | `str` | `AnalysisResult.symbol` (same as input `MarketData.symbol`) |
| `regime` | `tuple[ClassificationSignal, ...]` | `RegimeClassifier.classify(...)` |
| `risk` | `tuple[ClassificationSignal, ...]` | `RiskClassifier.classify(...)` |
| `economic` | `tuple[ClassificationSignal, ...]` | `EconomicClassifier.classify(...)` |
| `exposure` | `tuple[ClassificationSignal, ...]` | `ExposureClassifier.classify(...)` |

This type is an application concern. Feature 5 will map it to REST DTOs; this feature does not serialize to JSON.

### `ClassifyMarket` use case

**Location:** `src/application/use_cases/classify_market.py`

```python
class ClassifyMarket:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        engine: MarketAnalysisEngine,
        regime_classifier: RegimeClassifier,
        risk_classifier: RiskClassifier,
        economic_classifier: EconomicClassifier,
        exposure_classifier: ExposureClassifier,
    ) -> None:
        ...

    def execute(
        self,
        symbol: str,
        *,
        market_data: MarketData | None = None,
        portfolio_state: PortfolioState | None = None,
    ) -> MarketClassification:
        ...
```

| Attribute | Value |
|-----------|-------|
| Constructor dependencies | `MarketDataProvider`, `MarketAnalysisEngine`, four classifier instances |
| Primary method | `execute(symbol, *, market_data=None, portfolio_state=None) -> MarketClassification` |
| Data resolution | If `market_data` is `None`, call `self._provider.get_market_data(symbol)`; otherwise use supplied `market_data` |
| Analysis | `analysis = self._engine.analyze(resolved_market_data, portfolio_state)` |
| Mapping | Call four mapper functions on `analysis.regime`, `analysis.risk`, `analysis.economic`, `analysis.exposure` |
| Classification | Invoke each injected classifier with mapped input; collect signal tuples |
| Catalog handling | `analysis.catalog` is not read or forwarded |
| Infrastructure imports | **None** (provider is port Protocol only) |

**Orchestration pseudocode:**

```python
resolved = market_data if market_data is not None else self._provider.get_market_data(symbol)
analysis = self._engine.analyze(resolved, portfolio_state)

regime_signals = self._regime_classifier.classify(
    to_regime_classifier_input(analysis.regime)
)
risk_signals = self._risk_classifier.classify(
    to_risk_classifier_input(analysis.risk)
)
economic_signals = self._economic_classifier.classify(
    to_economic_classifier_input(analysis.economic)
)
exposure_signals = self._exposure_classifier.classify(
    to_exposure_classifier_input(analysis.exposure)
)

return MarketClassification(
    symbol=analysis.symbol,
    regime=regime_signals,
    risk=risk_signals,
    economic=economic_signals,
    exposure=exposure_signals,
)
```

### Classifier contract (existing, unchanged)

**Location:** `src/modules/classification/contracts/classifier.py`

```python
class Classifier(Protocol[TAssessment]):
    def classify(self, assessment: TAssessment) -> tuple[ClassificationSignal, ...]:
        ...
```

Concrete classifiers (`RegimeClassifier`, `RiskClassifier`, `EconomicClassifier`, `ExposureClassifier`) already satisfy this protocol with their respective `*ClassifierInput` types.

## Data Model

### Types involved (no new domain entities)

```
MarketData (analysis)
    │
    ▼
AnalysisResult (analysis)
├── RegimeAssessment ──► RegimeClassifierInput ──► ClassificationSignal(s)
├── RiskAssessment   ──► RiskClassifierInput   ──► ClassificationSignal(s)
├── EconomicAssessment ─► EconomicClassifierInput ► ClassificationSignal(s)
├── ExposureProfile  ──► ExposureClassifierInput ──► ClassificationSignal(s)
└── CatalogResult    ──► (not used in pipeline)

Aggregated at application layer:
MarketClassification
├── symbol: str
├── regime: tuple[ClassificationSignal, ...]
├── risk: tuple[ClassificationSignal, ...]
├── economic: tuple[ClassificationSignal, ...]
└── exposure: tuple[ClassificationSignal, ...]
```

### Regime enum correspondence

Both enums use identical string values; mapping is value-based, not name-based inference:

| `MarketRegime` (analysis) | `RegimeLabel` (classification) |
|---------------------------|--------------------------------|
| `TREND_UP` | `TREND_UP` |
| `TREND_DOWN` | `TREND_DOWN` |
| `RANGE` | `RANGE` |
| `CHAOTIC` | `CHAOTIC` |
| `NEWS_SPIKE` | `NEWS_SPIKE` |

If analysis introduces a `MarketRegime` value with no `RegimeLabel` counterpart, `RegimeLabel(...)` construction shall raise `ValueError`; the use case does not catch this (caller propagates).

## Error Handling

| Scenario | Component | Behavior |
|----------|-----------|----------|
| Symbol not found / fixture missing | `MarketDataProvider` (e.g., `MockMarketDataProvider`) | Raises `MarketDataNotFoundError`; use case propagates |
| Invalid fixture JSON | `MarketDataProvider` | Raises `MarketDataDeserializationError`; use case propagates |
| Unknown `MarketRegime` value at map time | Mapper (`RegimeLabel(...)`) | Raises `ValueError`; use case propagates |
| Unknown regime at classify time | `RegimeClassifier` | Raises `ValueError`; use case propagates |
| Insufficient market data in analysis | `MarketAnalysisEngine` | Engine returns assessments with `insufficient_data=True`; mapper and classifiers still run on available scalar fields |
| Direct `market_data` override with mismatched symbol | Use case | **No validation** in this feature — `AnalysisResult.symbol` reflects `market_data.symbol`; caller responsibility |
| Successful pipeline | `ClassifyMarket` | Returns `MarketClassification` with all four signal tuples populated |

Recovery: no automatic retry, fallback symbols, or partial-result mode in this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| Mapper unit tests | `src/application/tests/test_assessment_to_classification.py` | Each `to_*` function: correct field mapping; all five regime enum values translate to matching `RegimeLabel` |
| Use case unit tests (delegation) | `src/application/tests/test_classify_market.py` | Fake `MarketDataProvider` + stub `MarketAnalysisEngine` + stub classifiers verify call order and that classifiers receive mapped inputs, not raw assessments |
| Use case unit tests (direct data) | Same file | `execute(symbol, market_data=...)` skips provider; provider `get_market_data` not called |
| Use case integration tests | Same file | `MockMarketDataProvider` + real `MarketAnalysisEngine` + real classifiers against `BTC/USDT` and `ETH/USDT` fixtures |
| Domain purity guard | Manual / test import check | Confirm no cross-imports between `src/modules/analysis/` and `src/modules/classification/` |

### Test doubles

**Stub engine** (unit tests — verifies delegation without running analyzers):

```python
class StubMarketAnalysisEngine:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self.last_market_data: MarketData | None = None
        self.last_portfolio_state: PortfolioState | None = None

    def analyze(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState | None = None,
    ) -> AnalysisResult:
        self.last_market_data = market_data
        self.last_portfolio_state = portfolio_state
        return self._result
```

**Recording classifier** (unit tests — verifies input type):

```python
class RecordingClassifier:
    def __init__(self) -> None:
        self.last_input: object | None = None

    def classify(self, assessment: object) -> tuple[ClassificationSignal, ...]:
        self.last_input = assessment
        return (ClassificationSignal(source="test", score=0.0, reason="stub"),)
```

**Integration test wiring:**

```python
use_case = ClassifyMarket(
    provider=MockMarketDataProvider(),
    engine=MarketAnalysisEngine(),
    regime_classifier=RegimeClassifier(),
    risk_classifier=RiskClassifier(),
    economic_classifier=EconomicClassifier(),
    exposure_classifier=ExposureClassifier(),
)
result = use_case.execute("BTC/USDT")
assert result.symbol == "BTC/USDT"
assert len(result.regime) >= 1
assert result.regime[0].source == "regime"
# ... analogous assertions for risk, economic, exposure sources
```

### Coverage expectations

- All four mapper functions tested with representative assessment instances.
- Regime enum translation tested for every `MarketRegime` member.
- Use case verifies provider called when `market_data` omitted; not called when supplied.
- Use case verifies `MarketAnalysisEngine.analyze` receives correct arguments.
- Use case verifies classifiers never receive analysis assessment types (recording classifier asserts `isinstance` on `*ClassifierInput`).
- Integration tests pass for both fixture symbols.
- No new tests under domain module directories required for this feature (application-layer tests only).

## Package configuration

Update `pyproject.toml` `[tool.setuptools]` packages list to include:

- `market_data_be.application.models`

No other package entries are required; `application.mappers` and `application.use_cases` are already listed.

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | `ClassifyMarket` use case orchestrates full pipeline |
| REQ-002 | `execute(symbol, ...)` primary input |
| REQ-003 | Provider delegation when `market_data is None` |
| REQ-004 | Skip provider when `market_data` supplied |
| REQ-005 | Call existing `MarketAnalysisEngine.analyze` |
| REQ-006 | Optional `portfolio_state` forwarded to engine |
| REQ-007 | Mapper module with four public functions |
| REQ-008 | Domain-to-domain imports in mapper |
| REQ-009 | `RegimeLabel(assessment.regime.value)` translation |
| REQ-010 | Scalar field mapping table per function |
| REQ-011 | Classifiers invoked with `*ClassifierInput` only |
| REQ-012 | `analysis.catalog` excluded from pipeline |
| REQ-013 | `MarketClassification` application output type |
| REQ-014 | `execute` returns `MarketClassification` |
| REQ-015 | Constructor injection for all dependencies |
| REQ-016 | Integration test with `BTC/USDT` fixture |
| REQ-017 | Integration test with `ETH/USDT` fixture |
| NFR-001 | No classification imports in analysis module |
| NFR-002 | No analysis imports in classification module |
| NFR-003 | Domain stdlib-only unchanged |
| NFR-004 | Strict types on use case, mapper, output model |
| NFR-005 | Tests under `src/application/tests/` |
| NFR-006 | Name `ClassifyMarket`, not `*Manager`/`*Helper` |
| NFR-007 | No HTTP routes added |
