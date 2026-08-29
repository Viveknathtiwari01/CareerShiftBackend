from datetime import datetime
from uuid import UUID

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


CostBand = Literal["free", "freemium", "paid_individual", "paid_team", "enterprise"]
FeasibilityTier = Literal[
    "self_serve", "company_tech", "org_must_enable", "stays_human_led"
]
VerificationStatus = Literal["UNVERIFIED", "VERIFIED", "REJECTED"]


class ToolOptionSchema(BaseModel):
    name: str = Field(max_length=120)
    cost_band: CostBand = "paid_individual"
    pricing_note: str = Field(default="", max_length=300)
    fit_description: str = Field(default="", max_length=500)
    market_note: str = Field(default="", max_length=500)
    pros: list[str] = Field(default_factory=list, max_length=4)
    cons: list[str] = Field(default_factory=list, max_length=4)
    credibility_note: str = Field(default="", max_length=500)
    feasibility: FeasibilityTier = "self_serve"
    verification_status: VerificationStatus = "UNVERIFIED"
    verified_at: datetime | None = None
    verified_by: str | None = None

    @field_validator("verification_status", mode="before")
    @classmethod
    def force_unverified_on_ingest(cls, value: str | None) -> str:
        return "UNVERIFIED"

    @field_validator("verified_at", "verified_by", mode="before")
    @classmethod
    def force_null_verification_meta(cls, value: Any) -> None:
        return None


class WorkComponentSchema(BaseModel):
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    is_automatable: bool = False
    capability: str = Field(default="", max_length=300)
    solution_pattern: str = Field(default="", max_length=300)
    tools: list[ToolOptionSchema] = Field(default_factory=list, max_length=4)


class CostOfStayingAsIs(BaseModel):
    type: str = "reclaimable_time"
    narrative: str = ""
    annual_hours: float = 0.0


class Task3BAnalysisItem(BaseModel):
    task_index: int
    category: str
    rationale: str | None = None
    reason: str | None = None
    next_actions: list[str] = Field(default_factory=list, max_length=3)
    auto_potential: int | None = None
    risk_level: str | None = None
    future_impact: str | None = None
    components: list[WorkComponentSchema] = Field(default_factory=list, max_length=7)
    importance: str | None = None
    feasibility_tier: str | None = None
    feasibility_note: str | None = None
    human_capability: str | None = None
    velocity: str | None = None
    velocity_note: str | None = None
    next_action: str | None = None
    learn_future: str | None = None
    learn_current: str | None = None
    learn_gap: str | None = None
    learn_do: str | None = None
    learn_dont: str | None = None
    where_to_learn: str | None = None
    status: str | None = None
    cost_of_staying_as_is: CostOfStayingAsIs | None = None


class Task3BAnalysisBatch(BaseModel):
    summary_confidence: int | None = None
    analyses: list[Task3BAnalysisItem] = Field(default_factory=list)


class HoursBucket(BaseModel):
    weekly_hours: float = 0.0
    annual_hours: float = 0.0
    task_count: int = 0


class HoursSummary(BaseModel):
    BUILD: HoursBucket = Field(default_factory=HoursBucket)
    BLEND: HoursBucket = Field(default_factory=HoursBucket)
    BOT: HoursBucket = Field(default_factory=HoursBucket)
    total: HoursBucket = Field(default_factory=HoursBucket)


class HoursByCategory(BaseModel):
    """Legacy flat weekly hours — kept for backward compatibility."""

    BUILD: float = 0.0
    BLEND: float = 0.0
    BOT: float = 0.0


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
    weekly_hours: float = 0.0
    annual_hours: float = 0.0
    importance: str | None = None
    feasibility_tier: str | None = None
    feasibility_note: str | None = None
    human_capability: str | None = None
    velocity: str | None = None
    velocity_note: str | None = None
    next_action: str | None = None
    learn_future: str | None = None
    learn_current: str | None = None
    learn_gap: str | None = None
    learn_do: str | None = None
    learn_dont: str | None = None
    where_to_learn: str | None = None
    status: str | None = None
    cost_of_staying_as_is: CostOfStayingAsIs | None = None
    action_updated_at: datetime | None = None


class TaskAnalysisResponse(BaseModel):
    analyses: list[TaskAnalysisItem]
    summary_confidence: int | None = None
    regenerated: bool = False
    hours_by_category: HoursByCategory = Field(default_factory=HoursByCategory)
    hours_summary: HoursSummary = Field(default_factory=HoursSummary)
    total_hours: float = 0.0
    generated_at: datetime | None = None


class PivotRole(BaseModel):
    name: str
    transfer_strength: str
    reuses: str
    note: str


class MarketReality(BaseModel):
    trend_text: str = ""
    pivot_roles: list[PivotRole] = Field(default_factory=list)

class TaskAnalysisStatusUpdate(BaseModel):
    status: str | None = None

class TaskAnalysisRunResponse(BaseModel):
    analyses: list[TaskAnalysisItem]
    summary_confidence: int | None = None
    regenerated: bool = False
    hours_by_category: HoursByCategory = Field(default_factory=HoursByCategory)
    hours_summary: HoursSummary = Field(default_factory=HoursSummary)
    total_hours: float = 0.0
    generated_at: datetime | None = None
    market_reality: MarketReality | None = None
    recommended_build_task_id: UUID | None = None
