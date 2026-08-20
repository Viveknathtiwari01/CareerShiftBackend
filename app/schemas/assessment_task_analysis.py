from uuid import UUID

from typing import Any

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
    components: list[dict[str, Any]] = Field(default_factory=list)

class HoursByCategory(BaseModel):
    BUILD: float = 0.0
    BLEND: float = 0.0
    BOT: float = 0.0


class TaskAnalysisResponse(BaseModel):
    analyses: list[TaskAnalysisItem]
    summary_confidence: int | None = None
    regenerated: bool = False
    hours_by_category: HoursByCategory = Field(default_factory=HoursByCategory)
    total_hours: float = 0.0


class TaskAnalysisRunResponse(BaseModel):
    analyses: list[TaskAnalysisItem]
    summary_confidence: int | None = None
    regenerated: bool = False
    hours_by_category: HoursByCategory = Field(default_factory=HoursByCategory)
    total_hours: float = 0.0
