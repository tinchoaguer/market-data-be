from market_data_be.modules.analysis.models.analysis_result import AnalysisResult
from market_data_be.modules.analysis.models.assessments import (
    EconomicAssessment,
    ExposureProfile,
    RegimeAssessment,
    RiskAssessment,
)
from market_data_be.modules.classification.models.classification_inputs import (
    ClassificationInputs,
)
from market_data_be.modules.classification.models.inputs.economic import (
    EconomicClassifierInput,
)
from market_data_be.modules.classification.models.inputs.exposure import (
    ExposureClassifierInput,
)
from market_data_be.modules.classification.models.inputs.regime import (
    RegimeClassifierInput,
    RegimeLabel,
)
from market_data_be.modules.classification.models.inputs.risk import RiskClassifierInput


def to_regime_classifier_input(assessment: RegimeAssessment) -> RegimeClassifierInput:
    return RegimeClassifierInput(regime=RegimeLabel(assessment.regime.value))


def to_risk_classifier_input(assessment: RiskAssessment) -> RiskClassifierInput:
    return RiskClassifierInput(score=assessment.score)


def to_economic_classifier_input(assessment: EconomicAssessment) -> EconomicClassifierInput:
    return EconomicClassifierInput(edge=assessment.edge)


def to_exposure_classifier_input(profile: ExposureProfile) -> ExposureClassifierInput:
    return ExposureClassifierInput(available_capacity_pct=profile.available_capacity_pct)


def to_classification_inputs(analysis: AnalysisResult) -> ClassificationInputs:
    return ClassificationInputs(
        symbol=analysis.symbol,
        regime=to_regime_classifier_input(analysis.regime),
        risk=to_risk_classifier_input(analysis.risk),
        economic=to_economic_classifier_input(analysis.economic),
        exposure=to_exposure_classifier_input(analysis.exposure),
    )
