from market_data_be.application.contracts.market_data_provider import MarketDataProvider
from market_data_be.application.mappers.assessment_to_classification import (
    to_classification_inputs,
)
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.analysis.models.market import MarketData
from market_data_be.modules.analysis.models.portfolio import PortfolioState
from market_data_be.modules.classification.market_classification_engine import (
    MarketClassificationEngine,
)
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)


class ClassifyMarket:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        engine: MarketAnalysisEngine,
        classification_engine: MarketClassificationEngine,
    ) -> None:
        self._provider = provider
        self._engine = engine
        self._classification_engine = classification_engine

    def execute(
        self,
        symbol: str,
        *,
        market_data: MarketData | None = None,
        portfolio_state: PortfolioState | None = None,
    ) -> ClassificationResult:
        resolved = (
            market_data if market_data is not None else self._provider.get_market_data(symbol)
        )
        analysis = self._engine.analyze(resolved, portfolio_state)
        inputs = to_classification_inputs(analysis)
        return self._classification_engine.classify(inputs)
