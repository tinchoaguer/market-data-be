from ..models.inputs.exposure import ExposureClassifierInput
from ..models.signal import ClassificationSignal
from ..reason_codes import AMPLE_CAPACITY, CONSTRAINED_CAPACITY, LIMITED_CAPACITY

SOURCE = "exposure"


class ExposureClassifier:
    def classify(
        self,
        assessment: ExposureClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        capacity = assessment.available_capacity_pct

        if capacity >= 50:
            score, reason = 0.30, AMPLE_CAPACITY
        elif capacity >= 20:
            score, reason = 0.10, LIMITED_CAPACITY
        else:
            score, reason = -0.20, CONSTRAINED_CAPACITY

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
