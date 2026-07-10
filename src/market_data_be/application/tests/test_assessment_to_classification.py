import pytest

from market_data_be.application.mappers.assessment_to_classification import (
    to_economic_classifier_input,
    to_exposure_classifier_input,
    to_regime_classifier_input,
    to_risk_classifier_input,
)
from market_data_be.modules.analysis.models.assessments import (
    EconomicAssessment,
    ExposureComponents,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)
from market_data_be.modules.analysis.models.enums import MarketRegime
from market_data_be.modules.classification.models.inputs.economic import (
    EconomicClassifierInput,
)
from market_data_be.modules.classification.models.inputs.exposure import (
    ExposureClassifierInput,
)
from market_data_be.modules.classification.models.inputs.regime import (
    RegimeClassifierInput,
    RegimeLabel,
)
from market_data_be.modules.classification.models.inputs.risk import RiskClassifierInput


@pytest.mark.parametrize(
    ("market_regime", "expected_label"),
    [
        (MarketRegime.TREND_UP, RegimeLabel.TREND_UP),
        (MarketRegime.TREND_DOWN, RegimeLabel.TREND_DOWN),
        (MarketRegime.RANGE, RegimeLabel.RANGE),
        (MarketRegime.CHAOTIC, RegimeLabel.CHAOTIC),
        (MarketRegime.NEWS_SPIKE, RegimeLabel.NEWS_SPIKE),
    ],
)
def test_to_regime_classifier_input_translates_enum(
    market_regime: MarketRegime,
    expected_label: RegimeLabel,
) -> None:
    assessment = RegimeAssessment(regime=market_regime, reasons=("test",))

    result = to_regime_classifier_input(assessment)

    assert isinstance(result, RegimeClassifierInput)
    assert result.regime is expected_label
    assert result.regime.value == market_regime.value


def test_to_risk_classifier_input_maps_score() -> None:
    assessment = RiskAssessment(score=0.55, components=(("volatility", 0.3),))

    result = to_risk_classifier_input(assessment)

    assert isinstance(result, RiskClassifierInput)
    assert result.score == 0.55


def test_to_economic_classifier_input_maps_edge() -> None:
    assessment = EconomicAssessment(edge=0.72, components=(("momentum", 0.4),))

    result = to_economic_classifier_input(assessment)

    assert isinstance(result, EconomicClassifierInput)
    assert result.edge == 0.72


def test_to_exposure_classifier_input_maps_available_capacity() -> None:
    profile = ExposureProfile(
        symbol="BTC/USDT",
        total_value=10_000.0,
        exposure_pct=0.1,
        allocated_value=1_000.0,
        portfolio_exposure_pct=0.25,
        available_capacity_pct=75.0,
        symbol_weight_cap_pct=0.35,
        recommended_allocation_pct=0.15,
        recommended_allocation_value=1_500.0,
        components=ExposureComponents(
            vol_budget_pct=0.12,
            liquidity_cap_value=5_000.0,
        ),
    )

    result = to_exposure_classifier_input(profile)

    assert isinstance(result, ExposureClassifierInput)
    assert result.available_capacity_pct == 75.0
