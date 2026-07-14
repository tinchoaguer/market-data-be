from market_data_be.infrastructure.http.dtos.analysis import (
    AnalysisRegimeLabel,
    AnalysisRegimeReasonCode,
    CatalogResultResponse,
    EconomicAssessmentResponse,
    ExposureComponentsResponse,
    ExposureProfileResponse,
    MarketAnalysisResponse,
    RegimeAssessmentResponse,
    RiskAssessmentResponse,
)
from market_data_be.modules.analysis.models.analysis_result import AnalysisResult
from market_data_be.modules.analysis.models.assessments import (
    EconomicAssessment,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)
from market_data_be.modules.analysis.models.strategy_catalog import CatalogResult


class UndeclaredAnalysisRegimeError(ValueError):
    """Raised when a domain regime label is not in the HTTP closed set."""

    def __init__(self, regime: str) -> None:
        self.regime = regime
        super().__init__(f"undeclared analysis regime label: {regime!r}")


class UndeclaredAnalysisReasonError(ValueError):
    """Raised when a domain regime reason is not in the HTTP closed set."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"undeclared analysis regime reason: {reason!r}")


def _parse_regime_label(regime: str) -> AnalysisRegimeLabel:
    try:
        return AnalysisRegimeLabel(regime)
    except ValueError as exc:
        raise UndeclaredAnalysisRegimeError(regime=regime) from exc


def _parse_regime_reason(reason: str) -> AnalysisRegimeReasonCode:
    try:
        return AnalysisRegimeReasonCode(reason)
    except ValueError as exc:
        raise UndeclaredAnalysisReasonError(reason=reason) from exc


def _map_regime(assessment: RegimeAssessment) -> RegimeAssessmentResponse:
    return RegimeAssessmentResponse(
        regime=_parse_regime_label(assessment.regime.value),
        reasons=[_parse_regime_reason(reason) for reason in assessment.reasons],
        insufficient_data=assessment.insufficient_data,
    )


def _map_risk(assessment: RiskAssessment) -> RiskAssessmentResponse:
    return RiskAssessmentResponse(
        score=assessment.score,
        components=list(assessment.components),
        insufficient_data=assessment.insufficient_data,
    )


def _map_economic(assessment: EconomicAssessment) -> EconomicAssessmentResponse:
    return EconomicAssessmentResponse(
        edge=assessment.edge,
        components=list(assessment.components),
        insufficient_data=assessment.insufficient_data,
    )


def _map_exposure(profile: ExposureProfile) -> ExposureProfileResponse:
    return ExposureProfileResponse(
        symbol=profile.symbol,
        total_value=profile.total_value,
        exposure_pct=profile.exposure_pct,
        allocated_value=profile.allocated_value,
        portfolio_exposure_pct=profile.portfolio_exposure_pct,
        available_capacity_pct=profile.available_capacity_pct,
        symbol_weight_cap_pct=profile.symbol_weight_cap_pct,
        recommended_allocation_pct=profile.recommended_allocation_pct,
        recommended_allocation_value=profile.recommended_allocation_value,
        components=ExposureComponentsResponse(
            vol_budget_pct=profile.components.vol_budget_pct,
            liquidity_cap_value=profile.components.liquidity_cap_value,
        ),
        insufficient_data=profile.insufficient_data,
    )


def _map_catalog(catalog: CatalogResult) -> CatalogResultResponse:
    return CatalogResultResponse(
        allowed_strategies=[strategy.value for strategy in catalog.allowed_strategies],
        forbidden_strategies=[
            strategy.value for strategy in catalog.forbidden_strategies
        ],
        preferred_strategy=catalog.preferred_strategy.value,
        catalog_reason=catalog.catalog_reason,
        hard_gate_reason=catalog.hard_gate_reason,
    )


def map_analysis_result_to_response(
    analysis_result: AnalysisResult,
) -> MarketAnalysisResponse:
    return MarketAnalysisResponse(
        symbol=analysis_result.symbol,
        regime=_map_regime(analysis_result.regime),
        risk=_map_risk(analysis_result.risk),
        economic=_map_economic(analysis_result.economic),
        exposure=_map_exposure(analysis_result.exposure),
        catalog=_map_catalog(analysis_result.catalog),
    )
