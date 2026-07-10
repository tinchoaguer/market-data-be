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
from market_data_be.modules.classification.classifiers.economic import EconomicClassifier
from market_data_be.modules.classification.classifiers.exposure import ExposureClassifier
from market_data_be.modules.classification.classifiers.regime import RegimeClassifier
from market_data_be.modules.classification.classifiers.risk import RiskClassifier
from market_data_be.modules.classification.models.inputs.economic import (
    EconomicClassifierInput,
)
from market_data_be.modules.classification.models.inputs.exposure import (
    ExposureClassifierInput,
)
from market_data_be.modules.classification.models.inputs.regime import RegimeClassifierInput
from market_data_be.modules.classification.models.inputs.risk import RiskClassifierInput
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


class RecordingClassifier:
    def __init__(self) -> None:
        self.last_input: object | None = None

    def classify(self, assessment: object) -> tuple[ClassificationSignal, ...]:
        self.last_input = assessment
        return (ClassificationSignal(source="test", score=0.0, reason="stub"),)


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


def _build_use_case(
    *,
    provider: FakeMarketDataProvider,
    engine: StubMarketAnalysisEngine,
    regime_classifier: RecordingClassifier | None = None,
    risk_classifier: RecordingClassifier | None = None,
    economic_classifier: RecordingClassifier | None = None,
    exposure_classifier: RecordingClassifier | None = None,
) -> ClassifyMarket:
    return ClassifyMarket(
        provider=provider,
        engine=engine,
        regime_classifier=regime_classifier or RecordingClassifier(),
        risk_classifier=risk_classifier or RecordingClassifier(),
        economic_classifier=economic_classifier or RecordingClassifier(),
        exposure_classifier=exposure_classifier or RecordingClassifier(),
    )


def test_classify_market_retrieves_data_via_provider_when_market_data_omitted() -> None:
    market_data = _sample_market_data()
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result())
    use_case = _build_use_case(provider=provider, engine=engine)

    result = use_case.execute("BTC/USDT")

    assert provider.call_count == 1
    assert provider.last_symbol == "BTC/USDT"
    assert result.symbol == "BTC/USDT"


def test_classify_market_skips_provider_when_market_data_supplied() -> None:
    market_data = _sample_market_data("ETH/USDT")
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result("ETH/USDT"))
    use_case = _build_use_case(provider=provider, engine=engine)

    result = use_case.execute("BTC/USDT", market_data=market_data)

    assert provider.call_count == 0
    assert engine.last_market_data is market_data
    assert result.symbol == "ETH/USDT"


def test_classify_market_forwards_portfolio_state_to_engine() -> None:
    market_data = _sample_market_data()
    portfolio_state = PortfolioState(total_value=25_000.0)
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result())
    use_case = _build_use_case(provider=provider, engine=engine)

    use_case.execute("BTC/USDT", portfolio_state=portfolio_state)

    assert engine.last_portfolio_state is portfolio_state


def test_classify_market_passes_classifier_inputs_not_raw_assessments() -> None:
    market_data = _sample_market_data()
    provider = FakeMarketDataProvider(market_data)
    engine = StubMarketAnalysisEngine(_sample_analysis_result())
    regime_classifier = RecordingClassifier()
    risk_classifier = RecordingClassifier()
    economic_classifier = RecordingClassifier()
    exposure_classifier = RecordingClassifier()
    use_case = _build_use_case(
        provider=provider,
        engine=engine,
        regime_classifier=regime_classifier,
        risk_classifier=risk_classifier,
        economic_classifier=economic_classifier,
        exposure_classifier=exposure_classifier,
    )

    use_case.execute("BTC/USDT", market_data=market_data)

    assert isinstance(regime_classifier.last_input, RegimeClassifierInput)
    assert isinstance(risk_classifier.last_input, RiskClassifierInput)
    assert isinstance(economic_classifier.last_input, EconomicClassifierInput)
    assert isinstance(exposure_classifier.last_input, ExposureClassifierInput)
    assert not isinstance(regime_classifier.last_input, RegimeAssessment)
    assert not isinstance(risk_classifier.last_input, RiskAssessment)
    assert not isinstance(economic_classifier.last_input, EconomicAssessment)
    assert not isinstance(exposure_classifier.last_input, ExposureProfile)


def _integration_use_case() -> ClassifyMarket:
    return ClassifyMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
        regime_classifier=RegimeClassifier(),
        risk_classifier=RiskClassifier(),
        economic_classifier=EconomicClassifier(),
        exposure_classifier=ExposureClassifier(),
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
