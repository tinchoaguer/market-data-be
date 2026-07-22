import re
from enum import StrEnum
from typing import TypeVar

from market_data_be.infrastructure.http.dtos.classification import (
    EconomicReasonCode,
    EconomicSignalMessageRef,
    EconomicSignalResponse,
    ExposureReasonCode,
    ExposureSignalMessageRef,
    ExposureSignalResponse,
    MarketClassificationResponse,
    MessageParamValue,
    RegimeReasonCode,
    RegimeSignalMessageRef,
    RegimeSignalResponse,
    RiskReasonCode,
    RiskSignalMessageRef,
    RiskSignalResponse,
)
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)
from market_data_be.modules.classification.models.signal import ClassificationSignal

ReasonCodeT = TypeVar("ReasonCodeT", bound=StrEnum)

# Machine-token strings: no whitespace, no sentence punctuation used for display English.
_PROSE_STRING_PATTERN = re.compile(r"[\s.,;:!?\"'`]")


class UndeclaredClassificationReasonError(ValueError):
    """Raised when a domain signal reason is not in the group's closed set."""

    def __init__(self, group: str, reason: str) -> None:
        self.group = group
        self.reason = reason
        super().__init__(
            f"undeclared classification reason for group {group!r}: {reason!r}"
        )


class InvalidClassificationMessageParamsError(ValueError):
    """Raised when a classification MessageRef param violates typed-scalar / no-prose rules."""

    def __init__(self, group: str, detail: str) -> None:
        self.group = group
        self.detail = detail
        super().__init__(f"invalid classification message params for group {group!r}: {detail}")


def _parse_reason(
    reason: str,
    reason_code_type: type[ReasonCodeT],
    group: str,
) -> ReasonCodeT:
    try:
        return reason_code_type(reason)
    except ValueError as exc:
        raise UndeclaredClassificationReasonError(group=group, reason=reason) from exc


def _validate_param_value(group: str, key: str, value: object) -> MessageParamValue:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        if not value or _PROSE_STRING_PATTERN.search(value):
            raise InvalidClassificationMessageParamsError(
                group, f"param {key!r} is not a machine token"
            )
        return value
    raise InvalidClassificationMessageParamsError(
        group, f"param {key!r} has non-scalar type {type(value).__name__}"
    )


def _build_params(group: str, raw_params: dict[str, object]) -> dict[str, MessageParamValue]:
    params: dict[str, MessageParamValue] = {}
    for key, value in raw_params.items():
        if not isinstance(key, str) or not key:
            raise InvalidClassificationMessageParamsError(
                group, "param keys must be non-empty strings"
            )
        params[key] = _validate_param_value(group, key, value)
    return params


def _map_regime_signals(
    signals: tuple[ClassificationSignal, ...],
) -> list[RegimeSignalResponse]:
    return [
        RegimeSignalResponse(
            source=signal.source,
            score=signal.score,
            reason=RegimeSignalMessageRef(
                code=_parse_reason(signal.reason, RegimeReasonCode, "regime"),
                params=_build_params("regime", {}),
            ),
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
            reason=RiskSignalMessageRef(
                code=_parse_reason(signal.reason, RiskReasonCode, "risk"),
                params=_build_params("risk", {}),
            ),
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
            reason=EconomicSignalMessageRef(
                code=_parse_reason(signal.reason, EconomicReasonCode, "economic"),
                params=_build_params("economic", {}),
            ),
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
            reason=ExposureSignalMessageRef(
                code=_parse_reason(signal.reason, ExposureReasonCode, "exposure"),
                params=_build_params("exposure", {}),
            ),
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
