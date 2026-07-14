"""Market regime classification from 15m candles (phase 1: single timeframe)."""

from ..models.assessments import RegimeAssessment
from ..models.enums import MarketRegime
from ..models.market import Candle, MarketData
from ..reason_codes import (
    ABNORMAL_RANGE_OR_BODY,
    ABOVE_SMA_RISING,
    ADX_LOW_BAND,
    ADX_STRONG,
    BELOW_SMA_FALLING,
    DEFAULT,
    FREQUENT_DIRECTION_CHANGES,
    HH_HL_STRUCTURE,
    INSUFFICIENT_CANDLES,
    LH_LL_STRUCTURE,
    LOW_ADX_HIGH_ATR,
    MINUS_DI_DOMINANT,
    PLUS_DI_DOMINANT,
    RELATIVE_TRADES_SPIKE,
    RELATIVE_VOLUME_SPIKE,
    SMA_WHIPSAW,
    TAKER_BUY_FLOW,
    TAKER_SELL_FLOW,
    VOLATILITY_EXPANSION,
)
from . import candle_metrics as cm

MIN_KLINES = 30

SPIKE_ATR_RANGE_MULT = 2.5
SPIKE_ATR_BODY_MULT = 1.5
SPIKE_REL_VOLUME = 2.0
SPIKE_REL_TRADES = 2.0
SPIKE_MIN_GROUPS = 2

CHAOTIC_VOL_SHORT_PERIOD = 20
CHAOTIC_VOL_LONG_PERIOD = 50
CHAOTIC_VOL_RATIO = 1.5
CHAOTIC_ADX_MAX = 20.0
CHAOTIC_ATR_SMA_PERIOD = 50
CHAOTIC_DIRECTION_WINDOW = 8
CHAOTIC_MIN_DIRECTION_CHANGES = 5
CHAOTIC_MIN_SMA_CROSSES = 3
CHAOTIC_MIN_CRITERIA = 2

TREND_ADX_PERIOD = 14
TREND_ADX_MIN = 25.0
TREND_STRUCTURE_WINDOW = 10
TREND_SMA_PERIOD = 20
TREND_SMA_LOOKBACK = 5
TREND_TAKER_LAST_N = 3
TREND_TAKER_BULL = 0.52
TREND_TAKER_BEAR = 0.48
TREND_MIN_CRITERIA = 3

RANGE_ADX_MAX = 20.0
RANGE_BAND_ATR_MULT = 1.5


class RegimeDetector:
    def assess(self, market_data: MarketData) -> RegimeAssessment:
        candles = market_data.candles

        if len(candles) < MIN_KLINES:
            return RegimeAssessment(
                regime=MarketRegime.RANGE,
                reasons=(INSUFFICIENT_CANDLES,),
                insufficient_data=True,
            )

        regime, reasons = self._classify(candles)
        return RegimeAssessment(regime=regime, reasons=tuple(reasons))

    def detect(self, market_data: MarketData) -> MarketRegime:
        """Backward-compatible shortcut."""
        return self.assess(market_data).regime

    def _classify(self, candles: tuple[Candle, ...]) -> tuple[MarketRegime, list[str]]:
        spike = self._check_news_spike(candles)
        if spike is not None:
            return spike

        chaotic = self._check_chaotic(candles)
        if chaotic is not None:
            return chaotic

        trend = self._check_trend(candles)
        if trend is not None:
            return trend

        if self._check_range(candles):
            return MarketRegime.RANGE, [ADX_LOW_BAND]

        return MarketRegime.RANGE, [DEFAULT]

    def _check_news_spike(
        self, candles: tuple[Candle, ...]
    ) -> tuple[MarketRegime, list[str]] | None:
        try:
            atr_val = cm.atr(candles, TREND_ADX_PERIOD)
            last = candles[-1]
            prev = candles[-2]

            range_hit = cm.candle_range(last) > SPIKE_ATR_RANGE_MULT * atr_val
            body_hit = abs(float(last.close) - float(last.open)) > SPIKE_ATR_BODY_MULT * atr_val
            range_group = range_hit or body_hit

            vol_hit = cm.relative_volume(candles) > SPIKE_REL_VOLUME
            trades_hit = cm.relative_trades(candles) > SPIKE_REL_TRADES

            prev_range_hit = cm.candle_range(prev) > SPIKE_ATR_RANGE_MULT * atr_val
            prev_body_hit = abs(float(prev.close) - float(prev.open)) > SPIKE_ATR_BODY_MULT * atr_val
            range_group = range_group or prev_range_hit or prev_body_hit

            groups = sum([range_group, vol_hit, trades_hit])
            if groups >= SPIKE_MIN_GROUPS:
                reasons = []
                if range_group:
                    reasons.append(ABNORMAL_RANGE_OR_BODY)
                if vol_hit:
                    reasons.append(RELATIVE_VOLUME_SPIKE)
                if trades_hit:
                    reasons.append(RELATIVE_TRADES_SPIKE)
                return MarketRegime.NEWS_SPIKE, reasons
        except ValueError:
            pass
        return None

    def _check_chaotic(
        self, candles: tuple[Candle, ...]
    ) -> tuple[MarketRegime, list[str]] | None:
        criteria: list[str] = []
        try:
            vol_short = cm.returns_volatility(candles, CHAOTIC_VOL_SHORT_PERIOD)
            vol_long = cm.returns_volatility(candles, CHAOTIC_VOL_LONG_PERIOD)
            if vol_long > 0 and vol_short / vol_long > CHAOTIC_VOL_RATIO:
                criteria.append(VOLATILITY_EXPANSION)

            adx_val, _, _ = cm.wilder_di_adx(candles, TREND_ADX_PERIOD)
            atr_val = cm.atr(candles, TREND_ADX_PERIOD)
            atr_series = cm.atr_series(candles, TREND_ADX_PERIOD)
            if len(atr_series) >= CHAOTIC_ATR_SMA_PERIOD:
                atr_sma = sum(atr_series[-CHAOTIC_ATR_SMA_PERIOD:]) / CHAOTIC_ATR_SMA_PERIOD
                if adx_val < CHAOTIC_ADX_MAX and atr_val > atr_sma:
                    criteria.append(LOW_ADX_HIGH_ATR)

            if cm.direction_changes(candles, CHAOTIC_DIRECTION_WINDOW) >= CHAOTIC_MIN_DIRECTION_CHANGES:
                criteria.append(FREQUENT_DIRECTION_CHANGES)

            if cm.sma_cross_count(candles, TREND_SMA_PERIOD, window=10) >= CHAOTIC_MIN_SMA_CROSSES:
                criteria.append(SMA_WHIPSAW)

            if len(criteria) >= CHAOTIC_MIN_CRITERIA:
                return MarketRegime.CHAOTIC, criteria
        except ValueError:
            pass
        return None

    def _check_trend(
        self, candles: tuple[Candle, ...]
    ) -> tuple[MarketRegime, list[str]] | None:
        try:
            adx_val, plus_di, minus_di = cm.wilder_di_adx(candles, TREND_ADX_PERIOD)
            close = float(candles[-1].close)
            sma_val = cm.sma(candles, TREND_SMA_PERIOD)
            slope = cm.sma_slope(candles, TREND_SMA_PERIOD, TREND_SMA_LOOKBACK)
            taker = cm.taker_buy_ratio(candles, TREND_TAKER_LAST_N)

            up_score = 0
            down_score = 0
            up_reasons: list[str] = []
            down_reasons: list[str] = []

            if adx_val > TREND_ADX_MIN:
                up_score += 1
                down_score += 1
                up_reasons.append(ADX_STRONG)
                down_reasons.append(ADX_STRONG)

            if plus_di > minus_di:
                up_score += 1
                up_reasons.append(PLUS_DI_DOMINANT)
            if minus_di > plus_di:
                down_score += 1
                down_reasons.append(MINUS_DI_DOMINANT)

            if cm.higher_highs_higher_lows(candles, TREND_STRUCTURE_WINDOW):
                up_score += 1
                up_reasons.append(HH_HL_STRUCTURE)
            if cm.lower_highs_lower_lows(candles, TREND_STRUCTURE_WINDOW):
                down_score += 1
                down_reasons.append(LH_LL_STRUCTURE)

            if close > sma_val and slope > 0:
                up_score += 1
                up_reasons.append(ABOVE_SMA_RISING)
            if close < sma_val and slope < 0:
                down_score += 1
                down_reasons.append(BELOW_SMA_FALLING)

            if taker > TREND_TAKER_BULL:
                up_score += 1
                up_reasons.append(TAKER_BUY_FLOW)
            if taker < TREND_TAKER_BEAR:
                down_score += 1
                down_reasons.append(TAKER_SELL_FLOW)

            if up_score >= TREND_MIN_CRITERIA and up_score > down_score:
                return MarketRegime.TREND_UP, up_reasons
            if down_score >= TREND_MIN_CRITERIA and down_score > up_score:
                return MarketRegime.TREND_DOWN, down_reasons
        except ValueError:
            pass
        return None

    def _check_range(self, candles: tuple[Candle, ...]) -> bool:
        try:
            adx_val, _, _ = cm.wilder_di_adx(candles, TREND_ADX_PERIOD)
            if adx_val >= RANGE_ADX_MAX:
                return False
            sma_val = cm.sma(candles, TREND_SMA_PERIOD)
            band = RANGE_BAND_ATR_MULT * cm.atr(candles, TREND_ADX_PERIOD)
            close = float(candles[-1].close)
            return abs(close - sma_val) <= band
        except ValueError:
            return True
