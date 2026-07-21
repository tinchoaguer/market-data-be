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
    AnalysisNarrativeMessageCode,
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
    MessageRef,
    RegimeAssessment,
    RiskAssessment,
    StrategyType,
)
from market_data_be.modules.analysis.narrative_codes import CATALOG_STRATEGY_ALLOWED

APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"
MODULES_ROOT = Path(__file__).resolve().parents[2] / "modules"
FORBIDDEN_PREFIXES = ("fastapi", "pydantic", "uvicorn")

TOP_LEVEL_KEYS = ("symbol", "regime", "risk", "economic", "exposure", "catalog")
ASSESSMENT_KEYS = ("regime", "risk", "economic", "exposure")

ALLOWED_REGIME_LABELS = {member.value for member in AnalysisRegimeLabel}
ALLOWED_REGIME_REASONS = {member.value for member in AnalysisRegimeReasonCode}
ALLOWED_NARRATIVE_CODES = {member.value for member in AnalysisNarrativeMessageCode}


def _resolve_schema(openapi: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        return openapi["components"]["schemas"][ref_name]
    return schema


def _sample_analysis_result(
    *,
    regime: MarketRegime = MarketRegime.TREND_UP,
    reasons: tuple[str, ...] = ("adx_strong",),
    catalog_reason: MessageRef | None = None,
    hard_gate_reason: MessageRef | None = None,
) -> AnalysisResult:
    if catalog_reason is None:
        catalog_reason = MessageRef.of(
            CATALOG_STRATEGY_ALLOWED,
            strategy=StrategyType.TREND_FOLLOWING.value,
            regime=regime.value,
        )
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
            catalog_reason=catalog_reason,
            hard_gate_reason=hard_gate_reason,
        ),
    )


def _assert_message_ref(value: object) -> None:
    assert isinstance(value, dict)
    assert "code" in value
    assert "params" in value
    assert value["code"] in ALLOWED_NARRATIVE_CODES
    assert isinstance(value["params"], dict)
    for param_value in value["params"].values():
        assert isinstance(param_value, (str, int, float, bool))
        if isinstance(param_value, str):
            assert " " not in param_value


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
    _assert_message_ref(catalog["catalog_reason"])
    hard_gate = catalog["hard_gate_reason"]
    if hard_gate is not None:
        _assert_message_ref(hard_gate)


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
    body = response.json()
    _assert_analysis_body(body, expected_symbol)
    assert MarketAnalysisResponse.model_validate(body)
    assert isinstance(body["catalog"]["catalog_reason"], dict)
    assert not isinstance(body["catalog"]["catalog_reason"], str)


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


def test_openapi_documents_message_ref_and_narrative_codes() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json").json()

    assert "MessageRefResponse" in openapi["components"]["schemas"]
    message_ref_schema = openapi["components"]["schemas"]["MessageRefResponse"]
    assert "code" in message_ref_schema["properties"]
    assert "params" in message_ref_schema["properties"]
    assert "severity" in message_ref_schema["properties"]
    assert "channel" in message_ref_schema["properties"]

    code_schema = _resolve_schema(openapi, message_ref_schema["properties"]["code"])
    assert set(code_schema["enum"]) == ALLOWED_NARRATIVE_CODES

    catalog_schema = openapi["components"]["schemas"]["CatalogResultResponse"]
    catalog_reason = catalog_schema["properties"]["catalog_reason"]
    hard_gate_reason = catalog_schema["properties"]["hard_gate_reason"]
    assert catalog_reason.get("$ref", "").endswith("/MessageRefResponse") or (
        "anyOf" in catalog_reason
        and any(
            ref.get("$ref", "").endswith("/MessageRefResponse")
            for ref in catalog_reason["anyOf"]
            if isinstance(ref, dict)
        )
    )
    # hard_gate_reason is MessageRef | null → anyOf with MessageRefResponse and null
    hard_gate_refs = hard_gate_reason.get("anyOf", [hard_gate_reason])
    assert any(
        isinstance(ref, dict) and ref.get("$ref", "").endswith("/MessageRefResponse")
        for ref in hard_gate_refs
    )


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


def test_undeclared_message_code_returns_http_500() -> None:
    undeclared = "catalog.not_a_declared_code"
    bad_result = _sample_analysis_result(
        catalog_reason=MessageRef.of(undeclared),
    )

    application = create_app()
    application.state.analyze_market = MagicMock()
    application.state.analyze_market.execute.return_value = bad_result

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/analysis")

    assert response.status_code == 500
    assert "detail" in response.json()
    assert undeclared not in response.text
    assert response.status_code != 200


def test_prose_message_params_returns_http_500() -> None:
    prose = "risk score too high for allocation"
    bad_result = _sample_analysis_result(
        catalog_reason=MessageRef.of(
            CATALOG_STRATEGY_ALLOWED,
            note=prose,
        ),
    )

    application = create_app()
    application.state.analyze_market = MagicMock()
    application.state.analyze_market.execute.return_value = bad_result

    client = TestClient(application, raise_server_exceptions=False)
    response = client.get("/markets/BTC-USDT/analysis")

    assert response.status_code == 500
    assert "detail" in response.json()
    assert prose not in response.text


def test_classification_openapi_untouched_by_analysis_message_refs() -> None:
    client = TestClient(create_app())
    openapi = client.get("/openapi.json").json()

    # Classification DTOs must not gain analysis MessageRef types as their contract.
    classification_schemas = {
        name
        for name in openapi["components"]["schemas"]
        if "Classification" in name or name.startswith("Signal")
    }
    for name in classification_schemas:
        schema = openapi["components"]["schemas"][name]
        blob = str(schema)
        assert "MessageRefResponse" not in blob or name == "MessageRefResponse"
        assert "AnalysisNarrativeMessageCode" not in blob
