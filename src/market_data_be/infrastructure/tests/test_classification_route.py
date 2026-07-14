import ast
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.infrastructure.http.app import create_app
from market_data_be.infrastructure.http.dtos.classification import (
    EconomicReasonCode,
    ExposureReasonCode,
    RegimeReasonCode,
    RiskReasonCode,
)
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)
from market_data_be.modules.classification.models.signal import ClassificationSignal

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"
MODULES_ROOT = Path(__file__).resolve().parents[2] / "modules"
FORBIDDEN_PREFIXES = ("fastapi", "pydantic", "uvicorn")

DOMAIN_KEYS = ("regime", "risk", "economic", "exposure")
EXPECTED_SOURCES = {"regime", "risk", "economic", "exposure"}

GROUP_REASON_CODES: dict[str, set[str]] = {
    "regime": {member.value for member in RegimeReasonCode},
    "risk": {member.value for member in RiskReasonCode},
    "economic": {member.value for member in EconomicReasonCode},
    "exposure": {member.value for member in ExposureReasonCode},
}


def _resolve_schema(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        return openapi["components"]["schemas"][ref_name]
    return schema


def _reason_enum_from_signal_schema(
    openapi: dict[str, Any],
    signal_schema_name: str,
) -> set[str]:
    signal_schema = openapi["components"]["schemas"][signal_schema_name]
    reason_schema = _resolve_schema(openapi, signal_schema["properties"]["reason"])
    enum_values = reason_schema.get("enum")
    assert enum_values is not None, f"missing enum on {signal_schema_name}.reason"
    return set(enum_values)


def _assert_classification_body(body: dict[str, object], expected_symbol: str) -> None:
    assert body["symbol"] == expected_symbol
    for domain in DOMAIN_KEYS:
        signals = body[domain]
        assert isinstance(signals, list)
        assert len(signals) > 0
        allowed = GROUP_REASON_CODES[domain]
        for signal in signals:
            assert isinstance(signal, dict)
            assert isinstance(signal["source"], str)
            assert isinstance(signal["score"], (int, float))
            assert isinstance(signal["reason"], str)
            assert signal["source"] in EXPECTED_SOURCES
            assert signal["reason"] in allowed


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


def test_openapi_documents_group_reason_enums() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json").json()

    path_item = openapi["paths"]["/markets/{symbol}/classification"]["get"]
    response_schema = _resolve_schema(
        openapi,
        path_item["responses"]["200"]["content"]["application/json"]["schema"],
    )

    expected_signal_schemas = {
        "regime": ("RegimeSignalResponse", GROUP_REASON_CODES["regime"]),
        "risk": ("RiskSignalResponse", GROUP_REASON_CODES["risk"]),
        "economic": ("EconomicSignalResponse", GROUP_REASON_CODES["economic"]),
        "exposure": ("ExposureSignalResponse", GROUP_REASON_CODES["exposure"]),
    }

    for group, (signal_schema_name, expected_codes) in expected_signal_schemas.items():
        items_ref = response_schema["properties"][group]["items"]["$ref"]
        assert items_ref.endswith(f"/{signal_schema_name}")
        assert (
            _reason_enum_from_signal_schema(openapi, signal_schema_name) == expected_codes
        )

def test_undeclared_reason_returns_http_500() -> None:
    undeclared = "not_a_declared_reason"
    bad_result = ClassificationResult(
        symbol="BTC/USDT",
        regime=(
            ClassificationSignal(source="regime", score=0.0, reason=undeclared),
        ),
        risk=(ClassificationSignal(source="risk", score=0.0, reason="low_risk"),),
        economic=(
            ClassificationSignal(source="economic", score=0.0, reason="neutral_edge"),
        ),
        exposure=(
            ClassificationSignal(source="exposure", score=0.0, reason="ample_capacity"),
        ),
    )

    application = create_app()
    application.state.classify_market = MagicMock()
    application.state.classify_market.execute.return_value = bad_result

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/classification")

    assert response.status_code == 500
    body = response.json()
    assert "detail" in body
    assert undeclared not in response.text
