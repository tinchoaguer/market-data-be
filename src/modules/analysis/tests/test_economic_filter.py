from trading_engine.app.engine.analyzers.economic_filter import (
    INSUFFICIENT_DATA_EDGE,
    MIN_KLINES,
    EconomicFilter,
)
from trading_engine.app.engine.tests.fixtures import _candle, _market_data, _order_book


def _range_friendly_series(count: int = 35):
    """Moderate ATR% (~0.4%) with stable participation."""
    candles = []
    price = 100.0
    for _ in range(count):
        o = price
        c = price + 0.2
        h = max(o, c) + 0.2
        l = min(o, c) - 0.2
        candles.append(_candle(o, h, l, c, base_volume=100.0))
        price = c
    return candles


def test_insufficient_klines_returns_neutral_edge():
    filter_ = EconomicFilter()
    candles = _range_friendly_series(MIN_KLINES - 1)
    assessment = filter_.assess(_market_data(candles))
    assert assessment.edge == INSUFFICIENT_DATA_EDGE
    assert assessment.insufficient_data


def test_bid_heavy_book_increases_edge():
    filter_ = EconomicFilter()
    candles = _range_friendly_series()
    balanced = _market_data(
        candles,
        order_book=_order_book(
            bids=[("100", "10")],
            asks=[("100.05", "10")],
        ),
    )
    bid_heavy = _market_data(
        candles,
        order_book=_order_book(
            bids=[("100", "50")],
            asks=[("100.05", "5")],
        ),
    )
    assert filter_.assess(bid_heavy).edge > filter_.assess(balanced).edge


def test_wide_spread_reduces_edge():
    filter_ = EconomicFilter()
    candles = _range_friendly_series()
    tight = _market_data(
        candles,
        order_book=_order_book(
            bids=[("100", "10")],
            asks=[("100.01", "10")],
        ),
    )
    wide = _market_data(
        candles,
        order_book=_order_book(
            bids=[("100", "10")],
            asks=[("102", "10")],
        ),
    )
    assert filter_.assess(tight).edge > filter_.assess(wide).edge


def test_volume_spike_reduces_activity_component():
    filter_ = EconomicFilter()
    normal = _range_friendly_series()
    spiked = list(normal)
    spiked[-1] = _candle(100.0, 100.8, 99.2, 100.0, base_volume=500.0)
    normal_edge = filter_.assess(_market_data(normal)).edge
    spiked_edge = filter_.assess(_market_data(spiked)).edge
    assert spiked_edge < normal_edge


def test_edge_bounded_minus_one_to_one():
    filter_ = EconomicFilter()
    candles = _range_friendly_series()
    edge = filter_.assess(_market_data(candles)).edge
    assert -1.0 <= edge <= 1.0
