from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskClassifierInput:
    score: float
