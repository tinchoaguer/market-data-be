from market_data_be.infrastructure.http.dtos.classification import (
    ClassificationSignalResponse,
    MarketClassificationResponse,
)
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)
from market_data_be.modules.classification.models.signal import ClassificationSignal


def _map_signals(
    signals: tuple[ClassificationSignal, ...],
) -> list[ClassificationSignalResponse]:
    return [
        ClassificationSignalResponse(
            source=signal.source,
            score=signal.score,
            reason=signal.reason,
        )
        for signal in signals
    ]


def map_market_classification_to_response(
    classification: ClassificationResult,
) -> MarketClassificationResponse:
    return MarketClassificationResponse(
        symbol=classification.symbol,
        regime=_map_signals(classification.regime),
        risk=_map_signals(classification.risk),
        economic=_map_signals(classification.economic),
        exposure=_map_signals(classification.exposure),
    )
