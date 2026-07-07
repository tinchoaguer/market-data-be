"""Economic viability scoring from microstructure, activity, range economics and costs."""

from ..models.assessments import EconomicAssessment, frozen_metrics
from ..models.market import MarketData
from . import candle_metrics as cm

MIN_KLINES = 30

REL_VOLUME_CAP = 1.5

ACTIVITY_VOL_PERIOD = 20
ACTIVITY_IDEAL_REL_VOL = 1.2
ACTIVITY_PEAK_SCORE = 1.0
ACTIVITY_THIN_THRESHOLD = 0.5
ACTIVITY_SPIKE_START = 1.5
ACTIVITY_SPIKE_DENOM = 2.0

ATR_PERIOD = 14
ATR_PCT_DEAD = 0.05
ATR_PCT_LOW = 0.15
ATR_PCT_IDEAL = 0.40
ATR_PCT_HIGH = 1.0
ATR_PCT_EXTREME = 2.5

TAKER_FEE = 0.001
MAKER_FEE = 0.0008
EST_GRID_FILLS = 8
MAX_ACCEPTABLE_COST_PCT = 0.02

W_MICROSTRUCTURE = 0.25
W_ACTIVITY = 0.25
W_RANGE_ECONOMICS = 0.30
W_COST = 0.20

INSUFFICIENT_DATA_EDGE = 0.0


class EconomicFilter:
    def assess(self, market_data: MarketData) -> EconomicAssessment:
        candles = market_data.candles

        if len(candles) < MIN_KLINES:
            return EconomicAssessment(
                edge=INSUFFICIENT_DATA_EDGE,
                components=(),
                insufficient_data=True,
            )

        components = self._compute_components(market_data)
        edge = max(
            -1.0,
            min(
                1.0,
                W_MICROSTRUCTURE * components["microstructure"]
                + W_ACTIVITY * components["activity"]
                + W_RANGE_ECONOMICS * components["range_economics"]
                - W_COST * components["cost_drag"],
            ),
        )
        return EconomicAssessment(edge=edge, components=frozen_metrics(components))

    def _compute_components(self, market_data: MarketData) -> dict[str, float]:
        candles = market_data.candles
        rel_vol = self._safe_relative_volume(candles)
        imbalance = cm.order_book_imbalance(market_data.order_book)

        return {
            "microstructure": self._microstructure_component(imbalance, rel_vol),
            "activity": self._activity_component(rel_vol),
            "range_economics": self._range_economics_component(candles),
            "cost_drag": self._cost_drag_component(market_data.order_book),
        }

    @staticmethod
    def _safe_relative_volume(candles) -> float:
        try:
            return cm.relative_volume(candles, ACTIVITY_VOL_PERIOD)
        except ValueError:
            return 0.0

    @staticmethod
    def _microstructure_component(imbalance: float, rel_vol: float) -> float:
        weight = min(1.0, rel_vol / REL_VOLUME_CAP)
        return max(-1.0, min(1.0, imbalance * weight))

    @staticmethod
    def _activity_component(rel_vol: float) -> float:
        if rel_vol < ACTIVITY_THIN_THRESHOLD:
            return rel_vol / ACTIVITY_THIN_THRESHOLD * 0.5
        if rel_vol <= ACTIVITY_SPIKE_START:
            deviation = abs(rel_vol - ACTIVITY_IDEAL_REL_VOL) / 0.8
            return max(0.5, ACTIVITY_PEAK_SCORE - deviation * 0.5)
        spike_penalty = (rel_vol - ACTIVITY_SPIKE_START) / ACTIVITY_SPIKE_DENOM
        return max(0.0, ACTIVITY_PEAK_SCORE * 0.5 - spike_penalty)

    @staticmethod
    def _range_economics_component(candles) -> float:
        try:
            atr_val = cm.atr(candles, ATR_PERIOD)
            close = cm.latest_close(candles)
        except ValueError:
            return 0.0
        if close <= 0:
            return 0.0

        atr_pct = atr_val / close * 100

        if atr_pct < ATR_PCT_DEAD:
            return 0.2
        if atr_pct < ATR_PCT_LOW:
            return 0.4 + (atr_pct - ATR_PCT_DEAD) / (ATR_PCT_LOW - ATR_PCT_DEAD) * 0.4
        if atr_pct <= ATR_PCT_HIGH:
            deviation = abs(atr_pct - ATR_PCT_IDEAL) / (ATR_PCT_HIGH - ATR_PCT_LOW)
            return max(0.5, 1.0 - deviation * 0.3)
        if atr_pct <= ATR_PCT_EXTREME:
            return max(0.1, 0.7 - (atr_pct - ATR_PCT_HIGH) / (ATR_PCT_EXTREME - ATR_PCT_HIGH) * 0.6)
        return 0.1

    @staticmethod
    def _cost_drag_component(order_book) -> float:
        spread = cm.spread_bps(order_book) / 10_000
        round_trip_fees = TAKER_FEE + MAKER_FEE
        est_cost = round_trip_fees + spread * EST_GRID_FILLS
        return min(1.0, est_cost / MAX_ACCEPTABLE_COST_PCT)
