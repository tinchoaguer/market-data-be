import pytest

from trading_engine.app.engine.analyzers.risk_engine import (
    INSUFFICIENT_DATA_SCORE,
    MIN_KLINES,
    RiskEngine,
)
from trading_engine.app.engine.models import MarketRegime, RegimeAssessment
from trading_engine.app.engine.tests.fixtures import _candle, _market_data, _order_book


def _flat_series(count: int = 35, base_volume: float = 100.0):
    return [
        _candle(100.0, 100.5, 99.5, 100.0, base_volume=base_volume, trade_count=10)
        for _ in range(count)
    ]


def _volatile_series(count: int = 55):
    candles = []
    price = 100.0
    for i in range(count):
        swing = 6.0 if i % 2 == 0 else -6.0
        o = price
        c = price + swing
        h = max(o, c) + 5.0
        l = min(o, c) - 5.0
        candles.append(_candle(o, h, l, c, base_volume=150.0 + i, trade_count=15))
        price = c
    return candles


def _regime(regime: MarketRegime) -> RegimeAssessment:
    return RegimeAssessment(regime=regime, reasons=())


def test_insufficient_klines_returns_cautious_default():
    engine = RiskEngine()
    assessment = engine.assess(_market_data(_flat_series(MIN_KLINES - 1)), _regime(MarketRegime.RANGE))
    assert assessment.score == INSUFFICIENT_DATA_SCORE
    assert assessment.insufficient_data


def test_range_low_vol_lower_risk_than_chaotic():
    engine = RiskEngine()
    flat = _flat_series()
    chaotic = _volatile_series()
    range_score = engine.assess(_market_data(flat), _regime(MarketRegime.RANGE)).score
    chaotic_score = engine.assess(_market_data(chaotic), _regime(MarketRegime.CHAOTIC)).score
    assert range_score < chaotic_score


def test_news_spike_highest_regime_risk():
    engine = RiskEngine()
    candles = _flat_series()
    spike_score = engine.assess(_market_data(candles), _regime(MarketRegime.NEWS_SPIKE)).score
    range_score = engine.assess(_market_data(candles), _regime(MarketRegime.RANGE)).score
    assert spike_score > range_score
    assert spike_score >= 0.7


def test_liquidity_stress_increases_score():
    engine = RiskEngine()
    candles = _flat_series()
    stressed_candles = candles[:-1] + [
        _candle(100.0, 100.5, 99.5, 100.0, base_volume=400.0, trade_count=10)
    ]
    balanced = engine.assess(_market_data(candles), _regime(MarketRegime.RANGE)).score
    stressed = engine.assess(
        _market_data(
            stressed_candles,
            order_book=_order_book(
                bids=[("100", "10")],
                asks=[("101", "1")],
            ),
        ),
        _regime(MarketRegime.RANGE),
    ).score
    assert stressed > balanced


def test_score_bounded_zero_to_one():
    engine = RiskEngine()
    score = engine.assess(_market_data(_volatile_series()), _regime(MarketRegime.CHAOTIC)).score
    assert 0.0 <= score <= 1.0


def test_trend_scores_between_range_and_spike():
    engine = RiskEngine()
    candles = _flat_series()
    trend_up = engine.assess(_market_data(candles), _regime(MarketRegime.TREND_UP)).score
    trend_down = engine.assess(_market_data(candles), _regime(MarketRegime.TREND_DOWN)).score
    range_score = engine.assess(_market_data(candles), _regime(MarketRegime.RANGE)).score
    spike_score = engine.assess(_market_data(candles), _regime(MarketRegime.NEWS_SPIKE)).score
    assert range_score < trend_up < spike_score
    assert range_score < trend_down < spike_score
