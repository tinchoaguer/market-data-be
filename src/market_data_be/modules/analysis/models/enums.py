from enum import Enum


class MarketRegime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"
    CHAOTIC = "CHAOTIC"
    NEWS_SPIKE = "NEWS_SPIKE"


class StrategyType(str, Enum):
    TREND_FOLLOWING = "TREND_FOLLOWING"
    RANGE_BOUNDING = "RANGE_BOUNDING"
    PING_PONG = "PING_PONG"
    NEWS_TRADING = "NEWS_TRADING"
    OTHER = "OTHER"


class Timeframe(str, Enum):
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
