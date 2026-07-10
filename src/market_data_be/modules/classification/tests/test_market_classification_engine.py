from market_data_be.modules.classification.market_classification_engine import (
    MarketClassificationEngine,
)
from market_data_be.modules.classification.models.classification_inputs import (
    ClassificationInputs,
)
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
from market_data_be.modules.classification.models.signal import ClassificationSignal


class RecordingClassifier:
    def __init__(self, source: str) -> None:
        self.source = source
        self.last_input: object | None = None

    def classify(self, assessment: object) -> tuple[ClassificationSignal, ...]:
        self.last_input = assessment
        return (ClassificationSignal(source=self.source, score=0.0, reason="stub"),)


def _sample_inputs() -> ClassificationInputs:
    return ClassificationInputs(
        symbol="BTC/USDT",
        regime=RegimeClassifierInput(regime=RegimeLabel.TREND_UP),
        risk=RiskClassifierInput(score=0.45),
        economic=EconomicClassifierInput(edge=0.55),
        exposure=ExposureClassifierInput(available_capacity_pct=80.0),
    )


def test_engine_returns_complete_classification_result() -> None:
    engine = MarketClassificationEngine()
    result = engine.classify(_sample_inputs())

    assert result.symbol == "BTC/USDT"
    assert len(result.regime) >= 1
    assert len(result.risk) >= 1
    assert len(result.economic) >= 1
    assert len(result.exposure) >= 1
    assert result.regime[0].source == "regime"
    assert result.risk[0].source == "risk"
    assert result.economic[0].source == "economic"
    assert result.exposure[0].source == "exposure"


def test_engine_passes_classifier_inputs_to_workers() -> None:
    regime_classifier = RecordingClassifier("regime")
    risk_classifier = RecordingClassifier("risk")
    economic_classifier = RecordingClassifier("economic")
    exposure_classifier = RecordingClassifier("exposure")
    inputs = _sample_inputs()
    engine = MarketClassificationEngine(
        regime_classifier=regime_classifier,
        risk_classifier=risk_classifier,
        economic_classifier=economic_classifier,
        exposure_classifier=exposure_classifier,
    )

    engine.classify(inputs)

    assert regime_classifier.last_input is inputs.regime
    assert risk_classifier.last_input is inputs.risk
    assert economic_classifier.last_input is inputs.economic
    assert exposure_classifier.last_input is inputs.exposure
