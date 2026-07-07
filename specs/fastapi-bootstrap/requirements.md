# Requirements

## Overview

Bootstrap the market-data backend as an HTTP service using FastAPI as the ASGI application entry point. This feature establishes the infrastructure layer, declares runtime dependencies, and exposes a single health endpoint to verify the service is operational. Domain modules (`src/modules/analysis/`, `src/modules/classification/`) and the application orchestration layer (`src/application/`) remain unchanged in responsibility; FastAPI and ASGI concerns live exclusively in infrastructure.

## Goals

- Enable local and deployable API execution via a standard ASGI server.
- Introduce a dedicated infrastructure layer that does not pollute domain bounded contexts.
- Provide a verifiable health probe as the sole HTTP surface for this feature.
- Configure project packaging so the HTTP application is importable and runnable from `pyproject.toml`.

## Functional Requirements

```text
REQ-001

The system shall declare FastAPI as a runtime dependency in pyproject.toml.
```

```text
REQ-002

The system shall declare uvicorn as a runtime dependency in pyproject.toml.
```

```text
REQ-003

The system shall provide a FastAPI application factory in the infrastructure layer that returns a configured ASGI application instance.
```

```text
REQ-004

The system shall expose an HTTP GET endpoint at `/health` that responds with status code 200 and a JSON body indicating the service is healthy.
```

```text
REQ-005

The system shall support starting the HTTP application with uvicorn using a documented, reproducible command that references the infrastructure application entry point.
```

```text
REQ-006

The system shall organize source code so that domain logic resides under `src/modules/`, application orchestration under `src/application/`, and HTTP/ASGI concerns under `src/infrastructure/`, with no FastAPI imports inside domain modules.
```

## Non-Functional Requirements

```text
NFR-001

Domain modules under `src/modules/` shall remain free of third-party framework dependencies (FastAPI, Pydantic, SQLAlchemy, or equivalent).
```

```text
NFR-002

The health endpoint shall respond without depending on domain modules, external services, or persistent storage.
```

```text
NFR-003

The HTTP bootstrap shall be compatible with Python 3.12+ and the existing project typing conventions (strict typing, no `Any` in public contracts).
```

```text
NFR-004

Package discovery in pyproject.toml shall map the `src/` layout to the `market_data_be` Python package namespace so infrastructure modules are importable for ASGI server startup.
```

## Acceptance Criteria

- [ ] **AC-001 (REQ-001):** `pyproject.toml` lists `fastapi` under `[project].dependencies` (or an equivalent runtime dependency group used for production execution).
- [ ] **AC-002 (REQ-002):** `pyproject.toml` lists `uvicorn` under `[project].dependencies` (or the same runtime dependency group as AC-001).
- [ ] **AC-003 (REQ-003, REQ-005):** After installing project dependencies, uvicorn starts the application without import errors using the documented startup command.
- [ ] **AC-004 (REQ-004):** `GET /health` returns HTTP 200 with a JSON response body.
- [ ] **AC-005 (REQ-006, NFR-001):** `src/infrastructure/` contains HTTP/ASGI code; `src/modules/analysis/` and `src/modules/classification/` contain no FastAPI or uvicorn imports.
- [ ] **AC-006 (NFR-004):** Infrastructure modules are importable under the `market_data_be` package namespace (e.g., `market_data_be.infrastructure.http.app`).
