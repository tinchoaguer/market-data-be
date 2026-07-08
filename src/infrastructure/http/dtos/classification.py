from pydantic import BaseModel


class ClassificationSignalResponse(BaseModel):
    source: str
    score: float
    reason: str


class MarketClassificationResponse(BaseModel):
    symbol: str
    regime: list[ClassificationSignalResponse]
    risk: list[ClassificationSignalResponse]
    economic: list[ClassificationSignalResponse]
    exposure: list[ClassificationSignalResponse]
