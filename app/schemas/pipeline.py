from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field


class PipelineMetadata(BaseModel):
    pipeline_run_id: UUID
    pipeline_version: str
    model_name: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_seconds: float | None = None
    engine_metrics: dict[str, float] = Field(default_factory=dict)


class PipelineError(BaseModel):
    message: str
    failed_stage: str | None = None


class CompetencyItem(BaseModel):
    name: str
    category: str
    importance: str | None = None
    expected_level: str | None = None
    what_it_is: str | None = None
    why_it_matters: str | None = None
    professional_context: str | None = None


class CompetencyMappingOutput(BaseModel):
    profession_summary: str | None = None
    competencies: list[CompetencyItem] = Field(default_factory=list)


class AssessmentDebugResponse(BaseModel):
    """Internal/admin response exposing raw stage outputs."""

    assessment_id: UUID
    status: str
    role_understanding: dict[str, Any] | None = None
    competency_discovery: dict[str, Any] | None = None
    competency_structuring: list[dict[str, Any]] | None = None
    competency_validation: dict[str, Any] | None = None
    competency_explanation: dict[str, Any] | None = None
    metadata: PipelineMetadata
    error: PipelineError | None = None
