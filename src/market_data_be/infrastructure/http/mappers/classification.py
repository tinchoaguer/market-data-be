from enum import StrEnum
from typing import TypeVar

from market_data_be.infrastructure.http.dtos.classification import (
    EconomicReasonCode,
    EconomicSignalResponse,
    ExposureReasonCode,
    ExposureSignalResponse,
    MarketClassificationResponse,
    RegimeReasonCode,
    RegimeSignalResponse,
    RiskReasonCode,
    RiskSignalResponse,
)
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)
from market_data_be.modules.classification.models.signal import ClassificationSignal

ReasonCodeT = TypeVar("ReasonCodeT", bound=StrEnum)


class UndeclaredClassificationReasonError(ValueError):
    """Raised when a domain signal reason is not in the group's closed set."""

    def __init__(self, group: str, reason: str) -> None:
        self.group = group
        self.reason = reason
        super().__init__(
            f"undeclared classification reason for group {group!r}: {reason!r}"
        )


def _parse_reason(
    reason: str,
    reason_code_type: type[ReasonCodeT],
    group: str,
) -> ReasonCodeT:
    try:
        return reason_code_type(reason)
    except ValueError as exc:
        raise UndeclaredClassificationReasonError(group=group, reason=reason) from exc


def _map_regime_signals(
    signals: tuple[ClassificationSignal, ...],
) -> list[RegimeSignalResponse]:
    return [
        RegimeSignalResponse(
            source=signal.source,
            score=signal.score,
            reason=_parse_reason(signal.reason, RegimeReasonCode, "regime"),
        )
        for signal in signals
    ]


def _map_risk_signals(
    signals: tuple[ClassificationSignal, ...],
) -> list[RiskSignalResponse]:
    return [
        RiskSignalResponse(
            source=signal.source,
            score=signal.score,
            reason=_parse_reason(signal.reason, RiskReasonCode, "risk"),
        )
        for signal in signals
    ]


def _map_economic_signals(
    signals: tuple[ClassificationSignal, ...],
) -> list[EconomicSignalResponse]:
    return [
        EconomicSignalResponse(
            source=signal.source,
            score=signal.score,
            reason=_parse_reason(signal.reason, EconomicReasonCode, "economic"),
        )
        for signal in signals
    ]


def _map_exposure_signals(
    signals: tuple[ClassificationSignal, ...],
) -> list[ExposureSignalResponse]:
    return [
        ExposureSignalResponse(
            source=signal.source,
            score=signal.score,
            reason=_parse_reason(signal.reason, ExposureReasonCode, "exposure"),
        )
        for signal in signals
    ]


def map_market_classification_to_response(
    classification: ClassificationResult,
) -> MarketClassificationResponse:
    return MarketClassificationResponse(
        symbol=classification.symbol,
        regime=_map_regime_signals(classification.regime),
        risk=_map_risk_signals(classification.risk),
        economic=_map_economic_signals(classification.economic),
        exposure=_map_exposure_signals(classification.exposure),
    )
