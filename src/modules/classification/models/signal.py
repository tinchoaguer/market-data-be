from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassificationSignal:
    source: str
    score: float
    reason: str
