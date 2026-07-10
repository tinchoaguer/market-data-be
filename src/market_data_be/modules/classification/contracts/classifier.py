from typing import Protocol, TypeVar

from ..models.signal import ClassificationSignal

TAssessment = TypeVar("TAssessment")


class Classifier(Protocol[TAssessment]):
    def classify(
        self,
        assessment: TAssessment,
    ) -> tuple[ClassificationSignal, ...]:
        ...
