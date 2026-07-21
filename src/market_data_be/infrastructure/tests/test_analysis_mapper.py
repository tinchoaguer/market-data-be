from enum import Enum

import pytest

from market_data_be.infrastructure.http.dtos.analysis import (
    AnalysisNarrativeMessageCode,
    AnalysisRegimeLabel,
    AnalysisRegimeReasonCode,
)
from market_data_be.infrastructure.http.mappers.analysis import (
    InvalidAnalysisMessageParamsError,
    UndeclaredAnalysisMessageCodeError,
    UndeclaredAnalysisReasonError,
    UndeclaredAnalysisRegimeError,
    map_analysis_result_to_response,
)
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


def _sample_analysis_result(
    *,
    regime: MarketRegime = MarketRegime.TREND_UP,
    reasons: tuple[str, ...] = ("adx_strong", "plus_di_dominant"),
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
        risk=RiskAssessment(score=0.45, components=(("vol", 0.2),)),
        economic=EconomicAssessment(edge=0.55, components=(("spread", 0.1),)),
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


def test_mapper_accepts_declared_regime_and_reasons() -> None:
    response = map_analysis_result_to_response(_sample_analysis_result())

    assert response.regime.regime == AnalysisRegimeLabel.TREND_UP
    assert response.regime.reasons == [
        AnalysisRegimeReasonCode.ADX_STRONG,
        AnalysisRegimeReasonCode.PLUS_DI_DOMINANT,
    ]


@pytest.mark.parametrize("regime", list(MarketRegime))
def test_mapper_accepts_all_market_regime_labels(regime: MarketRegime) -> None:
    response = map_analysis_result_to_response(
        _sample_analysis_result(regime=regime, reasons=("default",))
    )

    assert response.regime.regime.value == regime.value
    assert response.regime.regime in AnalysisRegimeLabel


def test_mapper_maps_message_refs() -> None:
    response = map_analysis_result_to_response(_sample_analysis_result())

    assert response.catalog.catalog_reason.code == AnalysisNarrativeMessageCode.CATALOG_STRATEGY_ALLOWED
    assert response.catalog.catalog_reason.params["strategy"] == "TREND_FOLLOWING"
    assert response.catalog.hard_gate_reason is None


def test_mapper_rejects_undeclared_regime() -> None:
    class BogusRegime(str, Enum):
        BOGUS = "NOT_A_DECLARED_REGIME"

    result = _sample_analysis_result()
    bad_result = AnalysisResult(
        symbol=result.symbol,
        regime=RegimeAssessment(
            regime=BogusRegime.BOGUS,  # type: ignore[arg-type]
            reasons=("default",),
        ),
        risk=result.risk,
        economic=result.economic,
        exposure=result.exposure,
        catalog=result.catalog,
    )

    with pytest.raises(UndeclaredAnalysisRegimeError) as exc_info:
        map_analysis_result_to_response(bad_result)

    assert exc_info.value.regime == "NOT_A_DECLARED_REGIME"


def test_mapper_rejects_undeclared_reason() -> None:
    with pytest.raises(UndeclaredAnalysisReasonError) as exc_info:
        map_analysis_result_to_response(
            _sample_analysis_result(reasons=("not_a_declared_reason",))
        )

    assert exc_info.value.reason == "not_a_declared_reason"


def test_mapper_rejects_undeclared_message_code() -> None:
    with pytest.raises(UndeclaredAnalysisMessageCodeError) as exc_info:
        map_analysis_result_to_response(
            _sample_analysis_result(
                catalog_reason=MessageRef.of("catalog.not_a_declared_code")
            )
        )

    assert exc_info.value.code == "catalog.not_a_declared_code"


def test_mapper_rejects_prose_message_params() -> None:
    with pytest.raises(InvalidAnalysisMessageParamsError):
        map_analysis_result_to_response(
            _sample_analysis_result(
                catalog_reason=MessageRef.of(
                    CATALOG_STRATEGY_ALLOWED,
                    note="risk score too high for allocation",
                )
            )
        )


def test_mapper_rejects_non_scalar_message_params() -> None:
    bad_ref = MessageRef(
        code=CATALOG_STRATEGY_ALLOWED,
        params=(("strategies", ("TREND_FOLLOWING", "PING_PONG")),),  # type: ignore[arg-type]
    )
    with pytest.raises(InvalidAnalysisMessageParamsError):
        map_analysis_result_to_response(
            _sample_analysis_result(catalog_reason=bad_ref)
        )


def test_mapper_maps_hard_gate_message_ref() -> None:
    hard_gate = MessageRef.of(
        "catalog.hard_gate.risk_too_high",
        risk_score=0.9,
    )
    catalog_reason = MessageRef.of(
        "catalog.wait",
        gate="risk_too_high",
        risk_score=0.9,
    )
    response = map_analysis_result_to_response(
        _sample_analysis_result(
            catalog_reason=catalog_reason,
            hard_gate_reason=hard_gate,
        )
    )

    assert response.catalog.hard_gate_reason is not None
    assert (
        response.catalog.hard_gate_reason.code
        == AnalysisNarrativeMessageCode.HARD_GATE_RISK_TOO_HIGH
    )
    assert response.catalog.hard_gate_reason.params["risk_score"] == 0.9
