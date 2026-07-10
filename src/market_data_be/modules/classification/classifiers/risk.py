from ..models.inputs.risk import RiskClassifierInput
from ..models.signal import ClassificationSignal

SOURCE = "risk"


class RiskClassifier:
    def classify(
        self,
        assessment: RiskClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        score_value = assessment.score

        if score_value < 0.30:
            score, reason = 0.30, "low_risk"
        elif score_value < 0.60:
            score, reason = 0.10, "moderate_risk"
        elif score_value < 0.80:
            score, reason = -0.20, "elevated_risk"
        else:
            score, reason = -0.40, "high_risk"

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
