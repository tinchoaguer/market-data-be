from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.analysis.models import MarketRegime, StrategyType
from market_data_be.modules.analysis.tests.fixtures import _candle, _market_data, _portfolio_state


def _flat_series(count: int = 35):
    return [_candle(100.0, 100.5, 99.5, 100.0) for _ in range(count)]


def test_engine_returns_complete_analysis_result():
    engine = MarketAnalysisEngine()
    result = engine.analyze(_market_data(_flat_series()))

    assert result.symbol == "BTCUSDT"
    assert result.regime.regime == MarketRegime.RANGE
    assert 0.0 <= result.risk.score <= 1.0
    assert -1.0 <= result.economic.edge <= 1.0
    assert result.exposure.recommended_allocation_value > 0.0
    assert result.catalog.preferred_strategy in {
        StrategyType.RANGE_BOUNDING,
        StrategyType.PING_PONG,
        StrategyType.OTHER,
    }


def test_engine_propagates_portfolio_state():
    engine = MarketAnalysisEngine()
    state = _portfolio_state(total_value=1000.0, allocations=[("BTCUSDT", 350.0)])
    result = engine.analyze(_market_data(_flat_series()), state)

    assert result.exposure.allocated_value == 350.0
    assert result.exposure.exposure_pct == 0.35
