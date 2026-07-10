from ..models.inputs.exposure import ExposureClassifierInput
from ..models.signal import ClassificationSignal

SOURCE = "exposure"


class ExposureClassifier:
    def classify(
        self,
        assessment: ExposureClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        capacity = assessment.available_capacity_pct

        if capacity >= 50:
            score, reason = 0.30, "ample_capacity"
        elif capacity >= 20:
            score, reason = 0.10, "limited_capacity"
        else:
            score, reason = -0.20, "constrained_capacity"

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
