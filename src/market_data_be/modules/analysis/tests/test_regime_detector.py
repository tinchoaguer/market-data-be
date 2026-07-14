import pytest

from market_data_be.modules.analysis.analyzers.regime_detector import MIN_KLINES, RegimeDetector
from market_data_be.modules.analysis.models import MarketRegime
from market_data_be.modules.analysis.reason_codes import REGIME_REASON_CODES
from market_data_be.modules.analysis.tests.fixtures import _candle, _market_data


def _flat_range_series(count: int = 35):
    return [
        _candle(100.0, 100.5, 99.5, 100.0, base_volume=100.0, trade_count=10, taker_ratio=0.5)
        for _ in range(count)
    ]


def _uptrend_series(count: int = 35):
    candles = []
    price = 100.0
    low = 99.0
    for _ in range(count):
        o = price
        c = price + 3.0
        low += 1.0
        h = c + 2.0
        candles.append(_candle(o, h, low, c, base_volume=120.0, trade_count=12, taker_ratio=0.6))
        price = c
    return candles


def _chaotic_series(count: int = 55):
    candles = []
    price = 100.0
    for i in range(count):
        swing = 8.0 if i % 2 == 0 else -8.0
        o = price
        c = price + swing
        h = max(o, c) + 6.0
        l = min(o, c) - 6.0
        vol = 150.0 + (i % 5) * 30.0
        candles.append(_candle(o, h, l, c, base_volume=vol, trade_count=20, taker_ratio=0.5))
        price = c
    return candles


def _news_spike_series(count: int = 35):
    candles = _flat_range_series(count - 1)
    candles.append(
        _candle(
            100.0,
            130.0,
            95.0,
            125.0,
            base_volume=400.0,
            trade_count=40,
            taker_ratio=0.7,
        )
    )
    return candles


def test_insufficient_klines_defaults_to_range():
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(_flat_range_series(MIN_KLINES - 1)))
    assert assessment.regime == MarketRegime.RANGE
    assert assessment.insufficient_data


def test_flat_low_vol_detects_range():
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(_flat_range_series()))
    assert assessment.regime == MarketRegime.RANGE


def test_news_spike_detected():
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(_news_spike_series()))
    assert assessment.regime == MarketRegime.NEWS_SPIKE
    assert assessment.reasons


def test_uptrend_detected():
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(_uptrend_series()))
    assert assessment.regime == MarketRegime.TREND_UP


def test_chaotic_detected():
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(_chaotic_series()))
    assert assessment.regime == MarketRegime.CHAOTIC


def test_downtrend_detected():
    candles = []
    price = 200.0
    low = 199.0
    for _ in range(35):
        o = price
        c = price - 3.0
        h = o + 1.0
        low -= 1.0
        candles.append(_candle(o, h, low, c, base_volume=120.0, trade_count=12, taker_ratio=0.4))
        price = c
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(candles))
    assert assessment.regime == MarketRegime.TREND_DOWN


def _downtrend_series(count: int = 35):
    candles = []
    price = 200.0
    low = 199.0
    for _ in range(count):
        o = price
        c = price - 3.0
        h = o + 1.0
        low -= 1.0
        candles.append(_candle(o, h, low, c, base_volume=120.0, trade_count=12, taker_ratio=0.4))
        price = c
    return candles


@pytest.mark.parametrize(
    "candles",
    [
        _flat_range_series(MIN_KLINES - 1),
        _flat_range_series(),
        _uptrend_series(),
        _downtrend_series(),
        _chaotic_series(),
        _news_spike_series(),
    ],
)
def test_regime_detector_emits_only_declared_reason_codes(candles) -> None:
    detector = RegimeDetector()
    assessment = detector.assess(_market_data(candles))

    assert assessment.reasons
    for reason in assessment.reasons:
        assert reason in REGIME_REASON_CODES

