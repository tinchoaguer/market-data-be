from ..models.inputs.risk import RiskClassifierInput
from ..models.signal import ClassificationSignal
from ..reason_codes import ELEVATED_RISK, HIGH_RISK, LOW_RISK, MODERATE_RISK

SOURCE = "risk"


class RiskClassifier:
    def classify(
        self,
        assessment: RiskClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        score_value = assessment.score

        if score_value < 0.30:
            score, reason = 0.30, LOW_RISK
        elif score_value < 0.60:
            score, reason = 0.10, MODERATE_RISK
        elif score_value < 0.80:
            score, reason = -0.20, ELEVATED_RISK
        else:
            score, reason = -0.40, HIGH_RISK

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
