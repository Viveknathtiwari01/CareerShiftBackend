from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.pipeline import (
    CompetencyMappingOutput,
    PipelineError,
    PipelineMetadata,
)


class AssessmentStartResponse(BaseModel):
    assessment_id: UUID
    pipeline_run_id: UUID
    status: str
    already_running: bool = False


class AssessmentPublicResponse(BaseModel):
    assessment_id: UUID
    status: str
    competency_mapping: CompetencyMappingOutput | None = None
    metadata: PipelineMetadata
    error: PipelineError | None = None


class AssessmentStartResult(BaseModel):
    """Internal service result for starting an assessment."""

    assessment_id: UUID
    pipeline_run_id: UUID
    status: str
    already_running: bool = False
    created_at: datetime | None = None
