import pytest

from market_data_be.infrastructure.http.dtos.classification import (
    EconomicReasonCode,
    ExposureReasonCode,
    RegimeReasonCode,
    RiskReasonCode,
)
from market_data_be.infrastructure.http.mappers.classification import (
    UndeclaredClassificationReasonError,
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
    assert response.regime[0].reason == RegimeReasonCode.TREND_UP
    assert response.risk[0].reason == RiskReasonCode.LOW_RISK
    assert response.economic[0].reason == EconomicReasonCode.NEUTRAL_EDGE
    assert response.exposure[0].reason == ExposureReasonCode.AMPLE_CAPACITY


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
