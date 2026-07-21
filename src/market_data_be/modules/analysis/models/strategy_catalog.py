"""Strategy catalog models produced by market analysis synthesis."""

from dataclasses import dataclass

from .enums import StrategyType
from .message_ref import MessageRef


@dataclass(frozen=True, slots=True)
class CatalogResult:
    allowed_strategies: tuple[StrategyType, ...]
    forbidden_strategies: tuple[StrategyType, ...]
    preferred_strategy: StrategyType
    catalog_reason: MessageRef
    hard_gate_reason: MessageRef | None = None

    @property
    def is_hard_gated(self) -> bool:
        return self.hard_gate_reason is not None
