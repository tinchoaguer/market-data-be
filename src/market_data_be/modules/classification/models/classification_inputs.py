from dataclasses import dataclass

from .inputs.economic import EconomicClassifierInput
from .inputs.exposure import ExposureClassifierInput
from .inputs.regime import RegimeClassifierInput
from .inputs.risk import RiskClassifierInput


@dataclass(frozen=True, slots=True)
class ClassificationInputs:
    symbol: str
    regime: RegimeClassifierInput
    risk: RiskClassifierInput
    economic: EconomicClassifierInput
    exposure: ExposureClassifierInput
