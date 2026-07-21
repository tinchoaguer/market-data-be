"""Domain string constants for analysis catalog narrative MessageRef codes.

Wire values must match the HTTP DTO closed set character-for-character.
Domain stays free of infrastructure imports.
"""

CATALOG_WAIT = "catalog.wait"
CATALOG_STRATEGY_ALLOWED = "catalog.strategy_allowed"
CATALOG_NO_STRATEGY_ALLOWED = "catalog.no_strategy_allowed"
HARD_GATE_EXTREME_REGIME = "catalog.hard_gate.extreme_regime"
HARD_GATE_RISK_TOO_HIGH = "catalog.hard_gate.risk_too_high"
HARD_GATE_NEGATIVE_EDGE = "catalog.hard_gate.negative_edge"
HARD_GATE_NO_CAPACITY = "catalog.hard_gate.no_capacity"

# Short gate tokens used as MessageRef params (never prose).
GATE_EXTREME_REGIME = "extreme_regime"
GATE_RISK_TOO_HIGH = "risk_too_high"
GATE_NEGATIVE_EDGE = "negative_edge"
GATE_NO_CAPACITY = "no_capacity"

NARRATIVE_MESSAGE_CODES: frozenset[str] = frozenset(
    {
        CATALOG_WAIT,
        CATALOG_STRATEGY_ALLOWED,
        CATALOG_NO_STRATEGY_ALLOWED,
        HARD_GATE_EXTREME_REGIME,
        HARD_GATE_RISK_TOO_HIGH,
        HARD_GATE_NEGATIVE_EDGE,
        HARD_GATE_NO_CAPACITY,
    }
)
