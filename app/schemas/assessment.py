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
    reused_existing: bool = False
    profile_stale: bool = False


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
    needs_pipeline_dispatch: bool = False
    reused_existing: bool = False
    profile_stale: bool = False
    created_at: datetime | None = None


class AssessmentSummaryResponse(BaseModel):
    assessment_id: UUID
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    competency_count: int | None = None


class AssessmentCurrentResponse(BaseModel):
    """Read-only resolution of which assessment session the client should use."""

    assessment_id: UUID | None = None
    pipeline_run_id: UUID | None = None
    status: str | None = None
    needs_sync: bool = True
    profile_stale: bool = False
    reused_existing: bool = False
