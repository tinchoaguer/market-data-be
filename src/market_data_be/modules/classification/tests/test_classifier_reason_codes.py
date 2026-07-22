import re

import pytest

from market_data_be.modules.classification.classifiers.economic import EconomicClassifier
from market_data_be.modules.classification.classifiers.exposure import ExposureClassifier
from market_data_be.modules.classification.classifiers.regime import RegimeClassifier
from market_data_be.modules.classification.classifiers.risk import RiskClassifier
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
from market_data_be.modules.classification.reason_codes import (
    ECONOMIC_REASON_CODES,
    EXPOSURE_REASON_CODES,
    REGIME_REASON_CODES,
    RISK_REASON_CODES,
)

# Machine-token strings: no whitespace, no sentence punctuation used for display English.
_PROSE_STRING_PATTERN = re.compile(r"[\s.,;:!?\"'`]")


@pytest.mark.parametrize("regime", list(RegimeLabel))
def test_regime_classifier_emits_declared_reason(regime: RegimeLabel) -> None:
    signals = RegimeClassifier().classify(RegimeClassifierInput(regime=regime))

    assert len(signals) == 1
    assert signals[0].reason in REGIME_REASON_CODES
    assert not _PROSE_STRING_PATTERN.search(signals[0].reason)


@pytest.mark.parametrize(
    "score",
    [0.0, 0.29, 0.30, 0.59, 0.60, 0.79, 0.80, 1.0],
)
def test_risk_classifier_emits_declared_reason(score: float) -> None:
    signals = RiskClassifier().classify(RiskClassifierInput(score=score))

    assert len(signals) == 1
    assert signals[0].reason in RISK_REASON_CODES
    assert not _PROSE_STRING_PATTERN.search(signals[0].reason)


@pytest.mark.parametrize(
    "edge",
    [-0.5, -0.01, 0.0, 0.39, 0.40, 0.69, 0.70, 1.0],
)
def test_economic_classifier_emits_declared_reason(edge: float) -> None:
    signals = EconomicClassifier().classify(EconomicClassifierInput(edge=edge))

    assert len(signals) == 1
    assert signals[0].reason in ECONOMIC_REASON_CODES
    assert not _PROSE_STRING_PATTERN.search(signals[0].reason)


@pytest.mark.parametrize(
    "capacity",
    [0.0, 19.9, 20.0, 49.9, 50.0, 100.0],
)
def test_exposure_classifier_emits_declared_reason(capacity: float) -> None:
    signals = ExposureClassifier().classify(
        ExposureClassifierInput(available_capacity_pct=capacity)
    )

    assert len(signals) == 1
    assert signals[0].reason in EXPOSURE_REASON_CODES
    assert not _PROSE_STRING_PATTERN.search(signals[0].reason)
