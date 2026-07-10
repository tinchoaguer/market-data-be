"""Deterministic strategy catalog built from interpreted market context.

Policy note: gates and strategy eligibility are inlined here on purpose.
Adding a strategy or gate requires editing this module (OCP violation).
Revisit with pluggable CatalogGate / StrategyEligibility if the rule set grows.
"""

from ..models.assessments import (
    EconomicAssessment,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)
from ..models.enums import MarketRegime, StrategyType
from ..models.strategy_catalog import CatalogResult

HIGH_RISK_GATE = 0.75
NEGATIVE_EDGE_GATE = 0.0
MIN_ALLOCATION_VALUE = 1.0

LOW_RISK_MAX = 0.35
MODERATE_RISK_MAX = 0.60
PING_PONG_EDGE_MIN = 0.25


class CatalogBuilder:
    """Turns deterministic assessments into allowed strategy types.

    Intentionally monolithic for now — see module docstring.
    """

    def evaluate(
        self,
        regime: RegimeAssessment,
        risk: RiskAssessment,
        economic: EconomicAssessment,
        exposure: ExposureProfile,
    ) -> CatalogResult:
        hard_gate = self._hard_gate_reason(regime, risk, economic, exposure)
        if hard_gate:
            return CatalogResult(
                allowed_strategies=(),
                forbidden_strategies=tuple(self._all_real_strategies()),
                hard_gate_reason=hard_gate,
                preferred_strategy=StrategyType.OTHER,
                catalog_reason=f"WAIT: {hard_gate}",
            )

        allowed = self._allowed_strategies(regime.regime, risk.score, economic.edge)
        preferred = allowed[0] if allowed else StrategyType.OTHER
        forbidden = [
            strategy for strategy in self._all_real_strategies() if strategy not in allowed
        ]
        return CatalogResult(
            allowed_strategies=tuple(allowed),
            forbidden_strategies=tuple(forbidden),
            hard_gate_reason=None,
            preferred_strategy=preferred,
            catalog_reason=self._catalog_reason(
                regime.regime, risk.score, economic.edge, allowed
            ),
        )

    @staticmethod
    def _all_real_strategies() -> list[StrategyType]:
        return [
            StrategyType.RANGE_BOUNDING,
            StrategyType.TREND_FOLLOWING,
            StrategyType.PING_PONG,
        ]

    @staticmethod
    def _hard_gate_reason(
        regime: RegimeAssessment,
        risk: RiskAssessment,
        economic: EconomicAssessment,
        exposure: ExposureProfile,
    ) -> str | None:
        if regime.regime in {MarketRegime.NEWS_SPIKE, MarketRegime.CHAOTIC}:
            return f"extreme regime: {regime.regime.value}"
        if risk.score >= HIGH_RISK_GATE:
            return f"risk score too high: {risk.score:.2f}"
        if economic.edge < NEGATIVE_EDGE_GATE:
            return f"negative economic edge: {economic.edge:.2f}"
        if exposure.recommended_allocation_value <= MIN_ALLOCATION_VALUE:
            return "no portfolio capacity for a new allocation"
        return None

    @staticmethod
    def _allowed_strategies(
        regime: MarketRegime, risk_score: float, economic_edge: float
    ) -> list[StrategyType]:
        if regime == MarketRegime.RANGE:
            allowed = [StrategyType.RANGE_BOUNDING]
            if risk_score <= LOW_RISK_MAX and economic_edge >= PING_PONG_EDGE_MIN:
                allowed.append(StrategyType.PING_PONG)
            return allowed

        if regime in {MarketRegime.TREND_UP, MarketRegime.TREND_DOWN}:
            if risk_score <= MODERATE_RISK_MAX and economic_edge > 0:
                return [StrategyType.TREND_FOLLOWING]

        return []

    @staticmethod
    def _catalog_reason(
        regime: MarketRegime,
        risk_score: float,
        economic_edge: float,
        allowed: list[StrategyType],
    ) -> str:
        if not allowed:
            return (
                f"No strategy allowed for regime={regime.value}, "
                f"risk={risk_score:.2f}, edge={economic_edge:.2f}"
            )
        strategies = ", ".join(strategy.value for strategy in allowed)
        return (
            f"Allowed {strategies} for regime={regime.value}, "
            f"risk={risk_score:.2f}, edge={economic_edge:.2f}"
        )


__all__ = ["CatalogBuilder", "CatalogResult", "HIGH_RISK_GATE"]
