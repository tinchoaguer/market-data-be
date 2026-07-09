from decimal import Decimal

from market_data_be.application.use_cases.get_market_data import GetMarketData
from market_data_be.modules.analysis.models.market import (
    CandleSeries,
    MarketData,
    OrderBook,
    Timeframe,
)


class FakeMarketDataProvider:
    def __init__(self, data: MarketData) -> None:
        self._data = data
        self.last_symbol: str | None = None

    def get_market_data(self, symbol: str) -> MarketData:
        self.last_symbol = symbol
        return self._data


def _sample_market_data() -> MarketData:
    return MarketData(
        symbol="FAKE/USDT",
        current_price=Decimal("100.00"),
        order_book=OrderBook(bids=(), asks=()),
        series=(
            CandleSeries(timeframe=Timeframe.M15, candles=()),
        ),
    )


def test_get_market_data_delegates_to_provider() -> None:
    expected = _sample_market_data()
    fake_provider = FakeMarketDataProvider(expected)
    use_case = GetMarketData(fake_provider)

    result = use_case.execute("BTC/USDT")

    assert result is expected
    assert fake_provider.last_symbol == "BTC/USDT"


def test_get_market_data_allows_provider_substitution() -> None:
    first = _sample_market_data()
    second = MarketData(
        symbol="OTHER/USDT",
        current_price=Decimal("200.00"),
        order_book=OrderBook(bids=(), asks=()),
        series=(
            CandleSeries(timeframe=Timeframe.M15, candles=()),
        ),
    )

    first_use_case = GetMarketData(FakeMarketDataProvider(first))
    second_use_case = GetMarketData(FakeMarketDataProvider(second))

    assert first_use_case.execute("BTC/USDT").symbol == "FAKE/USDT"
    assert second_use_case.execute("ETH/USDT").symbol == "OTHER/USDT"
