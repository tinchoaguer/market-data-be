from enum import StrEnum

from pydantic import BaseModel, Field


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


MessageParamValue = str | int | float | bool


class RegimeSignalMessageRef(BaseModel):
    code: RegimeReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class RiskSignalMessageRef(BaseModel):
    code: RiskReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class EconomicSignalMessageRef(BaseModel):
    code: EconomicReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class ExposureSignalMessageRef(BaseModel):
    code: ExposureReasonCode
    params: dict[str, MessageParamValue] = Field(default_factory=dict)


class RegimeSignalResponse(BaseModel):
    source: str
    score: float
    reason: RegimeSignalMessageRef


class RiskSignalResponse(BaseModel):
    source: str
    score: float
    reason: RiskSignalMessageRef


class EconomicSignalResponse(BaseModel):
    source: str
    score: float
    reason: EconomicSignalMessageRef


class ExposureSignalResponse(BaseModel):
    source: str
    score: float
    reason: ExposureSignalMessageRef


class MarketClassificationResponse(BaseModel):
    symbol: str
    regime: list[RegimeSignalResponse]
    risk: list[RiskSignalResponse]
    economic: list[EconomicSignalResponse]
    exposure: list[ExposureSignalResponse]


class ClassificationErrorCode(StrEnum):
    INVALID_SYMBOL_FORMAT = "classification.invalid_symbol_format"
    UNDECLARED_REASON = "classification.undeclared_reason"
    INVALID_MESSAGE_PARAMS = "classification.invalid_message_params"


class ClassificationErrorDetail(BaseModel):
    code: ClassificationErrorCode
    message: str
