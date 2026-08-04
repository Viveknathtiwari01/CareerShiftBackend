from enum import Enum


class PipelineStage(str, Enum):
    ROLE_UNDERSTANDING = "role_understanding"
    COMPETENCY_DISCOVERY = "competency_discovery"
    COMPETENCY_STRUCTURING = "competency_structuring"
    COMPETENCY_VALIDATION = "competency_validation"
    COMPETENCY_EXPLANATION = "competency_explanation"


COMPETENCY_PIPELINE_STAGES: tuple[PipelineStage, ...] = (
    PipelineStage.ROLE_UNDERSTANDING,
    PipelineStage.COMPETENCY_DISCOVERY,
    PipelineStage.COMPETENCY_STRUCTURING,
    PipelineStage.COMPETENCY_VALIDATION,
    PipelineStage.COMPETENCY_EXPLANATION,
)

STAGE_JSON_COLUMNS: dict[PipelineStage, str] = {
    PipelineStage.ROLE_UNDERSTANDING: "role_understanding_json",
    PipelineStage.COMPETENCY_DISCOVERY: "competency_discovery_json",
    PipelineStage.COMPETENCY_STRUCTURING: "competency_structuring_json",
    PipelineStage.COMPETENCY_VALIDATION: "competency_validation_json",
    PipelineStage.COMPETENCY_EXPLANATION: "competency_explanation_json",
}
