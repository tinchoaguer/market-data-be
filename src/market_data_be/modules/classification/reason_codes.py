"""Domain string constants for classification signal reasons.

Wire values must match the HTTP DTO closed sets character-for-character.
Domain stays free of infrastructure imports.
"""

# Regime
TREND_UP = "trend_up"
TREND_DOWN = "trend_down"
RANGE = "range"
CHAOTIC = "chaotic"
NEWS_SPIKE = "news_spike"

REGIME_REASON_CODES: frozenset[str] = frozenset(
    {TREND_UP, TREND_DOWN, RANGE, CHAOTIC, NEWS_SPIKE}
)

# Risk
LOW_RISK = "low_risk"
MODERATE_RISK = "moderate_risk"
ELEVATED_RISK = "elevated_risk"
HIGH_RISK = "high_risk"

RISK_REASON_CODES: frozenset[str] = frozenset(
    {LOW_RISK, MODERATE_RISK, ELEVATED_RISK, HIGH_RISK}
)

# Economic
STRONG_EDGE = "strong_edge"
MODERATE_EDGE = "moderate_edge"
NEUTRAL_EDGE = "neutral_edge"
NEGATIVE_EDGE = "negative_edge"

ECONOMIC_REASON_CODES: frozenset[str] = frozenset(
    {STRONG_EDGE, MODERATE_EDGE, NEUTRAL_EDGE, NEGATIVE_EDGE}
)

# Exposure
AMPLE_CAPACITY = "ample_capacity"
LIMITED_CAPACITY = "limited_capacity"
CONSTRAINED_CAPACITY = "constrained_capacity"

EXPOSURE_REASON_CODES: frozenset[str] = frozenset(
    {AMPLE_CAPACITY, LIMITED_CAPACITY, CONSTRAINED_CAPACITY}
)
