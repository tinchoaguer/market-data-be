# Design

## Overview

Introduce a thin HTTP infrastructure layer under `src/infrastructure/http/` that owns the FastAPI application factory, route registration, and ASGI entry point. Update `pyproject.toml` to declare `fastapi` and `uvicorn` as runtime dependencies and to configure setuptools package discovery for the existing `src/` layout under the `market_data_be` namespace. The only API surface in this feature is `GET /health`, implemented without coupling to domain modules.

## Architecture

### Layer responsibilities

| Layer | Path | Responsibility |
|-------|------|----------------|
| Domain | `src/modules/analysis/`, `src/modules/classification/` | Pure business logic (stdlib only); unchanged by this feature |
| Application | `src/application/` | Use-case orchestration and mappers; unchanged by this feature |
| Infrastructure | `src/infrastructure/http/` | FastAPI app factory, HTTP routes, ASGI entry point |

### New components

```
src/
├── application/                    # existing — no changes required
├── modules/                        # existing — no changes required
│   ├── analysis/
│   └── classification/
└── infrastructure/
    └── http/
        ├── __init__.py
        ├── app.py                  # create_app() factory; module-level `app` for uvicorn
        └── routes/
            ├── __init__.py
            └── health.py           # health router
```

### Component details

**`create_app()` factory (`app.py`)**
- Instantiates `FastAPI` with project metadata (title, version from `pyproject.toml` or a constant).
- Registers the health router.
- Returns the configured `FastAPI` instance.
- Exposes a module-level `app = create_app()` attribute for uvicorn's default import pattern.

**Health router (`routes/health.py`)**
- Defines `APIRouter` with prefix `/health` or a route path `/health` on the root router.
- Handler returns HTTP 200 with a typed response model or plain dict.

**Package layout (`market_data_be`)**
- Add `src/market_data_be/` as the installable package root OR configure `package-dir` mapping so existing `src/application/`, `src/modules/`, and new `src/infrastructure/` resolve under `market_data_be.*` imports (consistent with existing `market_data_be.application` imports in `assessment_to_classification.py`).
- Recommended approach: introduce `src/market_data_be/` as a namespace package containing re-exports or relocate modules under it. **Minimal-change approach for this feature:** configure setuptools `package-dir` so `market_data_be.application` maps to `src/application`, `market_data_be.modules` maps to `src/modules`, and `market_data_be.infrastructure` maps to `src/infrastructure`.

### Dependency configuration (`pyproject.toml`)

| Dependency | Purpose |
|------------|---------|
| `fastapi` | ASGI web framework and routing |
| `uvicorn[standard]` | ASGI server with standard extras (HTTP tooling) |

Update `[tool.setuptools]` to use `find` with `where = ["src"]` and appropriate `package-dir` mappings instead of the placeholder `packages = ["market-data-be"]` entry.

## Data Flow

```
Client
  │
  │  GET /health
  ▼
uvicorn (ASGI server)
  │
  ▼
FastAPI app (infrastructure/http/app.py)
  │
  ▼
health router (infrastructure/http/routes/health.py)
  │
  ▼
HTTP 200 + JSON {"status": "ok"}
```

No domain or application layer participation. The health check is infrastructure-only.

## Interfaces

### HTTP: `GET /health`

| Attribute | Value |
|-----------|-------|
| Method | `GET` |
| Path | `/health` |
| Auth | None |
| Success status | `200` |
| Response `Content-Type` | `application/json` |
| Response body | `{"status": "ok"}` |

### ASGI entry point

| Attribute | Value |
|-----------|-------|
| Import path | `market_data_be.infrastructure.http.app:app` |
| Documented startup | `uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000` |
| Factory alternative | `uvicorn market_data_be.infrastructure.http.app:create_app --factory` |

### Application factory

```python
def create_app() -> FastAPI:
    ...
```

Public contract: returns a configured `FastAPI` instance with the health route registered. No parameters required for bootstrap.

## Data Model

No persistent entities. The health response is a minimal inline schema:

| Field | Type | Value |
|-------|------|-------|
| `status` | `str` | `"ok"` |

Use a small Pydantic `BaseModel` or a typed `dict` in the infrastructure layer only. Do not introduce shared DTO packages or domain models for this feature.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| `GET /health` | Always returns HTTP 200 while the process is running; no failure branches in bootstrap scope |
| Missing dependencies at startup | uvicorn/import fails at process start with standard Python import error (no custom handler required) |
| Unknown routes | FastAPI default 404 |

No custom exception handlers or middleware are required for this feature.

## Testing Strategy

| Test type | Location | Scope |
|-----------|----------|-------|
| HTTP integration | `src/infrastructure/tests/test_health.py` | `TestClient` against `create_app()` verifies `GET /health` returns 200 and `{"status": "ok"}` |
| Import guard (optional static check) | Same test module or separate | Assert `src/modules/analysis/` and `src/modules/classification/` source files contain no `fastapi` or `uvicorn` imports |

**Coverage expectations:**
- Health endpoint success path is required.
- Application factory instantiation is required.
- Domain purity (NFR-001) verified by absence of framework imports in domain paths.

Use `pytest` (existing dev dependency) and FastAPI's `TestClient` (from `fastapi.testclient`, backed by `starlette`).

## Requirement Traceability

| Requirement | Design decision |
|-------------|-----------------|
| REQ-001 | Add `fastapi` to `[project].dependencies` in `pyproject.toml` |
| REQ-002 | Add `uvicorn[standard]` to `[project].dependencies` in `pyproject.toml` |
| REQ-003 | Implement `create_app()` in `src/infrastructure/http/app.py` returning configured `FastAPI` instance |
| REQ-004 | Implement health router in `src/infrastructure/http/routes/health.py` with `GET /health` → 200 + `{"status": "ok"}` |
| REQ-005 | Expose module-level `app` and document uvicorn startup command targeting `market_data_be.infrastructure.http.app:app` |
| REQ-006 | Place all HTTP code under `src/infrastructure/http/`; leave `src/modules/` and `src/application/` free of FastAPI |
| NFR-001 | Enforced by layer placement; no imports from `fastapi` inside `src/modules/` |
| NFR-002 | Health handler returns static response without calling domain or application layers |
| NFR-003 | Use strict type hints on factory and route handler; target Python 3.12+ |
| NFR-004 | Configure setuptools `package-dir` / `find` so `market_data_be.infrastructure.*` resolves from `src/infrastructure/` |
