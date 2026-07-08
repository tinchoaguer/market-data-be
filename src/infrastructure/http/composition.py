from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.classification.classifiers.economic import EconomicClassifier
from market_data_be.modules.classification.classifiers.exposure import ExposureClassifier
from market_data_be.modules.classification.classifiers.regime import RegimeClassifier
from market_data_be.modules.classification.classifiers.risk import RiskClassifier


def build_classify_market() -> ClassifyMarket:
    return ClassifyMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
        regime_classifier=RegimeClassifier(),
        risk_classifier=RiskClassifier(),
        economic_classifier=EconomicClassifier(),
        exposure_classifier=ExposureClassifier(),
    )
