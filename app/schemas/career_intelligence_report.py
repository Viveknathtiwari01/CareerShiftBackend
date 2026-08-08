from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReadinessDimension(BaseModel):
    name: str
    score: int


class AIReadinessSection(BaseModel):
    overall_score: int
    tier_label: str
    tier_description: str
    dimensions: list[ReadinessDimension] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    factors: list[dict] = Field(default_factory=list)


class ReportOverview(BaseModel):
    overall_score: int
    tasks_analyzed: int
    competency_count: int
    ai_tools_count: int
    automation_pct: int
    career_risk: str
    job_title: str
    industry: str
    experience_years: int
    profession_summary: str | None = None
    reading_time_minutes: int = 12


class CompetencyGroup(BaseModel):
    category: str
    items: list[dict] = Field(default_factory=list)


class DailyWorkTask(BaseModel):
    title: str
    hours_per_week: float
    category: str | None = None
    complexity: str
    ai_assistance: str | None = None


class TaskRoutingItem(BaseModel):
    task_id: str
    task_title: str
    category: str
    rationale: str | None = None
    reason: str | None = None
    next_actions: list[str] = Field(default_factory=list)
    auto_potential: int | None = None
    risk_level: str | None = None
    recommended_tools: list[str] = Field(default_factory=list)


class CareerIdentitySection(BaseModel):
    identity_title: str
    confidence_pct: int
    executive_summary: str
    ideal_roles: list[str] = Field(default_factory=list)
    superpowers: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    growth_strategy: str


class RoadmapPhase(BaseModel):
    horizon: str
    title: str
    items: list[str] = Field(default_factory=list)


class ToolkitItem(BaseModel):
    name: str
    category: str
    use_case: str
    source: str = "3B Analysis"
    priority_rank: int | None = None
    priority_label: str | None = None
    priority_reason: str | None = None


class ActionPlanSection(BaseModel):
    start: list[str] = Field(default_factory=list)
    stop: list[str] = Field(default_factory=list)
    automate: list[str] = Field(default_factory=list)
    learn: list[str] = Field(default_factory=list)


class CareerIntelligenceReportResponse(BaseModel):
    assessment_id: UUID
    report_version: str
    generated_at: datetime
    strategic_note: str | None = None
    overview: ReportOverview
    ai_readiness: AIReadinessSection
    competencies: list[CompetencyGroup]
    daily_work: dict
    task_routing: list[TaskRoutingItem]
    career_identity: CareerIdentitySection
    learning_roadmap: list[RoadmapPhase]
    ai_toolkit: list[ToolkitItem]
    action_plan: ActionPlanSection
    before_after: dict = Field(default_factory=dict)
    cost_roi: dict = Field(default_factory=dict)
    market_urgency: dict = Field(default_factory=dict)
