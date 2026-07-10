# ADR-0001: Package layout alignment and classification facade symmetry

- **Status:** accepted
- **Date:** 2026-07-09
- **Supersedes:** setuptools `package-dir` remapping described in `specs/fastapi-bootstrap/design.md`

## Context

The backend evolved in two steps that left documentation and folder layout out of sync:

1. **Bootstrap packaging** introduced the import namespace `market_data_be` while keeping physical folders at `src/application/`, `src/modules/`, and `src/infrastructure/` via setuptools `package-dir` remapping. This worked but was confusing: the repo is `market-data-be`, imports are `market_data_be.*`, and code lived in sibling folders under `src/`.

2. **Analysis–classification pipeline** placed orchestration in `ClassifyMarket` with four classifier dependencies injected directly, and defined `MarketClassification` as an application output type. Meanwhile `modules/analysis/` already exposed a single facade (`MarketAnalysisEngine`) with its own output aggregate (`AnalysisResult`). The two bounded contexts were asymmetric.

## Decision

### 1. Align filesystem with the Python package

Move all installable code under `src/market_data_be/`:

```
src/market_data_be/
├── application/
├── modules/
│   ├── analysis/
│   └── classification/
└── infrastructure/
```

Configure setuptools with standard discovery:

```toml
[tool.setuptools.packages.find]
where = ["src"]
```

Remove manual `package-dir` remapping and the empty anchor-only layout.

**Import namespace is unchanged:** `market_data_be.application.*`, `market_data_be.modules.*`, `market_data_be.infrastructure.*`.

### 2. Introduce a classification facade symmetric to analysis

Add to `modules/classification/`:

| Artifact | Role | Analysis parallel |
|----------|------|-------------------|
| `MarketClassificationEngine` | Single entry point | `MarketAnalysisEngine` |
| `classify(inputs)` | Public method | `analyze(market_data, ...)` |
| `ClassificationInputs` | Input bundle | `MarketData` (+ optional `PortfolioState` via analysis) |
| `ClassificationResult` | Output aggregate | `AnalysisResult` |
| `classifiers/*` | Workers | `analyzers/*` |
| `contracts/classifier.py` | `Classifier[T]` protocol | (implicit in analysis via concrete analyzers) |

**Module isolation preserved:** classification does not import analysis types. The application mapper (`to_classification_inputs`) remains the anti-corruption layer between `AnalysisResult` and `ClassificationInputs`.

### 3. Slim application orchestration

`ClassifyMarket` now depends on:

- `MarketDataProvider` (application port)
- `MarketAnalysisEngine` (analysis facade)
- `MarketClassificationEngine` (classification facade)

It no longer injects four individual classifiers. `application/models/market_classification.py` is removed; pipeline output is `ClassificationResult` from the classification domain.

### 4. HTTP layer maps domain result to DTOs

`map_market_classification_to_response` accepts `ClassificationResult` (not the removed application type). The Pydantic DTO name `MarketClassificationResponse` is unchanged — it is the HTTP contract only.

## Consequences

### Positive

- Filesystem matches imports; onboarding and tooling are simpler.
- Analysis and classification modules are structurally symmetric.
- `Classifier` protocol is used by the classification facade.
- `pyproject.toml` no longer lists every subpackage manually.
- `resources/tests/` no longer needs `sys.modules` bootstrapping.

### Negative / follow-ups

- Historical feature specs written before this ADR reference old paths and `MarketClassification`; each affected spec carries an **Amendments** section pointing here.
- `MarketAnalysisEngine` and `MarketClassificationEngine` retain the `Engine` suffix (pre-existing; rename is out of scope).
- Fixture path resolution in `MockMarketDataProvider` uses `parents[4]` from its new depth under `src/market_data_be/`.

## References

- `knowledge/architecture.md` — current layout and layer rules
- Spec amendments: `analysis-classification-pipeline`, `classification-api`, `fastapi-bootstrap`, `market-data-provider`
