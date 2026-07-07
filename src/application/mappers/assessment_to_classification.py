from market_data_be.application.models.assessment import Assessment
from market_data_be.application.models.classification import Classification
from market_data_be.application.models.classification.inputs import (
    EconomicClassifierInput,
    ExposureClassifierInput,
    RegimeClassifierInput,
    RegimeLabel,
    RiskClassifierInput,
)
from market_data_be.application.models.assessment import (
    EconomicAssessment,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)


def to_regime_classifier_input(assessment: RegimeAssessment) -> RegimeClassifierInput:
    return RegimeClassifierInput(regime=RegimeLabel(assessment.regime.value))


def to_risk_classifier_input(assessment: RiskAssessment) -> RiskClassifierInput:
    return RiskClassifierInput(score=assessment.score)


def to_economic_classifier_input(assessment: EconomicAssessment) -> EconomicClassifierInput:
    return EconomicClassifierInput(edge=assessment.edge)


def to_exposure_classifier_input(profile: ExposureProfile) -> ExposureClassifierInput:
    return ExposureClassifierInput(available_capacity_pct=profile.available_capacity_pct)
