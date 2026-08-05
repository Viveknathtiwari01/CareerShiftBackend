from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SuggestedTaskItem(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    hours_per_week: float = Field(default=0, ge=0, le=80)
    complexity: str = "medium"
    creativity: str = "medium"
    human_touch: str = "medium"
    confidence: int | None = Field(default=None, ge=0, le=100)


class AssessmentTaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    category: str | None = None
    hours_per_week: float
    complexity: str
    creativity: str
    human_touch: str
    confidence: int | None = None
    selected: bool
    source: str
    sort_order: int
    frequency: str | None = None
    business_criticality: str | None = None
    time_allocation: float | None = None
    ai_assistance: str | None = None
    confidence_score: int | None = None
    manual_notes: str | None = None

    model_config = {"from_attributes": True}


class AssessmentTaskUpsertItem(BaseModel):
    id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: str | None = None
    hours_per_week: float = Field(default=0, ge=0, le=80)
    complexity: str = "medium"
    creativity: str = "medium"
    human_touch: str = "medium"
    confidence: int | None = Field(default=None, ge=0, le=100)
    selected: bool = True
    source: str = "USER"
    sort_order: int = 0
    frequency: str | None = None
    business_criticality: str | None = None
    time_allocation: float | None = None
    ai_assistance: str | None = None
    confidence_score: int | None = Field(default=None, ge=1, le=10)
    manual_notes: str | None = None

    @field_validator("complexity", "creativity", "human_touch")
    @classmethod
    def validate_level(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"low", "medium", "high"}:
            raise ValueError("Must be low, medium, or high")
        return normalized


class AssessmentTasksBulkUpsert(BaseModel):
    tasks: list[AssessmentTaskUpsertItem] = Field(min_length=1)


class TaskGenerationResponse(BaseModel):
    tasks: list[AssessmentTaskResponse]
    suggested_additional: list[SuggestedTaskItem] = Field(default_factory=list)
    regenerated: bool = False
