from ..models.inputs.regime import RegimeClassifierInput, RegimeLabel
from ..models.signal import ClassificationSignal

SOURCE = "regime"


class RegimeClassifier:
    def classify(
        self,
        assessment: RegimeClassifierInput,
    ) -> tuple[ClassificationSignal, ...]:
        match assessment.regime:
            case RegimeLabel.TREND_UP:
                score, reason = 0.40, "trend_up"
            case RegimeLabel.TREND_DOWN:
                score, reason = -0.40, "trend_down"
            case RegimeLabel.RANGE:
                score, reason = 0.00, "range"
            case RegimeLabel.CHAOTIC:
                score, reason = -0.20, "chaotic"
            case RegimeLabel.NEWS_SPIKE:
                score, reason = -0.40, "news_spike"
            case _:
                raise ValueError(f"unknown regime: {assessment.regime!r}")

        return (
            ClassificationSignal(
                source=SOURCE,
                score=score,
                reason=reason,
            ),
        )
