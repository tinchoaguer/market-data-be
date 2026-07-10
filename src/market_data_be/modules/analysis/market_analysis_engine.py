"""Single entry point for deterministic market analysis."""

from .analyzers.economic_filter import EconomicFilter
from .analyzers.portfolio_manager import DEFAULT_TOTAL_VALUE, PortfolioManager
from .analyzers.regime_detector import RegimeDetector
from .analyzers.risk_engine import RiskEngine
from .models.analysis_result import AnalysisResult
from .models.market import MarketData
from .models.portfolio import PortfolioConstraints, PortfolioState
from .synthesis.catalog_builder import CatalogBuilder


class MarketAnalysisEngine:
    def __init__(
        self,
        *,
        constraints: PortfolioConstraints | None = None,
        regime_detector: RegimeDetector | None = None,
        risk_engine: RiskEngine | None = None,
        economic_filter: EconomicFilter | None = None,
        portfolio_manager: PortfolioManager | None = None,
        catalog_builder: CatalogBuilder | None = None,
    ):
        self._constraints = constraints
        self._regime_detector = regime_detector or RegimeDetector()
        self._risk_engine = risk_engine or RiskEngine()
        self._economic_filter = economic_filter or EconomicFilter()
        self._portfolio_manager = portfolio_manager or PortfolioManager()
        self._catalog_builder = catalog_builder or CatalogBuilder()

    def analyze(
        self,
        market_data: MarketData,
        portfolio_state: PortfolioState | None = None,
    ) -> AnalysisResult:
        state = portfolio_state or PortfolioState(total_value=DEFAULT_TOTAL_VALUE)

        regime = self._regime_detector.assess(market_data)
        risk = self._risk_engine.assess(market_data, regime)
        economic = self._economic_filter.assess(market_data)
        exposure = self._portfolio_manager.evaluate(market_data, state, self._constraints)
        catalog = self._catalog_builder.evaluate(regime, risk, economic, exposure)

        return AnalysisResult(
            symbol=market_data.symbol,
            regime=regime,
            risk=risk,
            economic=economic,
            exposure=exposure,
            catalog=catalog,
        )
