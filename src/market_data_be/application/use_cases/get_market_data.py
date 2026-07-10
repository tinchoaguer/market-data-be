from market_data_be.application.contracts.market_data_provider import MarketDataProvider
from market_data_be.modules.analysis.models.market import MarketData


class GetMarketData:
    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def execute(self, symbol: str) -> MarketData:
        return self._provider.get_market_data(symbol)
