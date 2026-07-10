from dataclasses import dataclass

from market_data_be.modules.classification.models.signal import ClassificationSignal


@dataclass(frozen=True, slots=True)
class MarketClassification:
    symbol: str
    regime: tuple[ClassificationSignal, ...]
    risk: tuple[ClassificationSignal, ...]
    economic: tuple[ClassificationSignal, ...]
    exposure: tuple[ClassificationSignal, ...]
