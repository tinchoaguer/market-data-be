import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.infrastructure.http.app import create_app
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"
MODULES_ROOT = Path(__file__).resolve().parents[2] / "modules"
FORBIDDEN_PREFIXES = ("fastapi", "pydantic", "uvicorn")

DOMAIN_KEYS = ("regime", "risk", "economic", "exposure")
EXPECTED_SOURCES = {"regime", "risk", "economic", "exposure"}


def _assert_classification_body(body: dict[str, object], expected_symbol: str) -> None:
    assert body["symbol"] == expected_symbol
    for domain in DOMAIN_KEYS:
        signals = body[domain]
        assert isinstance(signals, list)
        assert len(signals) > 0
        for signal in signals:
            assert isinstance(signal["source"], str)
            assert isinstance(signal["score"], (int, float))
            assert isinstance(signal["reason"], str)
            assert signal["source"] in EXPECTED_SOURCES


@pytest.mark.parametrize(
    ("url_symbol", "expected_symbol"),
    [
        ("BTC-USDT", "BTC/USDT"),
        ("ETH-USDT", "ETH/USDT"),
    ],
)
def test_classification_success(url_symbol: str, expected_symbol: str) -> None:
    client = TestClient(create_app())
    response = client.get(f"/markets/{url_symbol}/classification")

    assert response.status_code == 200
    _assert_classification_body(response.json(), expected_symbol)


def test_parse_url_symbol_converts_hyphen_to_slash() -> None:
    assert parse_url_symbol("BTC-USDT") == "BTC/USDT"
    assert parse_url_symbol("btc-usdt") == "BTC/USDT"


def test_classification_url_param_converted_to_internal_symbol() -> None:
    captured: list[str] = []

    original_execute = ClassifyMarket.execute

    def spy_execute(self: ClassifyMarket, symbol: str, **kwargs: object) -> object:
        captured.append(symbol)
        return original_execute(self, symbol, **kwargs)

    with patch.object(ClassifyMarket, "execute", spy_execute):
        client = TestClient(create_app())
        response = client.get("/markets/BTC-USDT/classification")

    assert response.status_code == 200
    assert captured == ["BTC/USDT"]
    assert response.json()["symbol"] == "BTC/USDT"


def test_classification_not_found_returns_404() -> None:
    client = TestClient(create_app())
    response = client.get("/markets/SOL-USDT/classification")

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.parametrize("url_symbol", ["BTC", "BTC%2FUSDT"])
def test_classification_invalid_symbol_format_returns_422(url_symbol: str) -> None:
    client = TestClient(create_app())
    response = client.get(f"/markets/{url_symbol}/classification")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_classification_unexpected_error_returns_500() -> None:
    application = create_app()
    application.state.classify_market = MagicMock()
    application.state.classify_market.execute.side_effect = RuntimeError("boom")

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/classification")

    assert response.status_code == 500
    assert "detail" in response.json()


def test_domain_modules_have_no_framework_imports() -> None:
    for root in (MODULES_ROOT, APPLICATION_ROOT):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert not any(
                            alias.name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES
                        ), f"{path} imports forbidden module {alias.name}"
                elif isinstance(node, ast.ImportFrom) and node.module is not None:
                    assert not any(
                        node.module.startswith(prefix) for prefix in FORBIDDEN_PREFIXES
                    ), f"{path} imports forbidden module {node.module}"
