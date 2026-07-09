from dataclasses import replace

from market_data_be.modules.analysis.analyzers.portfolio_manager import PortfolioManager
from market_data_be.modules.analysis.models import (
    EconomicAssessment,
    MarketRegime,
    RegimeAssessment,
    RiskAssessment,
    StrategyType,
)
from market_data_be.modules.analysis.synthesis.catalog_builder import (
    HIGH_RISK_GATE,
    CatalogBuilder,
)
from market_data_be.modules.analysis.tests.fixtures import _candle, _market_data, _order_book, _portfolio_state


def _market_data_series(count: int = 35, price: float = 100.0):
    candles = [_candle(price, price + 1, price - 1, price) for _ in range(count)]
    return _market_data(
        candles,
        price=price,
        order_book=_order_book(
            bids=[("100", "10")],
            asks=[("100.05", "10")],
        ),
    )


def _evaluate(
    regime: MarketRegime,
    risk_score: float,
    economic_edge: float,
    allocation_value: float = 1000.0,
):
    market_data = _market_data_series()
    regime_assessment = RegimeAssessment(regime=regime, reasons=("test",))
    risk = RiskAssessment(score=risk_score, components=())
    economic = EconomicAssessment(edge=economic_edge, components=())
    exposure = PortfolioManager().evaluate(
        market_data,
        _portfolio_state(total_value=10_000.0),
    )
    exposure = replace(exposure, recommended_allocation_value=allocation_value)
    return CatalogBuilder().evaluate(regime_assessment, risk, economic, exposure)


def test_extreme_regime_hard_gates_all_strategies():
    result = _evaluate(MarketRegime.NEWS_SPIKE, risk_score=0.2, economic_edge=0.5)
    assert result.is_hard_gated
    assert result.allowed_strategies == ()
    assert StrategyType.RANGE_BOUNDING in result.forbidden_strategies
    assert result.preferred_strategy == StrategyType.OTHER


def test_high_risk_hard_gate():
    result = _evaluate(MarketRegime.RANGE, risk_score=HIGH_RISK_GATE, economic_edge=0.5)
    assert result.is_hard_gated
    assert "risk score too high" in result.hard_gate_reason


def test_negative_edge_hard_gate():
    result = _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=-0.01)
    assert result.is_hard_gated
    assert "negative economic edge" in result.hard_gate_reason


def test_no_capacity_hard_gate():
    result = _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=0.5, allocation_value=0.0)
    assert result.is_hard_gated
    assert "no portfolio capacity" in result.hard_gate_reason


def test_range_allows_range_bounding_and_ping_pong_when_quality_is_high():
    result = _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=0.4)
    assert not result.is_hard_gated
    assert result.allowed_strategies == (
        StrategyType.RANGE_BOUNDING,
        StrategyType.PING_PONG,
    )
    assert result.preferred_strategy == StrategyType.RANGE_BOUNDING


def test_trend_allows_only_trend_following_strategy():
    result = _evaluate(MarketRegime.TREND_UP, risk_score=0.4, economic_edge=0.2)
    assert result.allowed_strategies == (StrategyType.TREND_FOLLOWING,)
    assert StrategyType.RANGE_BOUNDING in result.forbidden_strategies
