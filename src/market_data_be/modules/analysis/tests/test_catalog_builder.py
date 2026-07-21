from dataclasses import replace
import re

from market_data_be.modules.analysis.analyzers.portfolio_manager import PortfolioManager
from market_data_be.modules.analysis.models import (
    EconomicAssessment,
    MarketRegime,
    MessageRef,
    RegimeAssessment,
    RiskAssessment,
    StrategyType,
)
from market_data_be.modules.analysis.narrative_codes import (
    CATALOG_STRATEGY_ALLOWED,
    CATALOG_WAIT,
    GATE_NEGATIVE_EDGE,
    GATE_NO_CAPACITY,
    GATE_RISK_TOO_HIGH,
    HARD_GATE_NEGATIVE_EDGE,
    HARD_GATE_NO_CAPACITY,
    HARD_GATE_RISK_TOO_HIGH,
    NARRATIVE_MESSAGE_CODES,
)
from market_data_be.modules.analysis.synthesis.catalog_builder import (
    HIGH_RISK_GATE,
    CatalogBuilder,
)
from market_data_be.modules.analysis.tests.fixtures import (
    _candle,
    _market_data,
    _order_book,
    _portfolio_state,
)

_PROSE_PATTERN = re.compile(r"[\s.,;:!?\"'`]")


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


def _assert_typed_message_ref(ref: MessageRef | None) -> None:
    assert ref is not None
    assert isinstance(ref, MessageRef)
    assert ref.code in NARRATIVE_MESSAGE_CODES
    for key, value in ref.params:
        assert isinstance(key, str) and key
        assert isinstance(value, (str, int, float, bool))
        if isinstance(value, str):
            assert value
            assert _PROSE_PATTERN.search(value) is None


def test_extreme_regime_hard_gates_all_strategies():
    result = _evaluate(MarketRegime.NEWS_SPIKE, risk_score=0.2, economic_edge=0.5)
    assert result.is_hard_gated
    assert result.allowed_strategies == ()
    assert StrategyType.RANGE_BOUNDING in result.forbidden_strategies
    assert result.preferred_strategy == StrategyType.OTHER
    _assert_typed_message_ref(result.hard_gate_reason)
    _assert_typed_message_ref(result.catalog_reason)
    assert result.catalog_reason.code == CATALOG_WAIT


def test_high_risk_hard_gate():
    result = _evaluate(MarketRegime.RANGE, risk_score=HIGH_RISK_GATE, economic_edge=0.5)
    assert result.is_hard_gated
    assert result.hard_gate_reason is not None
    assert result.hard_gate_reason.code == HARD_GATE_RISK_TOO_HIGH
    assert dict(result.hard_gate_reason.params)["risk_score"] == HIGH_RISK_GATE
    assert result.catalog_reason.code == CATALOG_WAIT
    assert dict(result.catalog_reason.params)["gate"] == GATE_RISK_TOO_HIGH
    _assert_typed_message_ref(result.hard_gate_reason)
    _assert_typed_message_ref(result.catalog_reason)


def test_negative_edge_hard_gate():
    result = _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=-0.01)
    assert result.is_hard_gated
    assert result.hard_gate_reason is not None
    assert result.hard_gate_reason.code == HARD_GATE_NEGATIVE_EDGE
    assert dict(result.hard_gate_reason.params)["edge"] == -0.01
    assert dict(result.catalog_reason.params)["gate"] == GATE_NEGATIVE_EDGE
    _assert_typed_message_ref(result.hard_gate_reason)
    _assert_typed_message_ref(result.catalog_reason)


def test_no_capacity_hard_gate():
    result = _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=0.5, allocation_value=0.0)
    assert result.is_hard_gated
    assert result.hard_gate_reason is not None
    assert result.hard_gate_reason.code == HARD_GATE_NO_CAPACITY
    assert dict(result.catalog_reason.params)["gate"] == GATE_NO_CAPACITY
    _assert_typed_message_ref(result.hard_gate_reason)
    _assert_typed_message_ref(result.catalog_reason)


def test_range_allows_range_bounding_and_ping_pong_when_quality_is_high():
    result = _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=0.4)
    assert not result.is_hard_gated
    assert result.allowed_strategies == (
        StrategyType.RANGE_BOUNDING,
        StrategyType.PING_PONG,
    )
    assert result.preferred_strategy == StrategyType.RANGE_BOUNDING
    assert result.hard_gate_reason is None
    assert result.catalog_reason.code == CATALOG_STRATEGY_ALLOWED
    params = dict(result.catalog_reason.params)
    assert params["strategy"] == StrategyType.RANGE_BOUNDING.value
    assert params["regime"] == MarketRegime.RANGE.value
    _assert_typed_message_ref(result.catalog_reason)


def test_trend_allows_only_trend_following_strategy():
    result = _evaluate(MarketRegime.TREND_UP, risk_score=0.4, economic_edge=0.2)
    assert result.allowed_strategies == (StrategyType.TREND_FOLLOWING,)
    assert StrategyType.RANGE_BOUNDING in result.forbidden_strategies
    assert result.catalog_reason.code == CATALOG_STRATEGY_ALLOWED
    _assert_typed_message_ref(result.catalog_reason)


def test_catalog_narrative_never_emits_english_prose():
    cases = [
        _evaluate(MarketRegime.NEWS_SPIKE, risk_score=0.2, economic_edge=0.5),
        _evaluate(MarketRegime.RANGE, risk_score=HIGH_RISK_GATE, economic_edge=0.5),
        _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=-0.01),
        _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=0.5, allocation_value=0.0),
        _evaluate(MarketRegime.RANGE, risk_score=0.2, economic_edge=0.4),
        _evaluate(MarketRegime.TREND_UP, risk_score=0.4, economic_edge=0.2),
        _evaluate(MarketRegime.TREND_UP, risk_score=0.9, economic_edge=0.2),
        _evaluate(MarketRegime.CHAOTIC, risk_score=0.2, economic_edge=0.5),
    ]
    for result in cases:
        _assert_typed_message_ref(result.catalog_reason)
        if result.hard_gate_reason is not None:
            _assert_typed_message_ref(result.hard_gate_reason)
