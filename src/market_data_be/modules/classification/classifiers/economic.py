from ..models.inputs.economic import EconomicClassifierInput
from ..models.signal import ClassificationSignal
from ..reason_codes import MODERATE_EDGE, NEGATIVE_EDGE, NEUTRAL_EDGE, STRONG_EDGE

SOURCE = "economic"


class EconomicClassifier:
    def classify(
        self,
        assessment: EconomicClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        edge = assessment.edge

        if edge >= 0.70:
            score, reason = 0.40, STRONG_EDGE
        elif edge >= 0.40:
            score, reason = 0.20, MODERATE_EDGE
        elif edge >= 0.00:
            score, reason = 0.00, NEUTRAL_EDGE
        else:
            score, reason = -0.30, NEGATIVE_EDGE

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
