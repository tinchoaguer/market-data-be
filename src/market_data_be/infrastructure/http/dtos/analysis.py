from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class AnalysisRegimeLabel(StrEnum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    CHAOTIC = "CHAOTIC"
    NEWS_SPIKE = "NEWS_SPIKE"


class AnalysisRegimeReasonCode(StrEnum):
    INSUFFICIENT_CANDLES = "insufficient_candles"
    ADX_LOW_BAND = "adx_low_band"
    DEFAULT = "default"
    ABNORMAL_RANGE_OR_BODY = "abnormal_range_or_body"
    RELATIVE_VOLUME_SPIKE = "relative_volume_spike"
    RELATIVE_TRADES_SPIKE = "relative_trades_spike"
    VOLATILITY_EXPANSION = "volatility_expansion"
    LOW_ADX_HIGH_ATR = "low_adx_high_atr"
    FREQUENT_DIRECTION_CHANGES = "frequent_direction_changes"
    SMA_WHIPSAW = "sma_whipsaw"
    ADX_STRONG = "adx_strong"
    PLUS_DI_DOMINANT = "plus_di_dominant"
    MINUS_DI_DOMINANT = "minus_di_dominant"
    HH_HL_STRUCTURE = "hh_hl_structure"
    LH_LL_STRUCTURE = "lh_ll_structure"
    ABOVE_SMA_RISING = "above_sma_rising"
    BELOW_SMA_FALLING = "below_sma_falling"
    TAKER_BUY_FLOW = "taker_buy_flow"
    TAKER_SELL_FLOW = "taker_sell_flow"


class AnalysisNarrativeMessageCode(StrEnum):
    CATALOG_WAIT = "catalog.wait"
    CATALOG_STRATEGY_ALLOWED = "catalog.strategy_allowed"
    CATALOG_NO_STRATEGY_ALLOWED = "catalog.no_strategy_allowed"
    HARD_GATE_EXTREME_REGIME = "catalog.hard_gate.extreme_regime"
    HARD_GATE_RISK_TOO_HIGH = "catalog.hard_gate.risk_too_high"
    HARD_GATE_NEGATIVE_EDGE = "catalog.hard_gate.negative_edge"
    HARD_GATE_NO_CAPACITY = "catalog.hard_gate.no_capacity"


MessageParamValue = str | int | float | bool


class MessageRefResponse(BaseModel):
    code: AnalysisNarrativeMessageCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)
    severity: Literal["info", "warning", "error"] | None = None
    channel: Literal["ui", "email", "push", "sms", "log"] | None = None


class RegimeAssessmentResponse(BaseModel):
    regime: AnalysisRegimeLabel
    reasons: list[AnalysisRegimeReasonCode]
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
    catalog_reason: MessageRefResponse
    hard_gate_reason: MessageRefResponse | None = None


class MarketAnalysisResponse(BaseModel):
    symbol: str
    regime: RegimeAssessmentResponse
    risk: RiskAssessmentResponse
    economic: EconomicAssessmentResponse
    exposure: ExposureProfileResponse
    catalog: CatalogResultResponse
