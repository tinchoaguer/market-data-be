from typing import Protocol

from market_data_be.modules.analysis.models.market import MarketData


class MarketDataProvider(Protocol):
    def get_market_data(self, symbol: str) -> MarketData:
        """Retrieve market data for the given trading pair symbol."""
        ...
