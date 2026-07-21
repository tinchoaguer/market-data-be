# Architecture

## Core Architectural Rules (Python 3.12+ | Domain-Driven Isolation)

## 1. Architectural Style & Boundaries (Modular Monolith)
- Every module is a self-contained Bounded Context focused on a specific domain capability.
- Modules must be completely isolated, decoupled, and share zero databases or global state with other modules.
- Pure Domain: Module internals must be pure domain code using Python's standard library. Third-party libraries for validation, typing, or frameworks (e.g., Pydantic, Pandas, FastAPI, SQLAlchemy) are Strictly FORBIDDEN inside the domain layer.

## 2. Infrastructure & Orchestration (Outside the Modules)
- Infrastructure (APIs, DB Persistence, Event Brokers, Third-Party Library integrations like Pydantic) lives OUTSIDE the domain modules.
- Use Cases (Application Layer) orchestrate the flow: they fetch data, handle third-party serialization if needed, pass native structures to the domain modules for pure calculation, and save/broadcast results.
- If a module is pure calculus (like 'classification'), it must NOT contain infrastructure directories, repositories, or event code. It only exposes its native models and pure functions/services.

## 3. Coding Standards & Typing
- Models: All domain models/Value Objects must be `@dataclass(frozen=True, slots=True)` by default.
- Naming: Use exact responsibility-driven names (e.g., 'RegimeClassifier', 'ClassificationSignal'). Strictly FORBIDDEN vague suffixes: 'Manager', 'Helper', 'Processor', 'Engine', 'Utils'.
- Typing: Strict typing using native Python types or local Protocols. Avoid 'Any' or 'dict' in public contracts.

## 4. Testing Strategy
- Tests must be strictly unit tests, reside inside each module's directory (`/tests`), and use only standard testing tools (or pytest as a runner).
- Domain logic must be testable without any external library dependencies or framework setup.
- Risk, oracle strength, and anti-bloat rules: [`testing-policy.md`](testing-policy.md) (authoritative for Spec Writer / Implementer / Reviewer).


## System overview

## System overview

Python backend organized as a **modular monolith** with DDD bounded contexts, packaged as `market_data_be`.

```
market-data-be/                    # repository / PyPI project name
└── src/
    └── market_data_be/            # Python import namespace
        ├── application/           # use cases, ports, anti-corruption mappers
        ├── modules/               # pure domain bounded contexts
        │   ├── analysis/
        │   └── classification/
        └── infrastructure/        # HTTP, market-data adapters, framework code
```

`src/` is a layout container only — it is **not** part of import paths.

## Layer responsibilities

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Domain — analysis** | `src/market_data_be/modules/analysis/` | Deterministic market interpretation; `MarketAnalysisEngine` facade |
| **Domain — classification** | `src/market_data_be/modules/classification/` | Signal classification; `MarketClassificationEngine` facade |
| **Application** | `src/market_data_be/application/` | Orchestration use cases, outbound ports (`MarketDataProvider`), cross-context mappers |
| **Infrastructure** | `src/market_data_be/infrastructure/` | FastAPI, JSON fixtures provider, HTTP DTOs, composition root |
| **Resources** | `resources/` | Static JSON fixtures (not part of the installable package) |

## Domain module symmetry

| Concern | Analysis | Classification |
|---------|----------|----------------|
| Facade | `MarketAnalysisEngine` | `MarketClassificationEngine` |
| Entry method | `analyze(market_data, portfolio_state?)` | `classify(inputs)` |
| Input type | `MarketData` (+ optional `PortfolioState`) | `ClassificationInputs` |
| Output type | `AnalysisResult` | `ClassificationResult` |
| Workers | `analyzers/*` | `classifiers/*` |
| Protocol | (concrete analyzers injected in facade) | `Classifier[T]` in `contracts/` |

Bounded contexts **do not import each other**. The application mapper `assessment_to_classification.to_classification_inputs()` translates `AnalysisResult` → `ClassificationInputs`.

## Application layer

```
application/
├── contracts/
│   └── market_data_provider.py    # outbound port (Protocol)
├── mappers/
│   └── assessment_to_classification.py
├── use_cases/
│   ├── classify_market.py           # provider + both facades
│   └── get_market_data.py
└── tests/
```

### `ClassifyMarket` pipeline

```
MarketDataProvider.get_market_data(symbol)
        → MarketAnalysisEngine.analyze(market_data)
        → to_classification_inputs(analysis)
        → MarketClassificationEngine.classify(inputs)
        → ClassificationResult
```

## Infrastructure layer

```
infrastructure/
├── http/
│   ├── app.py                       # FastAPI factory; uvicorn entry point
│   ├── composition.py               # wires ClassifyMarket for dev/default
│   ├── routes/
│   ├── dtos/                        # Pydantic response models
│   ├── mappers/                     # ClassificationResult → HTTP DTOs
│   └── validation/
├── market_data/
│   ├── mock_provider.py             # MarketDataProvider adapter (JSON fixtures)
│   ├── deserializer.py
│   └── symbol_resolver.py
└── tests/
```

**Composition root** (`infrastructure/http/composition.py`):

```python
ClassifyMarket(
    provider=MockMarketDataProvider(),
    engine=MarketAnalysisEngine(),
    classification_engine=MarketClassificationEngine(),
)
```

## Packaging and imports

- **Project name:** `market-data-be` (`pyproject.toml`)
- **Import package:** `market_data_be`
- **Discovery:** `[tool.setuptools.packages.find] where = ["src"]`
- **Dev install:** `pip install -e ".[dev]"`
- **Run API:** `uvicorn market_data_be.infrastructure.http.app:app`

See [ADR-0001](adr/0001-package-layout-and-domain-facades.md) for the migration from `package-dir` remapping.

## Architectural rules


## Layer responsibilities

| Layer | Path | Responsibility |
|-------|------|----------------|
| **Domain — analysis** | `src/market_data_be/modules/analysis/` | Deterministic market interpretation; `MarketAnalysisEngine` facade |
| **Domain — classification** | `src/market_data_be/modules/classification/` | Signal classification; `MarketClassificationEngine` facade |
| **Application** | `src/market_data_be/application/` | Orchestration use cases, outbound ports (`MarketDataProvider`), cross-context mappers |
| **Infrastructure** | `src/market_data_be/infrastructure/` | FastAPI, JSON fixtures provider, HTTP DTOs, composition root |
| **Resources** | `resources/` | Static JSON fixtures (not part of the installable package) |

## Domain module symmetry

| Concern | Analysis | Classification |
|---------|----------|----------------|
| Facade | `MarketAnalysisEngine` | `MarketClassificationEngine` |
| Entry method | `analyze(market_data, portfolio_state?)` | `classify(inputs)` |
| Input type | `MarketData` (+ optional `PortfolioState`) | `ClassificationInputs` |
| Output type | `AnalysisResult` | `ClassificationResult` |
| Workers | `analyzers/*` | `classifiers/*` |
| Protocol | (concrete analyzers injected in facade) | `Classifier[T]` in `contracts/` |

Bounded contexts **do not import each other**. The application mapper `assessment_to_classification.to_classification_inputs()` translates `AnalysisResult` → `ClassificationInputs`.

## Application layer

```
application/
├── contracts/
│   └── market_data_provider.py    # outbound port (Protocol)
├── mappers/
│   └── assessment_to_classification.py
├── use_cases/
│   ├── classify_market.py           # provider + both facades
│   └── get_market_data.py
└── tests/
```

### `ClassifyMarket` pipeline

```
MarketDataProvider.get_market_data(symbol)
        → MarketAnalysisEngine.analyze(market_data)
        → to_classification_inputs(analysis)
        → MarketClassificationEngine.classify(inputs)
        → ClassificationResult
```

## Infrastructure layer

```
infrastructure/
├── http/
│   ├── app.py                       # FastAPI factory; uvicorn entry point
│   ├── composition.py               # wires ClassifyMarket for dev/default
│   ├── routes/
│   ├── dtos/                        # Pydantic response models
│   ├── mappers/                     # ClassificationResult → HTTP DTOs
│   └── validation/
├── market_data/
│   ├── mock_provider.py             # MarketDataProvider adapter (JSON fixtures)
│   ├── deserializer.py
│   └── symbol_resolver.py
└── tests/
```

**Composition root** (`infrastructure/http/composition.py`):

```python
ClassifyMarket(
    provider=MockMarketDataProvider(),
    engine=MarketAnalysisEngine(),
    classification_engine=MarketClassificationEngine(),
)
```

## Packaging and imports

- **Project name:** `market-data-be` (`pyproject.toml`)
- **Import package:** `market_data_be`
- **Discovery:** `[tool.setuptools.packages.find] where = ["src"]`
- **Dev install:** `pip install -e ".[dev]"`
- **Run API:** `uvicorn market_data_be.infrastructure.http.app:app`

See [ADR-0001](adr/0001-package-layout-and-domain-facades.md) for the migration from `package-dir` remapping.

## Architectural rules

- Domain modules: **stdlib only** — no Pydantic, FastAPI, SQLAlchemy inside `modules/`
- Infrastructure and frameworks live outside domain modules
- Models: `@dataclass(frozen=True, slots=True)` by default
- Tests: unit tests inside each module's `tests/` directory; HTTP integration tests under `infrastructure/tests/`; see [`testing-policy.md`](testing-policy.md)
- Naming: responsibility-driven; avoid Manager, Helper, Processor, Utils (existing `*Engine` facades are grandfathered)

## Related documents

- `.cursorrules`
- [`knowledge/testing-policy.md`](testing-policy.md)
- `knowledge/adr/0001-package-layout-and-domain-facades.md`
- `ARQUITECTURA_MOTOR.md` (Spanish reference — may predate `modules/` layout)
- Feature specs under `specs/` (historical; see **Amendments** sections where present)
