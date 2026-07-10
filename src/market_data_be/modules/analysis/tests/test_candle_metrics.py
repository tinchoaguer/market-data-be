import pytest

from market_data_be.modules.analysis.analyzers.candle_metrics import (
    atr,
    book_top_depth_base,
    close_n_bars_ago,
    direction_changes,
    higher_highs_higher_lows,
    latest_close,
    order_book_imbalance,
    relative_volume,
    returns_volatility,
    sma,
    spread_bps,
    taker_buy_ratio,
    total_volume,
    true_range,
    wilder_di_adx,
)
from market_data_be.modules.analysis.tests.fixtures import _candle, _order_book


def test_latest_close_and_close_n_bars_ago():
    candles = [_candle(90, 91, 89, 90), _candle(95, 96, 94, 95), _candle(100, 101, 99, 100)]
    assert latest_close(candles) == 100
    assert close_n_bars_ago(candles, 1) == 95


def test_true_range():
    assert true_range(105, 95, 100) == 10


def test_atr_constant_range():
    candles = [_candle(100, 102, 98, 100) for _ in range(20)]
    assert atr(candles, period=14) == pytest.approx(4.0)


def test_returns_volatility_zero_for_flat_prices():
    candles = [_candle(100, 101, 99, 100) for _ in range(25)]
    assert returns_volatility(candles) == 0.0


def test_total_volume_sums_last_n():
    candles = [
        _candle(100, 101, 99, 100),
        _candle(100, 101, 99, 100, base_volume=200),
        _candle(100, 101, 99, 100, base_volume=300),
    ]
    assert total_volume(candles, last_n=2) == 500


def test_sma_and_relative_volume():
    candles = [_candle(100 + i, 101 + i, 99 + i, 100 + i) for i in range(24)]
    candles.append(_candle(124, 125, 123, 124, base_volume=300))
    assert sma(candles, 20) == pytest.approx(sum(range(105, 125)) / 20)
    expected_avg = sum(float(c.base_volume) for c in candles[-20:]) / 20
    assert relative_volume(candles) == pytest.approx(300.0 / expected_avg)


def test_wilder_di_adx_uptrend():
    candles = []
    price = 100.0
    low = 99.0
    for _ in range(35):
        o = price
        c = price + 2.0
        low += 0.5
        h = c + 1.0
        candles.append(_candle(o, h, low, c))
        price = c
    adx, plus_di, minus_di = wilder_di_adx(candles)
    assert adx > 20
    assert plus_di > minus_di


def test_higher_highs_and_direction_changes():
    candles = []
    price = 100.0
    low = 99.0
    for _ in range(12):
        o = price
        c = price + 1.0
        low += 0.5
        h = c + 0.5
        candles.append(_candle(o, h, low, c))
        price = c
    assert higher_highs_higher_lows(candles, window=10)

    zigzag = [
        _candle(100, 101, 99, 100),
        _candle(105, 106, 104, 105),
        _candle(100, 101, 99, 100),
        _candle(105, 106, 104, 105),
        _candle(100, 101, 99, 100),
        _candle(105, 106, 104, 105),
    ]
    assert direction_changes(zigzag, window=5) >= 3


def test_taker_buy_ratio():
    candles = [_candle(100, 101, 99, 100, taker_ratio=0.6) for _ in range(3)]
    assert taker_buy_ratio(candles) == pytest.approx(0.6)


def test_order_book_imbalance_balanced_and_skewed():
    balanced = _order_book(bids=[("100", "1")], asks=[("101", "1")])
    assert order_book_imbalance(balanced) == 0.0

    bid_heavy = _order_book(bids=[("100", "3")], asks=[("101", "1")])
    assert order_book_imbalance(bid_heavy) == pytest.approx(0.5)

    assert order_book_imbalance(_order_book()) == 0.0


def test_book_top_depth_base():
    book = _order_book(
        bids=[("100", "2"), ("99", "3")],
        asks=[("101", "4")],
    )
    assert book_top_depth_base(book, levels=2) == pytest.approx(9.0)
    assert book_top_depth_base(_order_book()) == 0.0


def test_spread_bps():
    book = _order_book(bids=[("100", "1")], asks=[("100.10", "1")])
    assert spread_bps(book) == pytest.approx(9.995, rel=1e-2)
    assert spread_bps(_order_book()) == 0.0
