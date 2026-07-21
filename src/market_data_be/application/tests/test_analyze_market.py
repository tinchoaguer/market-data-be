from decimal import Decimal

import pytest

from market_data_be.application.use_cases.analyze_market import AnalyzeMarket
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.analysis.models.analysis_result import AnalysisResult
from market_data_be.modules.analysis.models.assessments import (
    EconomicAssessment,
    ExposureComponents,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)
from market_data_be.modules.analysis.models.enums import MarketRegime, StrategyType
from market_data_be.modules.analysis.models.market import (
    CandleSeries,
    MarketData,
    OrderBook,
    Timeframe,
)
from market_data_be.modules.analysis.models.message_ref import MessageRef
from market_data_be.modules.analysis.models.portfolio import PortfolioState
from market_data_be.modules.analysis.models.strategy_catalog import CatalogResult
from market_data_be.modules.analysis.narrative_codes import CATALOG_STRATEGY_ALLOWED


class FakeMarketDataProvider:
    def __init__(self, data: MarketData) -> None:
        self._data = data
        self.last_symbol: str | None = None
        self.call_count = 0

    def get_market_data(self, symbol: str) -> MarketData:
        self.last_symbol = symbol
        self.call_count += 1
        return self._data


class StubMarketAnalysisEngine:
    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self.last_market_data: MarketData | None = None
        self.analyze_call_count = 0
        self.received_portfolio_state: object = object()

    def analyze(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState | None = None,
    ) -> AnalysisResult:
        self.analyze_call_count += 1
        self.last_market_data = market_data
        self.received_portfolio_state = portfolio_state
        return self._result


def _sample_market_data(symbol: str = "BTC/USDT") -> MarketData:
    return MarketData(
        symbol=symbol,
        current_price=Decimal("100.00"),
        order_book=OrderBook(bids=(), asks=()),
        series=(
            CandleSeries(timeframe=Timeframe.M15, candles=()),
        ),
    )


def _sample_analysis_result(symbol: str = "BTC/USDT") -> AnalysisResult:
    return AnalysisResult(
        symbol=symbol,
        regime=RegimeAssessment(regime=MarketRegime.TREND_UP, reasons=("trend",)),
        risk=RiskAssessment(score=0.45, components=()),
        economic=EconomicAssessment(edge=0.55, components=()),
        exposure=ExposureProfile(
            symbol=symbol,
            total_value=10_000.0,
            exposure_pct=0.1,
            allocated_value=1_000.0,
            portfolio_exposure_pct=0.2,
            available_capacity_pct=80.0,
            symbol_weight_cap_pct=0.35,
            recommended_allocation_pct=0.15,
            recommended_allocation_value=1_500.0,
            components=ExposureComponents(
                vol_budget_pct=0.12,
                liquidity_cap_value=5_000.0,
            ),
        ),
        catalog=CatalogResult(
            allowed_strategies=(StrategyType.TREND_FOLLOWING,),
            forbidden_strategies=(),
            preferred_strategy=StrategyType.TREND_FOLLOWING,
            catalog_reason=MessageRef.of(
                CATALOG_STRATEGY_ALLOWED,
                strategy=StrategyType.TREND_FOLLOWING.value,
            ),
        ),
    )


def test_analyze_market_delegates_provider_then_engine_without_portfolio() -> None:
    market_data = _sample_market_data()
    analysis = _sample_analysis_result()
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(analysis)
    use_case = AnalyzeMarket(provider=provider, engine=engine)

    result = use_case.execute("BTC/USDT")

    assert provider.call_count == 1
    assert provider.last_symbol == "BTC/USDT"
    assert engine.analyze_call_count == 1
    assert engine.last_market_data is market_data
    assert engine.received_portfolio_state is None
    assert result is analysis


@pytest.mark.parametrize(
    "symbol",
    ["BTC/USDT", "ETH/USDT"],
)
def test_analyze_market_integration_with_mock_provider(symbol: str) -> None:
    use_case = AnalyzeMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
    )

    result = use_case.execute(symbol)

    assert result.symbol == symbol
    assert result.regime is not None
    assert result.risk is not None
    assert result.economic is not None
    assert result.exposure is not None
    assert result.catalog is not None
