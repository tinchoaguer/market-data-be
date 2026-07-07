# Architecture

## System Overview

Python trading engine organized as a **modular monolith** with DDD bounded contexts.

The harness operates in this repository only. This document describes where code lives and which paths agents may touch.

## Module Layout

```
src/
├── analysis/          # Market analysis pipeline (engine facade, analyzers, synthesis)
├── classification/    # Classification bounded context (pure domain)
└── application/       # Use cases and mappers (orchestration layer)
```

### analysis

Deterministic market interpretation pipeline. Entry point: `MarketAnalysisEngine`.

- `src/analysis/market_analysis_engine.py` — facade
- `src/analysis/analyzers/` — pure analyzers
- `src/analysis/synthesis/` — catalog builder
- `src/analysis/models/` — domain models
- `src/analysis/tests/` — unit tests

### classification

Isolated classification module. Pure domain only (stdlib).

- `src/classification/classifiers/`
- `src/classification/models/`
- `src/classification/contracts/`

### application

Use cases that orchestrate domain modules and map between layers.

- `src/application/`

## Writable Paths (Implementer)

- `src/**`
- `trading_engine/**/tests/**`

## Readable Paths (Reviewer)

Same as writable paths, plus:

- `pyproject.toml`
- `.cursorrules`

## Architectural Rules

- Domain modules use Python stdlib only — no Pydantic, FastAPI, SQLAlchemy inside domain
- Infrastructure lives outside domain modules
- Models: `@dataclass(frozen=True, slots=True)`
- Tests: unit tests inside each module's `tests/` directory
- Naming: responsibility-driven names; avoid Manager, Helper, Processor, Engine, Utils suffixes

See also:

- `.cursorrules`
- `ARQUITECTURA_MOTOR.md`
- `ARQUITECTURA_DOMINIOS.md`

## Dependencies

- Python 3.12+
- pytest for test runner
- Domain modules: `dependencies = []` (no third-party in pure domain)
