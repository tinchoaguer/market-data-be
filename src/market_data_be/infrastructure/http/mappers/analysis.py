import re
from typing import Literal, cast

from market_data_be.infrastructure.http.dtos.analysis import (
    AnalysisNarrativeMessageCode,
    AnalysisRegimeLabel,
    AnalysisRegimeReasonCode,
    CatalogResultResponse,
    EconomicAssessmentResponse,
    ExposureComponentsResponse,
    ExposureProfileResponse,
    MarketAnalysisResponse,
    MessageParamValue,
    MessageRefResponse,
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
from market_data_be.modules.analysis.models.message_ref import MessageRef
from market_data_be.modules.analysis.models.strategy_catalog import CatalogResult

# Machine-token strings: no whitespace, no sentence punctuation used for display English.
_PROSE_STRING_PATTERN = re.compile(r"[\s.,;:!?\"'`]")


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


class UndeclaredAnalysisMessageCodeError(ValueError):
    """Raised when a domain MessageRef code is not in the HTTP closed set."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"undeclared analysis message code: {code!r}")


class InvalidAnalysisMessageParamsError(ValueError):
    """Raised when MessageRef params violate typed-scalar / no-prose rules."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"invalid analysis message params: {detail}")


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


def _parse_message_code(code: str) -> AnalysisNarrativeMessageCode:
    try:
        return AnalysisNarrativeMessageCode(code)
    except ValueError as exc:
        raise UndeclaredAnalysisMessageCodeError(code=code) from exc


def _validate_param_value(key: str, value: object) -> MessageParamValue:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        if not value or _PROSE_STRING_PATTERN.search(value):
            raise InvalidAnalysisMessageParamsError(
                f"param {key!r} is not a machine token"
            )
        return value
    raise InvalidAnalysisMessageParamsError(
        f"param {key!r} has non-scalar type {type(value).__name__}"
    )


def _map_message_ref(ref: MessageRef) -> MessageRefResponse:
    code = _parse_message_code(ref.code)
    params: dict[str, MessageParamValue] = {}
    for key, value in ref.params:
        if not isinstance(key, str) or not key:
            raise InvalidAnalysisMessageParamsError("param keys must be non-empty strings")
        params[key] = _validate_param_value(key, value)

    severity: Literal["info", "warning", "error"] | None = None
    if ref.severity is not None:
        if ref.severity not in {"info", "warning", "error"}:
            raise InvalidAnalysisMessageParamsError(
                f"severity {ref.severity!r} is not allowed"
            )
        severity = cast(Literal["info", "warning", "error"], ref.severity)

    channel: Literal["ui", "email", "push", "sms", "log"] | None = None
    if ref.channel is not None:
        if ref.channel not in {"ui", "email", "push", "sms", "log"}:
            raise InvalidAnalysisMessageParamsError(
                f"channel {ref.channel!r} is not allowed"
            )
        channel = cast(Literal["ui", "email", "push", "sms", "log"], ref.channel)

    return MessageRefResponse(
        code=code,
        params=params,
        severity=severity,
        channel=channel,
    )


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
    hard_gate: MessageRefResponse | None = None
    if catalog.hard_gate_reason is not None:
        hard_gate = _map_message_ref(catalog.hard_gate_reason)
    return CatalogResultResponse(
        allowed_strategies=[strategy.value for strategy in catalog.allowed_strategies],
        forbidden_strategies=[
            strategy.value for strategy in catalog.forbidden_strategies
        ],
        preferred_strategy=catalog.preferred_strategy.value,
        catalog_reason=_map_message_ref(catalog.catalog_reason),
        hard_gate_reason=hard_gate,
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
