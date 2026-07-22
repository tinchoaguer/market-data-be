import pytest

from market_data_be.infrastructure.http.dtos.classification import (
    EconomicReasonCode,
    EconomicSignalMessageRef,
    ExposureReasonCode,
    ExposureSignalMessageRef,
    RegimeReasonCode,
    RegimeSignalMessageRef,
    RiskReasonCode,
    RiskSignalMessageRef,
)
from market_data_be.infrastructure.http.mappers.classification import (
    InvalidClassificationMessageParamsError,
    UndeclaredClassificationReasonError,
    _build_params,
    map_market_classification_to_response,
)
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)
from market_data_be.modules.classification.models.signal import ClassificationSignal

REGIME_REASONS = {member.value for member in RegimeReasonCode}
RISK_REASONS = {member.value for member in RiskReasonCode}
ECONOMIC_REASONS = {member.value for member in EconomicReasonCode}
EXPOSURE_REASONS = {member.value for member in ExposureReasonCode}


def _valid_result() -> ClassificationResult:
    return ClassificationResult(
        symbol="BTC/USDT",
        regime=(ClassificationSignal(source="regime", score=0.4, reason="trend_up"),),
        risk=(ClassificationSignal(source="risk", score=0.0, reason="low_risk"),),
        economic=(
            ClassificationSignal(source="economic", score=0.0, reason="neutral_edge"),
        ),
        exposure=(
            ClassificationSignal(source="exposure", score=0.0, reason="ample_capacity"),
        ),
    )


def test_mapper_accepts_declared_reasons() -> None:
    response = map_market_classification_to_response(_valid_result())

    assert response.symbol == "BTC/USDT"
    assert response.regime[0].reason == RegimeSignalMessageRef(
        code=RegimeReasonCode.TREND_UP, params={}
    )
    assert response.risk[0].reason == RiskSignalMessageRef(
        code=RiskReasonCode.LOW_RISK, params={}
    )
    assert response.economic[0].reason == EconomicSignalMessageRef(
        code=EconomicReasonCode.NEUTRAL_EDGE, params={}
    )
    assert response.exposure[0].reason == ExposureSignalMessageRef(
        code=ExposureReasonCode.AMPLE_CAPACITY, params={}
    )


def test_mapper_reason_message_ref_has_declared_code_and_empty_params() -> None:
    response = map_market_classification_to_response(_valid_result())

    assert response.regime[0].reason.code == RegimeReasonCode.TREND_UP
    assert response.regime[0].reason.params == {}
    assert response.risk[0].reason.code == RiskReasonCode.LOW_RISK
    assert response.risk[0].reason.params == {}
    assert response.economic[0].reason.code == EconomicReasonCode.NEUTRAL_EDGE
    assert response.economic[0].reason.params == {}
    assert response.exposure[0].reason.code == ExposureReasonCode.AMPLE_CAPACITY
    assert response.exposure[0].reason.params == {}


@pytest.mark.parametrize(
    ("params", "expected_message_fragment"),
    [
        ({"note": "this is prose"}, "not a machine token"),
        ({"note": ""}, "not a machine token"),
        ({"payload": {"nested": 1}}, "non-scalar type"),
        ({"payload": [1, 2]}, "non-scalar type"),
    ],
)
def test_build_params_rejects_invalid_param_values(
    params: dict[str, object], expected_message_fragment: str
) -> None:
    with pytest.raises(InvalidClassificationMessageParamsError) as exc_info:
        _build_params("regime", params)

    assert exc_info.value.group == "regime"
    assert expected_message_fragment in exc_info.value.detail


def test_build_params_accepts_typed_scalars() -> None:
    params = _build_params(
        "regime", {"count": 3, "ratio": 0.5, "flag": True, "token": "machine_token"}
    )

    assert params == {"count": 3, "ratio": 0.5, "flag": True, "token": "machine_token"}


@pytest.mark.parametrize(
    ("group", "build"),
    [
        (
            "regime",
            lambda: ClassificationResult(
                symbol="BTC/USDT",
                regime=(
                    ClassificationSignal(
                        source="regime", score=0.0, reason="unknown_regime"
                    ),
                ),
                risk=(ClassificationSignal(source="risk", score=0.0, reason="low_risk"),),
                economic=(
                    ClassificationSignal(
                        source="economic", score=0.0, reason="neutral_edge"
                    ),
                ),
                exposure=(
                    ClassificationSignal(
                        source="exposure", score=0.0, reason="ample_capacity"
                    ),
                ),
            ),
        ),
        (
            "risk",
            lambda: ClassificationResult(
                symbol="BTC/USDT",
                regime=(
                    ClassificationSignal(source="regime", score=0.0, reason="trend_up"),
                ),
                risk=(
                    ClassificationSignal(
                        source="risk", score=0.0, reason="unknown_risk"
                    ),
                ),
                economic=(
                    ClassificationSignal(
                        source="economic", score=0.0, reason="neutral_edge"
                    ),
                ),
                exposure=(
                    ClassificationSignal(
                        source="exposure", score=0.0, reason="ample_capacity"
                    ),
                ),
            ),
        ),
        (
            "economic",
            lambda: ClassificationResult(
                symbol="BTC/USDT",
                regime=(
                    ClassificationSignal(source="regime", score=0.0, reason="trend_up"),
                ),
                risk=(ClassificationSignal(source="risk", score=0.0, reason="low_risk"),),
                economic=(
                    ClassificationSignal(
                        source="economic", score=0.0, reason="unknown_edge"
                    ),
                ),
                exposure=(
                    ClassificationSignal(
                        source="exposure", score=0.0, reason="ample_capacity"
                    ),
                ),
            ),
        ),
        (
            "exposure",
            lambda: ClassificationResult(
                symbol="BTC/USDT",
                regime=(
                    ClassificationSignal(source="regime", score=0.0, reason="trend_up"),
                ),
                risk=(ClassificationSignal(source="risk", score=0.0, reason="low_risk"),),
                economic=(
                    ClassificationSignal(
                        source="economic", score=0.0, reason="neutral_edge"
                    ),
                ),
                exposure=(
                    ClassificationSignal(
                        source="exposure", score=0.0, reason="unknown_capacity"
                    ),
                ),
            ),
        ),
    ],
)
def test_mapper_rejects_undeclared_reason(group: str, build: object) -> None:
    result_builder = build  # callable returning ClassificationResult
    with pytest.raises(UndeclaredClassificationReasonError) as exc_info:
        map_market_classification_to_response(result_builder())  # type: ignore[operator]

    assert exc_info.value.group == group
