# Conventions

## Language

- Code, specs, and harness artifacts: **English**
- Existing Spanish architecture docs (`ARQUITECTURA_*.md`) are reference material; new specs follow English per harness governance

## Python

- Python 3.12+
- Strict typing; avoid `Any` and `dict` in public contracts
- `@dataclass(frozen=True, slots=True)` for domain models
- Pure domain: stdlib only inside bounded contexts

## Naming

- Responsibility-driven names: `RegimeClassifier`, `ClassificationSignal`
- Forbidden suffixes: Manager, Helper, Processor, Engine, Utils

## Tests

- Unit tests only
- Location: `<module>/tests/`
- No external dependencies for domain logic tests
- Use pytest as runner

## Specifications

Follow `../harness/governance/spec_guidelines.md`:

- EARS notation in `requirements.md`
- REQ-NNN identifiers
- Traceability across requirements, design, tasks, code, and tests

## Git

- One feature per harness workflow cycle
- Commits after Implementation stage completes and review approves (project policy)
