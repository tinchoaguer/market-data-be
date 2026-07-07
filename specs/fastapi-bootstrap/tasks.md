# Tasks

## Implementation Tasks

Tasks are ordered to minimize dependencies. Each task maps to one or more requirements.

- [x] Update `pyproject.toml`: add `fastapi` and `uvicorn[standard]` to runtime dependencies; replace placeholder package config with setuptools discovery mapping `src/` modules to the `market_data_be` namespace (REQ-001, REQ-002, NFR-004)

- [x] Create infrastructure package skeleton: `src/infrastructure/http/__init__.py`, `src/infrastructure/http/routes/__init__.py` (REQ-006)

- [x] Implement health router at `src/infrastructure/http/routes/health.py` with `GET /health` returning HTTP 200 and JSON `{"status": "ok"}` (REQ-004, NFR-002, NFR-003)

- [x] Implement `create_app()` factory and module-level `app` in `src/infrastructure/http/app.py`; register the health router (REQ-003, REQ-005)

- [x] Document the uvicorn startup command in a project-visible location (e.g., `README` section or inline comment in `app.py` docstring): `uvicorn market_data_be.infrastructure.http.app:app --host 0.0.0.0 --port 8000` (REQ-005)

- [x] Add infrastructure tests at `src/infrastructure/tests/test_health.py` using FastAPI `TestClient` to assert `GET /health` returns status 200 and body `{"status": "ok"}` (REQ-004, REQ-003)

- [x] Verify domain purity: confirm no `fastapi` or `uvicorn` imports exist under `src/modules/analysis/` or `src/modules/classification/` (REQ-006, NFR-001)

- [x] Manual smoke test: install dependencies, run the documented uvicorn command, and confirm the process starts and `GET /health` responds with HTTP 200 (REQ-005, AC-003, AC-004)
