from dataclasses import dataclass

from .enums import MarketRegime


def frozen_metrics(components: dict[str, float]) -> tuple[tuple[str, float], ...]:
    return tuple(sorted(components.items()))


@dataclass(frozen=True, slots=True)
class RegimeAssessment:
    regime: MarketRegime
    reasons: tuple[str, ...]
    insufficient_data: bool = False


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    score: float
    components: tuple[tuple[str, float], ...]
    insufficient_data: bool = False


@dataclass(frozen=True, slots=True)
class EconomicAssessment:
    edge: float
    components: tuple[tuple[str, float], ...]
    insufficient_data: bool = False


@dataclass(frozen=True, slots=True)
class ExposureComponents:
    vol_budget_pct: float
    liquidity_cap_value: float


@dataclass(frozen=True, slots=True)
class ExposureProfile:
    symbol: str
    total_value: float
    exposure_pct: float
    allocated_value: float
    portfolio_exposure_pct: float
    available_capacity_pct: float
    symbol_weight_cap_pct: float
    recommended_allocation_pct: float
    recommended_allocation_value: float
    components: ExposureComponents
    insufficient_data: bool = False
