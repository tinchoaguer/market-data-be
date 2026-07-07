"""Multi-factor risk scoring from candles, order book and detected regime."""

from ..models.assessments import RegimeAssessment, RiskAssessment, frozen_metrics
from ..models.enums import MarketRegime
from ..models.market import MarketData
from . import candle_metrics as cm

MIN_KLINES = 30

VOL_PERIOD = 20
VOL_SCALE = 50.0

ATR_PERIOD = 14
ATR_SMA_PERIOD = 50
ATR_EXPANSION_DENOM = 1.0

REGIME_RISK: dict[MarketRegime, float] = {
    MarketRegime.NEWS_SPIKE: 0.95,
    MarketRegime.CHAOTIC: 0.75,
    MarketRegime.TREND_UP: 0.45,
    MarketRegime.TREND_DOWN: 0.45,
    MarketRegime.RANGE: 0.25,
}

REGIME_FLOORS: dict[MarketRegime, float] = {
    MarketRegime.NEWS_SPIKE: 0.75,
    MarketRegime.CHAOTIC: 0.55,
}

REL_VOLUME_STRESS_START = 1.0
REL_VOLUME_STRESS_DENOM = 2.0
IMBALANCE_WEIGHT = 0.5
VOLUME_STRESS_WEIGHT = 0.5

W_VOLATILITY = 0.30
W_ATR_EXPANSION = 0.20
W_REGIME = 0.30
W_LIQUIDITY = 0.20

INSUFFICIENT_DATA_SCORE = 0.5


class RiskEngine:
    def assess(self, market_data: MarketData, regime: RegimeAssessment) -> RiskAssessment:
        candles = market_data.candles

        if len(candles) < MIN_KLINES:
            return RiskAssessment(
                score=INSUFFICIENT_DATA_SCORE,
                components=(),
                insufficient_data=True,
            )

        components = self._compute_components(market_data, regime.regime)
        score = min(
            1.0,
            W_VOLATILITY * components["volatility"]
            + W_ATR_EXPANSION * components["atr_expansion"]
            + W_REGIME * components["regime"]
            + W_LIQUIDITY * components["liquidity_stress"],
        )
        floor = REGIME_FLOORS.get(regime.regime)
        if floor is not None:
            score = max(score, floor)

        return RiskAssessment(score=score, components=frozen_metrics(components))

    def score(self, market_data: MarketData, regime: MarketRegime) -> float:
        """Backward-compatible shortcut."""
        assessment = self.assess(
            market_data,
            RegimeAssessment(regime=regime, reasons=()),
        )
        return assessment.score

    def _compute_components(
        self, market_data: MarketData, regime: MarketRegime
    ) -> dict[str, float]:
        candles = market_data.candles
        return {
            "volatility": self._volatility_component(candles),
            "atr_expansion": self._atr_expansion_component(candles),
            "regime": REGIME_RISK.get(regime, 0.5),
            "liquidity_stress": self._liquidity_stress_component(market_data),
        }

    @staticmethod
    def _volatility_component(candles) -> float:
        try:
            vol = cm.returns_volatility(candles, VOL_PERIOD)
        except ValueError:
            return 0.0
        return min(1.0, vol * VOL_SCALE)

    @staticmethod
    def _atr_expansion_component(candles) -> float:
        try:
            atr_val = cm.atr(candles, ATR_PERIOD)
            series = cm.atr_series(candles, ATR_PERIOD)
            if len(series) < ATR_SMA_PERIOD:
                return 0.0
            atr_sma = sum(series[-ATR_SMA_PERIOD:]) / ATR_SMA_PERIOD
            if atr_sma == 0:
                return 0.0
            expansion = max(0.0, atr_val / atr_sma - 1.0)
            return min(1.0, expansion / ATR_EXPANSION_DENOM)
        except ValueError:
            return 0.0

    @staticmethod
    def _liquidity_stress_component(market_data: MarketData) -> float:
        imbalance = abs(cm.order_book_imbalance(market_data.order_book))
        try:
            rel_vol = cm.relative_volume(market_data.candles)
            vol_stress = max(0.0, rel_vol - REL_VOLUME_STRESS_START) / REL_VOLUME_STRESS_DENOM
            vol_stress = min(1.0, vol_stress)
        except ValueError:
            vol_stress = 0.0
        return min(1.0, IMBALANCE_WEIGHT * imbalance + VOLUME_STRESS_WEIGHT * vol_stress)
