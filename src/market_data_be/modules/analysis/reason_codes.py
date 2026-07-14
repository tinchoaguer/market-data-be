"""Domain string constants for analysis regime reasons.

Wire values must match the HTTP DTO closed set character-for-character.
Domain stays free of infrastructure imports.
"""

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

REGIME_REASON_CODES: frozenset[str] = frozenset(
    {
        INSUFFICIENT_CANDLES,
        ADX_LOW_BAND,
        DEFAULT,
        ABNORMAL_RANGE_OR_BODY,
        RELATIVE_VOLUME_SPIKE,
        RELATIVE_TRADES_SPIKE,
        VOLATILITY_EXPANSION,
        LOW_ADX_HIGH_ATR,
        FREQUENT_DIRECTION_CHANGES,
        SMA_WHIPSAW,
        ADX_STRONG,
        PLUS_DI_DOMINANT,
        MINUS_DI_DOMINANT,
        HH_HL_STRUCTURE,
        LH_LL_STRUCTURE,
        ABOVE_SMA_RISING,
        BELOW_SMA_FALLING,
        TAKER_BUY_FLOW,
        TAKER_SELL_FLOW,
    }
)
