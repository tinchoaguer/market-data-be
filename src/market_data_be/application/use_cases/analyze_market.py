from market_data_be.application.contracts.market_data_provider import MarketDataProvider
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.analysis.models.analysis_result import AnalysisResult


class AnalyzeMarket:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        engine: MarketAnalysisEngine,
    ) -> None:
        self._provider = provider
        self._engine = engine

    def execute(self, symbol: str) -> AnalysisResult:
        market_data = self._provider.get_market_data(symbol)
        return self._engine.analyze(market_data)
