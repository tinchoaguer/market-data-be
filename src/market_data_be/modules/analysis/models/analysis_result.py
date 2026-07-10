from dataclasses import dataclass

from .assessments import (
    EconomicAssessment,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)
from .strategy_catalog import CatalogResult


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    symbol: str
    regime: RegimeAssessment
    risk: RiskAssessment
    economic: EconomicAssessment
    exposure: ExposureProfile
    catalog: CatalogResult
