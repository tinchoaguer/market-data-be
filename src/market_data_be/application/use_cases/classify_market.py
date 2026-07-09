from market_data_be.application.contracts.market_data_provider import MarketDataProvider
from market_data_be.application.mappers.assessment_to_classification import (
    to_economic_classifier_input,
    to_exposure_classifier_input,
    to_regime_classifier_input,
    to_risk_classifier_input,
)
from market_data_be.application.models.market_classification import MarketClassification
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.analysis.models.market import MarketData
from market_data_be.modules.analysis.models.portfolio import PortfolioState
from market_data_be.modules.classification.classifiers.economic import EconomicClassifier
from market_data_be.modules.classification.classifiers.exposure import ExposureClassifier
from market_data_be.modules.classification.classifiers.regime import RegimeClassifier
from market_data_be.modules.classification.classifiers.risk import RiskClassifier


class ClassifyMarket:
    def __init__(
        self,
        *,
        provider: MarketDataProvider,
        engine: MarketAnalysisEngine,
        regime_classifier: RegimeClassifier,
        risk_classifier: RiskClassifier,
        economic_classifier: EconomicClassifier,
        exposure_classifier: ExposureClassifier,
    ) -> None:
        self._provider = provider
        self._engine = engine
        self._regime_classifier = regime_classifier
        self._risk_classifier = risk_classifier
        self._economic_classifier = economic_classifier
        self._exposure_classifier = exposure_classifier

    def execute(
        self,
        symbol: str,
        *,
        market_data: MarketData | None = None,
        portfolio_state: PortfolioState | None = None,
    ) -> MarketClassification:
        resolved = (
            market_data if market_data is not None else self._provider.get_market_data(symbol)
        )
        analysis = self._engine.analyze(resolved, portfolio_state)

        regime_signals = self._regime_classifier.classify(
            to_regime_classifier_input(analysis.regime)
        )
        risk_signals = self._risk_classifier.classify(
            to_risk_classifier_input(analysis.risk)
        )
        economic_signals = self._economic_classifier.classify(
            to_economic_classifier_input(analysis.economic)
        )
        exposure_signals = self._exposure_classifier.classify(
            to_exposure_classifier_input(analysis.exposure)
        )

        return MarketClassification(
            symbol=analysis.symbol,
            regime=regime_signals,
            risk=risk_signals,
            economic=economic_signals,
            exposure=exposure_signals,
        )
