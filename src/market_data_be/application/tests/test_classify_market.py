from decimal import Decimal

import pytest

from market_data_be.application.use_cases.classify_market import ClassifyMarket
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
from market_data_be.modules.analysis.models.portfolio import PortfolioState
from market_data_be.modules.analysis.models.strategy_catalog import CatalogResult
from market_data_be.modules.classification.market_classification_engine import (
    MarketClassificationEngine,
)
from market_data_be.modules.classification.models.classification_inputs import (
    ClassificationInputs,
)
from market_data_be.modules.classification.models.classification_result import (
    ClassificationResult,
)
from market_data_be.modules.classification.models.signal import ClassificationSignal


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
        self.last_portfolio_state: PortfolioState | None = None

    def analyze(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState | None = None,
    ) -> AnalysisResult:
        self.last_market_data = market_data
        self.last_portfolio_state = portfolio_state
        return self._result


class StubMarketClassificationEngine:
    def __init__(self, result: ClassificationResult) -> None:
        self._result = result
        self.last_inputs: ClassificationInputs | None = None

    def classify(self, inputs: ClassificationInputs) -> ClassificationResult:
        self.last_inputs = inputs
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
            catalog_reason="test",
        ),
    )


def _sample_classification_result(symbol: str = "BTC/USDT") -> ClassificationResult:
    signal = ClassificationSignal(source="test", score=0.0, reason="stub")
    return ClassificationResult(
        symbol=symbol,
        regime=(signal,),
        risk=(signal,),
        economic=(signal,),
        exposure=(signal,),
    )


def _build_use_case(
    *,
    provider: FakeMarketDataProvider,
    engine: StubMarketAnalysisEngine,
    classification_engine: StubMarketClassificationEngine,
) -> ClassifyMarket:
    return ClassifyMarket(
        provider=provider,
        engine=engine,
        classification_engine=classification_engine,
    )


def test_classify_market_retrieves_data_via_provider_when_market_data_omitted() -> None:
    market_data = _sample_market_data()
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result())
    classification_engine = StubMarketClassificationEngine(
        _sample_classification_result()
    )
    use_case = _build_use_case(
        provider=provider,
        engine=engine,
        classification_engine=classification_engine,
    )

    result = use_case.execute("BTC/USDT")

    assert provider.call_count == 1
    assert provider.last_symbol == "BTC/USDT"
    assert result.symbol == "BTC/USDT"


def test_classify_market_skips_provider_when_market_data_supplied() -> None:
    market_data = _sample_market_data("ETH/USDT")
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result("ETH/USDT"))
    classification_engine = StubMarketClassificationEngine(
        _sample_classification_result("ETH/USDT")
    )
    use_case = _build_use_case(
        provider=provider,
        engine=engine,
        classification_engine=classification_engine,
    )

    result = use_case.execute("BTC/USDT", market_data=market_data)

    assert provider.call_count == 0
    assert engine.last_market_data is market_data
    assert result.symbol == "ETH/USDT"


def test_classify_market_forwards_portfolio_state_to_engine() -> None:
    market_data = _sample_market_data()
    portfolio_state = PortfolioState(total_value=25_000.0)
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result())
    classification_engine = StubMarketClassificationEngine(
        _sample_classification_result()
    )
    use_case = _build_use_case(
        provider=provider,
        engine=engine,
        classification_engine=classification_engine,
    )

    use_case.execute("BTC/USDT", portfolio_state=portfolio_state)

    assert engine.last_portfolio_state is portfolio_state


def test_classify_market_maps_analysis_to_classification_inputs() -> None:
    market_data = _sample_market_data()
    provider = FakeMarketDataProvider(market_data)
    analysis = _sample_analysis_result()
    engine = StubMarketAnalysisEngine(analysis)
    classification_engine = StubMarketClassificationEngine(
        _sample_classification_result()
    )
    use_case = _build_use_case(
        provider=provider,
        engine=engine,
        classification_engine=classification_engine,
    )

    use_case.execute("BTC/USDT", market_data=market_data)

    assert classification_engine.last_inputs is not None
    assert classification_engine.last_inputs.symbol == analysis.symbol
    assert classification_engine.last_inputs.regime.regime.value == analysis.regime.regime.value
    assert classification_engine.last_inputs.risk.score == analysis.risk.score
    assert classification_engine.last_inputs.economic.edge == analysis.economic.edge
    assert (
        classification_engine.last_inputs.exposure.available_capacity_pct
        == analysis.exposure.available_capacity_pct
    )


def _integration_use_case() -> ClassifyMarket:
    return ClassifyMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
        classification_engine=MarketClassificationEngine(),
    )


@pytest.mark.parametrize(
    "symbol",
    ["BTC/USDT", "ETH/USDT"],
)
def test_classify_market_integration_with_mock_provider(symbol: str) -> None:
    use_case = _integration_use_case()

    result = use_case.execute(symbol)

    assert result.symbol == symbol
    assert len(result.regime) >= 1
    assert len(result.risk) >= 1
    assert len(result.economic) >= 1
    assert len(result.exposure) >= 1
    assert result.regime[0].source == "regime"
    assert result.risk[0].source == "risk"
    assert result.economic[0].source == "economic"
    assert result.exposure[0].source == "exposure"
