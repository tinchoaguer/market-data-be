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

Follow [`testing-policy.md`](testing-policy.md) (authoritative).

Summary:

- Unit tests by default; location `<layer>/tests/` (HTTP under `infrastructure/tests/`)
- Strong oracles over file count or line coverage
- Domain tests: no FastAPI/Pydantic; pytest as runner
- Do not require one new test file per AC

## Specifications

Follow harness `governance/spec_guidelines.md` (see `HARNESS.md`):

- EARS notation in `requirements.md`
- REQ-NNN identifiers
- Traceability across requirements, design, tasks, code, and tests
- Specs stay inside this PROJECT_ROOT

## Git

- One feature per harness workflow cycle
- Commits after Implementation stage completes and review approves (project policy)
