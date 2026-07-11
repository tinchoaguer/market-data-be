from market_data_be.application.use_cases.analyze_market import AnalyzeMarket
from market_data_be.application.use_cases.classify_market import ClassifyMarket
from market_data_be.application.use_cases.get_market_data import GetMarketData
from market_data_be.infrastructure.market_data.mock_provider import MockMarketDataProvider
from market_data_be.modules.analysis.market_analysis_engine import MarketAnalysisEngine
from market_data_be.modules.classification.market_classification_engine import (
    MarketClassificationEngine,
)


def build_classify_market() -> ClassifyMarket:
    return ClassifyMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
        classification_engine=MarketClassificationEngine(),
    )


def build_get_market_data() -> GetMarketData:
    return GetMarketData(
        provider=MockMarketDataProvider(),
    )


def build_analyze_market() -> AnalyzeMarket:
    return AnalyzeMarket(
        provider=MockMarketDataProvider(),
        engine=MarketAnalysisEngine(),
    )
