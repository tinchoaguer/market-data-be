from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExposureClassifierInput:
    available_capacity_pct: float
