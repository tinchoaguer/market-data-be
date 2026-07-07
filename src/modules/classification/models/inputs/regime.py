from dataclasses import dataclass
from enum import Enum


class RegimeLabel(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    CHAOTIC = "CHAOTIC"
    NEWS_SPIKE = "NEWS_SPIKE"


@dataclass(frozen=True, slots=True)
class RegimeClassifierInput:
    regime: RegimeLabel
