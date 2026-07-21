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
from ..models.message_ref import MessageRef
from ..models.strategy_catalog import CatalogResult
from ..narrative_codes import (
    CATALOG_NO_STRATEGY_ALLOWED,
    CATALOG_STRATEGY_ALLOWED,
    CATALOG_WAIT,
    GATE_EXTREME_REGIME,
    GATE_NEGATIVE_EDGE,
    GATE_NO_CAPACITY,
    GATE_RISK_TOO_HIGH,
    HARD_GATE_EXTREME_REGIME,
    HARD_GATE_NEGATIVE_EDGE,
    HARD_GATE_NO_CAPACITY,
    HARD_GATE_RISK_TOO_HIGH,
)

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
                catalog_reason=self._wait_reason(hard_gate),
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
    ) -> MessageRef | None:
        if regime.regime in {MarketRegime.NEWS_SPIKE, MarketRegime.CHAOTIC}:
            return MessageRef.of(
                HARD_GATE_EXTREME_REGIME,
                regime=regime.regime.value,
            )
        if risk.score >= HIGH_RISK_GATE:
            return MessageRef.of(
                HARD_GATE_RISK_TOO_HIGH,
                risk_score=risk.score,
            )
        if economic.edge < NEGATIVE_EDGE_GATE:
            return MessageRef.of(
                HARD_GATE_NEGATIVE_EDGE,
                edge=economic.edge,
            )
        if exposure.recommended_allocation_value <= MIN_ALLOCATION_VALUE:
            return MessageRef.of(HARD_GATE_NO_CAPACITY)
        return None

    @staticmethod
    def _wait_reason(hard_gate: MessageRef) -> MessageRef:
        gate_token = {
            HARD_GATE_EXTREME_REGIME: GATE_EXTREME_REGIME,
            HARD_GATE_RISK_TOO_HIGH: GATE_RISK_TOO_HIGH,
            HARD_GATE_NEGATIVE_EDGE: GATE_NEGATIVE_EDGE,
            HARD_GATE_NO_CAPACITY: GATE_NO_CAPACITY,
        }[hard_gate.code]
        return MessageRef(
            code=CATALOG_WAIT,
            params=(("gate", gate_token), *hard_gate.params),
        )

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
    ) -> MessageRef:
        if not allowed:
            return MessageRef.of(
                CATALOG_NO_STRATEGY_ALLOWED,
                regime=regime.value,
                risk_score=risk_score,
                edge=economic_edge,
            )
        return MessageRef.of(
            CATALOG_STRATEGY_ALLOWED,
            strategy=allowed[0].value,
            regime=regime.value,
            risk_score=risk_score,
            edge=economic_edge,
        )


__all__ = ["CatalogBuilder", "CatalogResult", "HIGH_RISK_GATE"]
