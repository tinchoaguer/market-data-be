from pydantic import BaseModel


class RegimeAssessmentResponse(BaseModel):
    regime: str
    reasons: list[str]
    insufficient_data: bool = False


class RiskAssessmentResponse(BaseModel):
    score: float
    components: list[tuple[str, float]]
    insufficient_data: bool = False


class EconomicAssessmentResponse(BaseModel):
    edge: float
    components: list[tuple[str, float]]
    insufficient_data: bool = False


class ExposureComponentsResponse(BaseModel):
    vol_budget_pct: float
    liquidity_cap_value: float


class ExposureProfileResponse(BaseModel):
    symbol: str
    total_value: float
    exposure_pct: float
    allocated_value: float
    portfolio_exposure_pct: float
    available_capacity_pct: float
    symbol_weight_cap_pct: float
    recommended_allocation_pct: float
    recommended_allocation_value: float
    components: ExposureComponentsResponse
    insufficient_data: bool = False


class CatalogResultResponse(BaseModel):
    allowed_strategies: list[str]
    forbidden_strategies: list[str]
    preferred_strategy: str
    catalog_reason: str
    hard_gate_reason: str | None = None


class MarketAnalysisResponse(BaseModel):
    symbol: str
    regime: RegimeAssessmentResponse
    risk: RiskAssessmentResponse
    economic: EconomicAssessmentResponse
    exposure: ExposureProfileResponse
    catalog: CatalogResultResponse
