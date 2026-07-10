"""Single entry point for deterministic market classification."""

from .classifiers.economic import EconomicClassifier
from .classifiers.exposure import ExposureClassifier
from .classifiers.regime import RegimeClassifier
from .classifiers.risk import RiskClassifier
from .contracts.classifier import Classifier
from .models.classification_inputs import ClassificationInputs
from .models.classification_result import ClassificationResult
from .models.inputs.economic import EconomicClassifierInput
from .models.inputs.exposure import ExposureClassifierInput
from .models.inputs.regime import RegimeClassifierInput
from .models.inputs.risk import RiskClassifierInput


class MarketClassificationEngine:
    def __init__(
        self,
        *,
        regime_classifier: Classifier[RegimeClassifierInput] | None = None,
        risk_classifier: Classifier[RiskClassifierInput] | None = None,
        economic_classifier: Classifier[EconomicClassifierInput] | None = None,
        exposure_classifier: Classifier[ExposureClassifierInput] | None = None,
    ) -> None:
        self._regime_classifier = regime_classifier or RegimeClassifier()
        self._risk_classifier = risk_classifier or RiskClassifier()
        self._economic_classifier = economic_classifier or EconomicClassifier()
        self._exposure_classifier = exposure_classifier or ExposureClassifier()

    def classify(self, inputs: ClassificationInputs) -> ClassificationResult:
        return ClassificationResult(
            symbol=inputs.symbol,
            regime=self._regime_classifier.classify(inputs.regime),
            risk=self._risk_classifier.classify(inputs.risk),
            economic=self._economic_classifier.classify(inputs.economic),
            exposure=self._exposure_classifier.classify(inputs.exposure),
        )
