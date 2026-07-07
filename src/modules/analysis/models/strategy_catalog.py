"""Strategy catalog models produced by market analysis synthesis."""

from dataclasses import dataclass

from .enums import StrategyType


@dataclass(frozen=True, slots=True)
class CatalogResult:
    allowed_strategies: tuple[StrategyType, ...]
    forbidden_strategies: tuple[StrategyType, ...]
    preferred_strategy: StrategyType
    catalog_reason: str
    hard_gate_reason: str | None = None

    @property
    def is_hard_gated(self) -> bool:
        return self.hard_gate_reason is not None
