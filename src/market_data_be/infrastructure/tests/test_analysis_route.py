import ast
from enum import Enum
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from market_data_be.application.use_cases.analyze_market import AnalyzeMarket
from market_data_be.infrastructure.http.app import create_app
from market_data_be.infrastructure.http.dtos.analysis import (
    AnalysisRegimeLabel,
    AnalysisRegimeReasonCode,
    MarketAnalysisResponse,
)
from market_data_be.infrastructure.http.validation.symbol import parse_url_symbol
from market_data_be.modules.analysis.models import (
    AnalysisResult,
    CatalogResult,
    EconomicAssessment,
    ExposureComponents,
    ExposureProfile,
    MarketRegime,
    RegimeAssessment,
    RiskAssessment,
    StrategyType,
)

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"
MODULES_ROOT = Path(__file__).resolve().parents[2] / "modules"
FORBIDDEN_PREFIXES = ("fastapi", "pydantic", "uvicorn")

TOP_LEVEL_KEYS = ("symbol", "regime", "risk", "economic", "exposure", "catalog")
ASSESSMENT_KEYS = ("regime", "risk", "economic", "exposure")

ALLOWED_REGIME_LABELS = {member.value for member in AnalysisRegimeLabel}
ALLOWED_REGIME_REASONS = {member.value for member in AnalysisRegimeReasonCode}


def _resolve_schema(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        return openapi["components"]["schemas"][ref_name]
    return schema


def _sample_analysis_result(
    *,
    regime: MarketRegime = MarketRegime.TREND_UP,
    reasons: tuple[str, ...] = ("adx_strong",),
) -> AnalysisResult:
    return AnalysisResult(
        symbol="BTC/USDT",
        regime=RegimeAssessment(regime=regime, reasons=reasons),
        risk=RiskAssessment(score=0.45, components=()),
        economic=EconomicAssessment(edge=0.55, components=()),
        exposure=ExposureProfile(
            symbol="BTC/USDT",
            total_value=10_000.0,
            exposure_pct=0.1,
            allocated_value=1_000.0,
            portfolio_exposure_pct=0.2,
            available_capacity_pct=80.0,
            symbol_weight_cap_pct=0.35,
            recommended_allocation_pct=0.15,
            recommended_allocation_value=1_500.0,
            components=ExposureComponents(
                vol_budget_pct=0.12,
                liquidity_cap_value=5_000.0,
            ),
        ),
        catalog=CatalogResult(
            allowed_strategies=(StrategyType.TREND_FOLLOWING,),
            forbidden_strategies=(),
            preferred_strategy=StrategyType.TREND_FOLLOWING,
            catalog_reason="test",
        ),
    )


def _assert_analysis_body(body: dict[str, object], expected_symbol: str) -> None:
    assert body["symbol"] == expected_symbol
    for key in TOP_LEVEL_KEYS:
        assert key in body

    for domain in ASSESSMENT_KEYS:
        assessment = body[domain]
        assert isinstance(assessment, dict)

    regime = body["regime"]
    assert isinstance(regime, dict)
    assert isinstance(regime["regime"], str)
    assert regime["regime"] in ALLOWED_REGIME_LABELS
    assert isinstance(regime["reasons"], list)
    for reason in regime["reasons"]:
        assert reason in ALLOWED_REGIME_REASONS
    assert isinstance(regime["insufficient_data"], bool)

    risk = body["risk"]
    assert isinstance(risk, dict)
    assert isinstance(risk["score"], (int, float))
    assert isinstance(risk["components"], list)
    assert isinstance(risk["insufficient_data"], bool)

    economic = body["economic"]
    assert isinstance(economic, dict)
    assert isinstance(economic["edge"], (int, float))
    assert isinstance(economic["components"], list)
    assert isinstance(economic["insufficient_data"], bool)

    exposure = body["exposure"]
    assert isinstance(exposure, dict)
    assert isinstance(exposure["available_capacity_pct"], (int, float))
    assert isinstance(exposure["components"], dict)

    catalog = body["catalog"]
    assert isinstance(catalog, dict)
    assert isinstance(catalog["allowed_strategies"], list)
    assert isinstance(catalog["forbidden_strategies"], list)
    assert isinstance(catalog["preferred_strategy"], str)
    assert isinstance(catalog["catalog_reason"], str)


@pytest.mark.parametrize(
    ("url_symbol", "expected_symbol"),
    [
        ("BTC-USDT", "BTC/USDT"),
        ("ETH-USDT", "ETH/USDT"),
    ],
)
def test_analysis_success(url_symbol: str, expected_symbol: str) -> None:
    client = TestClient(create_app())
    response = client.get(f"/markets/{url_symbol}/analysis")

    assert response.status_code == 200
    _assert_analysis_body(response.json(), expected_symbol)
    assert MarketAnalysisResponse.model_validate(response.json())


def test_parse_url_symbol_converts_hyphen_to_slash() -> None:
    assert parse_url_symbol("BTC-USDT") == "BTC/USDT"
    assert parse_url_symbol("btc-usdt") == "BTC/USDT"


def test_analysis_url_param_converted_to_internal_symbol() -> None:
    captured: list[str] = []

    original_execute = AnalyzeMarket.execute

    def spy_execute(self: AnalyzeMarket, symbol: str) -> object:
        captured.append(symbol)
        return original_execute(self, symbol)

    with patch.object(AnalyzeMarket, "execute", spy_execute):
        client = TestClient(create_app())
        response = client.get("/markets/BTC-USDT/analysis")

    assert response.status_code == 200
    assert captured == ["BTC/USDT"]
    assert response.json()["symbol"] == "BTC/USDT"


def test_analysis_not_found_returns_404() -> None:
    client = TestClient(create_app())
    response = client.get("/markets/SOL-USDT/analysis")

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.parametrize("url_symbol", ["BTC", "BTC%2FUSDT"])
def test_analysis_invalid_symbol_format_returns_422(url_symbol: str) -> None:
    client = TestClient(create_app())
    response = client.get(f"/markets/{url_symbol}/analysis")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_analysis_slash_separated_path_returns_422() -> None:
    client = TestClient(create_app())
    response = client.get("/markets/BTC/USDT/analysis")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_analysis_unexpected_error_returns_500() -> None:
    application = create_app()
    application.state.analyze_market = MagicMock()
    application.state.analyze_market.execute.side_effect = RuntimeError("boom")

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/analysis")

    assert response.status_code == 500
    assert "detail" in response.json()


def test_domain_and_application_have_no_framework_imports() -> None:
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


def test_openapi_documents_regime_and_reason_enums() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json").json()

    path_item = openapi["paths"]["/markets/{symbol}/analysis"]["get"]
    response_schema = _resolve_schema(
        openapi,
        path_item["responses"]["200"]["content"]["application/json"]["schema"],
    )

    regime_ref = response_schema["properties"]["regime"]["$ref"]
    assert regime_ref.endswith("/RegimeAssessmentResponse")
    regime_schema = openapi["components"]["schemas"]["RegimeAssessmentResponse"]

    regime_label_schema = _resolve_schema(openapi, regime_schema["properties"]["regime"])
    assert set(regime_label_schema["enum"]) == ALLOWED_REGIME_LABELS

    reasons_items = _resolve_schema(openapi, regime_schema["properties"]["reasons"]["items"])
    assert set(reasons_items["enum"]) == ALLOWED_REGIME_REASONS


def test_undeclared_regime_returns_http_500() -> None:
    class BogusRegime(str, Enum):
        BOGUS = "NOT_A_DECLARED_REGIME"

    undeclared = "NOT_A_DECLARED_REGIME"
    bad_result = _sample_analysis_result()
    bad_result = AnalysisResult(
        symbol=bad_result.symbol,
        regime=RegimeAssessment(
            regime=BogusRegime.BOGUS,  # type: ignore[arg-type]
            reasons=("default",),
        ),
        risk=bad_result.risk,
        economic=bad_result.economic,
        exposure=bad_result.exposure,
        catalog=bad_result.catalog,
    )

    application = create_app()
    application.state.analyze_market = MagicMock()
    application.state.analyze_market.execute.return_value = bad_result

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/analysis")

    assert response.status_code == 500
    assert "detail" in response.json()
    assert undeclared not in response.text


def test_undeclared_reason_returns_http_500() -> None:
    undeclared = "not_a_declared_reason"
    bad_result = _sample_analysis_result(reasons=(undeclared,))

    application = create_app()
    application.state.analyze_market = MagicMock()
    application.state.analyze_market.execute.return_value = bad_result

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/analysis")

    assert response.status_code == 500
    assert "detail" in response.json()
    assert undeclared not in response.text
