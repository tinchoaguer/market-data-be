from ..models.inputs.economic import EconomicClassifierInput
from ..models.signal import ClassificationSignal

SOURCE = "economic"


class EconomicClassifier:
    def classify(
        self,
        assessment: EconomicClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        edge = assessment.edge

        if edge >= 0.70:
            score, reason = 0.40, "strong_edge"
        elif edge >= 0.40:
            score, reason = 0.20, "moderate_edge"
        elif edge >= 0.00:
            score, reason = 0.00, "neutral_edge"
        else:
            score, reason = -0.30, "negative_edge"

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
