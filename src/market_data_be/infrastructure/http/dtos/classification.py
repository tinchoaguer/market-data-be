from enum import StrEnum

from pydantic import BaseModel


class RegimeReasonCode(StrEnum):
    TREND_UP = "trend_up"
    TREND_DOWN = "trend_down"
    RANGE = "range"
    CHAOTIC = "chaotic"
    NEWS_SPIKE = "news_spike"


class RiskReasonCode(StrEnum):
    LOW_RISK = "low_risk"
    MODERATE_RISK = "moderate_risk"
    ELEVATED_RISK = "elevated_risk"
    HIGH_RISK = "high_risk"


class EconomicReasonCode(StrEnum):
    STRONG_EDGE = "strong_edge"
    MODERATE_EDGE = "moderate_edge"
    NEUTRAL_EDGE = "neutral_edge"
    NEGATIVE_EDGE = "negative_edge"


class ExposureReasonCode(StrEnum):
    AMPLE_CAPACITY = "ample_capacity"
    LIMITED_CAPACITY = "limited_capacity"
    CONSTRAINED_CAPACITY = "constrained_capacity"


class RegimeSignalResponse(BaseModel):
    source: str
    score: float
    reason: RegimeReasonCode


class RiskSignalResponse(BaseModel):
    source: str
    score: float
    reason: RiskReasonCode


class EconomicSignalResponse(BaseModel):
    source: str
    score: float
    reason: EconomicReasonCode


class ExposureSignalResponse(BaseModel):
    source: str
    score: float
    reason: ExposureReasonCode


class MarketClassificationResponse(BaseModel):
    symbol: str
    regime: list[RegimeSignalResponse]
    risk: list[RiskSignalResponse]
    economic: list[EconomicSignalResponse]
    exposure: list[ExposureSignalResponse]
