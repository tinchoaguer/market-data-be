import json
from decimal import Decimal
from pathlib import Path

import pytest

from market_data_be.infrastructure.market_data.deserializer import market_data_from_dict
from market_data_be.modules.analysis.models import (
    Candle,
    CandleSeries,
    MarketData,
    OrderBook,
    OrderLevel,
    Timeframe,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = PROJECT_ROOT / "resources" / "market_data"


@pytest.mark.parametrize(
    ("filename", "symbol"),
    [
        ("btc_usdt.json", "BTC/USDT"),
        ("eth_usdt.json", "ETH/USDT"),
    ],
)
def test_market_data_from_dict_loads_fixture(filename: str, symbol: str) -> None:
    payload = json.loads((FIXTURES_DIR / filename).read_text(encoding="utf-8"))
    market_data = market_data_from_dict(payload)

    assert isinstance(market_data, MarketData)
    assert market_data.symbol == symbol
    assert isinstance(market_data.current_price, Decimal)
    assert isinstance(market_data.order_book, OrderBook)
    assert len(market_data.order_book.bids) >= 1
    assert len(market_data.order_book.asks) >= 1
    assert all(isinstance(level, OrderLevel) for level in market_data.order_book.bids)
    assert all(isinstance(level, OrderLevel) for level in market_data.order_book.asks)
    assert len(market_data.series) >= 1
    assert all(isinstance(series, CandleSeries) for series in market_data.series)
    assert all(
        isinstance(candle, Candle)
        for series in market_data.series
        for candle in series.candles
    )


def test_market_data_from_dict_invalid_timeframe_raises() -> None:
    payload = json.loads((FIXTURES_DIR / "btc_usdt.json").read_text(encoding="utf-8"))
    payload["series"][0]["timeframe"] = "invalid"

    with pytest.raises(ValueError):
        market_data_from_dict(payload)
