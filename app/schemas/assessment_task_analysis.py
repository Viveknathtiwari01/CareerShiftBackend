from uuid import UUID

from pydantic import BaseModel, Field


class TaskAnalysisItem(BaseModel):
    task_id: UUID
    task_title: str
    task_description: str | None = None
    task_category: str | None = None
    category: str
    rationale: str | None = None
    reason: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    auto_potential: int | None = None
    risk_level: str | None = None
    future_impact: str | None = None
    recommended_tools: list[str] = Field(default_factory=list)


class TaskAnalysisResponse(BaseModel):
    analyses: list[TaskAnalysisItem]
    summary_confidence: int | None = None
    regenerated: bool = False


class TaskAnalysisRunResponse(BaseModel):
    analyses: list[TaskAnalysisItem]
    summary_confidence: int | None = None
    regenerated: bool = False
