from ..models.inputs.regime import RegimeClassifierInput, RegimeLabel
from ..models.signal import ClassificationSignal
from ..reason_codes import CHAOTIC, NEWS_SPIKE, RANGE, TREND_DOWN, TREND_UP

SOURCE = "regime"


class RegimeClassifier:
    def classify(
        self,
        assessment: RegimeClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        match assessment.regime:
            case RegimeLabel.TREND_UP:
                score, reason = 0.40, TREND_UP
            case RegimeLabel.TREND_DOWN:
                score, reason = -0.40, TREND_DOWN
            case RegimeLabel.RANGE:
                score, reason = 0.00, RANGE
            case RegimeLabel.CHAOTIC:
                score, reason = -0.20, CHAOTIC
            case RegimeLabel.NEWS_SPIKE:
                score, reason = -0.40, NEWS_SPIKE
            case _:
                raise ValueError(f"unknown regime: {assessment.regime!r}")

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
