from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PortfolioConstraints:
    max_symbol_weight: float = 0.35
    max_portfolio_deployed: float = 0.80
    vol_budget_base: float = 0.15
    vol_budget_min: float = 0.05
    vol_reference: float = 0.01
    liquidity_depth_levels: int = 10
    liquidity_depth_fraction: float = 0.15
    insufficient_data_recommended_pct: float = 0.05


@dataclass(frozen=True, slots=True)
class PortfolioState:
    total_value: float
    allocations: tuple[tuple[str, float], ...] = ()

    def allocated_for(self, symbol: str) -> float:
        for entry_symbol, notional in self.allocations:
            if entry_symbol == symbol:
                return notional
        return 0.0

    @property
    def total_allocated(self) -> float:
        return sum(notional for _, notional in self.allocations)
