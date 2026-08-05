from app.services.assessment import AssessmentService
from app.services.competency_pipeline import CompetencyPipeline, CompetencyPipelineEngines


def get_competency_pipeline() -> CompetencyPipeline:
    return CompetencyPipeline(engines=CompetencyPipelineEngines.default())


def get_assessment_service() -> AssessmentService:
    return AssessmentService(competency_pipeline=get_competency_pipeline())
