import pytest

from market_data_be.modules.analysis.analyzers.portfolio_manager import (
    MIN_KLINES,
    PortfolioManager,
)
from market_data_be.modules.analysis.models import PortfolioConstraints
from market_data_be.modules.analysis.tests.fixtures import (
    _candle,
    _market_data,
    _order_book,
    _portfolio_state,
)


def _flat_series(count: int = 35):
    return [_candle(100.0, 100.5, 99.5, 100.0) for _ in range(count)]


def _volatile_series(count: int = 35):
    candles = []
    price = 100.0
    for i in range(count):
        swing = 5.0 if i % 2 == 0 else -5.0
        o = price
        c = price + swing
        h = max(o, c) + 4.0
        l = min(o, c) - 4.0
        candles.append(_candle(o, h, l, c))
        price = c
    return candles


def test_fresh_portfolio_has_zero_exposure_and_positive_capacity():
    manager = PortfolioManager()
    exposure = manager.evaluate(_market_data(_flat_series()), _portfolio_state())
    assert exposure.exposure_pct == 0.0
    assert exposure.allocated_value == 0.0
    assert exposure.total_value == 10_000.0
    assert exposure.recommended_allocation_value > 0.0
    assert exposure.available_capacity_pct == pytest.approx(1.0)


def test_allocation_increases_exposure_pct():
    manager = PortfolioManager()
    state = _portfolio_state(total_value=1000.0, allocations=[("BTCUSDT", 250.0)])
    exposure = manager.evaluate(_market_data(_flat_series()), state)
    assert exposure.exposure_pct == pytest.approx(0.25)
    assert exposure.allocated_value == pytest.approx(250.0)
    assert exposure.portfolio_exposure_pct == pytest.approx(0.25)


def test_high_volatility_reduces_recommended_allocation():
    manager = PortfolioManager()
    deep_book = _order_book(bids=[("100", "500")], asks=[("100.05", "500")])
    state = _portfolio_state()
    calm = manager.evaluate(_market_data(_flat_series(), order_book=deep_book), state)
    volatile = manager.evaluate(_market_data(_volatile_series(), order_book=deep_book), state)
    assert volatile.recommended_allocation_value < calm.recommended_allocation_value


def test_symbol_cap_limits_recommended_allocation():
    manager = PortfolioManager()
    state = _portfolio_state(
        total_value=1000.0,
        allocations=[("BTCUSDT", 1000.0 * PortfolioConstraints().max_symbol_weight)],
    )
    exposure = manager.evaluate(_market_data(_flat_series()), state)
    assert exposure.recommended_allocation_value == 0.0
    assert exposure.recommended_allocation_pct == 0.0


def test_reduced_allocation_frees_capacity():
    manager = PortfolioManager()
    state = _portfolio_state(total_value=1000.0, allocations=[("BTCUSDT", 200.0)])
    exposure = manager.evaluate(_market_data(_flat_series()), state)
    assert exposure.allocated_value == pytest.approx(200.0)
    assert exposure.exposure_pct == pytest.approx(0.2)


def test_insufficient_klines_uses_conservative_recommendation():
    manager = PortfolioManager()
    exposure = manager.evaluate(
        _market_data(_flat_series(MIN_KLINES - 1)),
        _portfolio_state(),
    )
    assert exposure.recommended_allocation_pct == pytest.approx(0.05)
    assert exposure.exposure_pct == 0.0
    assert exposure.insufficient_data
