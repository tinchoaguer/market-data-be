import ast
from pathlib import Path

from fastapi.testclient import TestClient

from market_data_be.infrastructure.http.app import create_app

MODULES_ROOT = Path(__file__).resolve().parents[2] / "modules"
FORBIDDEN_PREFIXES = ("fastapi", "uvicorn")


def test_create_app_returns_fastapi_instance() -> None:
    application = create_app()
    assert application.title == "Market Data backend"
    assert application.version == "5.5.0"


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_domain_modules_have_no_framework_imports() -> None:
    for path in MODULES_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(FORBIDDEN_PREFIXES), (
                        f"{path} imports forbidden module {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                assert not node.module.startswith(FORBIDDEN_PREFIXES), (
                    f"{path} imports forbidden module {node.module}"
                )
