from dataclasses import dataclass

from .signal import ClassificationSignal


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    symbol: str
    regime: tuple[ClassificationSignal, ...]
    risk: tuple[ClassificationSignal, ...]
    economic: tuple[ClassificationSignal, ...]
    exposure: tuple[ClassificationSignal, ...]
