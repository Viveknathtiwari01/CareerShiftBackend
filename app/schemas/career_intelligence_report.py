from uuid import UUID

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ai_readiness import AIReadinessResponse
from app.schemas.assessment_task_analysis import TaskAnalysisRunResponse


class ReportKpi(BaseModel):
    label: str
    value: str
    tone: str = "default"


class ReportSnapshotItem(BaseModel):
    label: str
    value: str


class ReportOverviewSection(BaseModel):
    kpis: list[ReportKpi] = Field(default_factory=list)
    career_snapshot: list[ReportSnapshotItem] = Field(default_factory=list)
    insight: str | None = None


class ReportCompetencyItem(BaseModel):
    name: str
    importance: str | None = None
    proficiency: int = Field(ge=0, le=100)
    growth: str


class ReportCompetencyGroup(BaseModel):
    title: str
    category_key: str
    items: list[ReportCompetencyItem] = Field(default_factory=list)


class ReportDailyWorkTask(BaseModel):
    name: str
    hours_per_week: float
    time_label: str
    criticality: str | None = None
    ai_usage: str | None = None
    confidence: str | None = None
    category_3b: str | None = None


class ReportTimeSlice(BaseModel):
    name: str
    value: float
    color: str


class ReportDailyWorkSection(BaseModel):
    tasks: list[ReportDailyWorkTask] = Field(default_factory=list)
    time_allocation: list[ReportTimeSlice] = Field(default_factory=list)
    total_hours: float = 0
    summary: str = ""


class ReportBeforeAfterSection(BaseModel):
    role_today: str
    role_future: str
    hours_freed_per_week: float
    narrative: str
    shifts: list[str] = Field(default_factory=list)


class ReportRoadmapItem(BaseModel):
    title: str
    priority: str
    effort: str
    impact: str


class ReportRoadmapPhase(BaseModel):
    period: str
    items: list[ReportRoadmapItem] = Field(default_factory=list)


class ReportToolkitTool(BaseModel):
    name: str
    description: str
    use_cases: str
    why: str
    efficiency_gain: str


class ReportToolkitCategory(BaseModel):
    title: str
    category_key: str
    tools: list[ReportToolkitTool] = Field(default_factory=list)


class ReportToolkitTaskLink(BaseModel):
    task_title: str
    reason: str


class ReportToolkitItem(BaseModel):
    name: str
    category: str = "Recommended"
    use_case: str
    source: str = "3B Analysis"
    priority_rank: int | None = None
    priority_label: str | None = None
    priority_reason: str | None = None
    task_links: list[ReportToolkitTaskLink] = Field(default_factory=list)


class ReportCostRoiSection(BaseModel):
    annual_salary_estimate: float | None = None
    ld_investment: float
    ai_tools_cost: float
    hours_saved_weekly: float
    payback_months: float | None = None
    roi_summary: str
    breakdown: list[ReportSnapshotItem] = Field(default_factory=list)


class ReportUrgencyBar(BaseModel):
    label: str
    value: int
    tone: str = "default"


class ReportMarketUrgencySection(BaseModel):
    urgency_score: int = Field(ge=0, le=100)
    demand_pct: int
    roles_at_risk_pct: int
    salary_premium_pct: int
    urgency_bars: list[ReportUrgencyBar] = Field(default_factory=list)
    summary: str


class ReportActionItem(BaseModel):
    text: str
    priority: str
    impact: str
    time: str
    difficulty: str


class ReportActionPlanSection(BaseModel):
    start_doing: list[ReportActionItem] = Field(default_factory=list)
    stop_doing: list[ReportActionItem] = Field(default_factory=list)
    automate_with_ai: list[ReportActionItem] = Field(default_factory=list)
    learn_next: list[ReportActionItem] = Field(default_factory=list)


class ReportCareerNode(BaseModel):
    label: str
    role: str


class ReportIdealRole(BaseModel):
    role: str
    reason: str


class ReportCareerIdentitySection(BaseModel):
    title: str
    subtitle: str
    narrative: str
    strengths: list[str] = Field(default_factory=list)
    blind_spots: list[str] = Field(default_factory=list)
    roadmap_nodes: list[ReportCareerNode] = Field(default_factory=list)
    ideal_roles: list[ReportIdealRole] = Field(default_factory=list)
    closing_note: str


class CareerIntelligenceReportResponse(BaseModel):
    assessment_id: UUID
    report_version: str
    generated_at: datetime
    strategic_note: str
    overview: ReportOverviewSection
    ai_readiness: AIReadinessResponse
    task_routing: TaskAnalysisRunResponse
    before_after: ReportBeforeAfterSection
    upskill_roadmap: list[ReportRoadmapPhase]
    ai_toolkit: list[ReportToolkitItem]
    cost_roi: ReportCostRoiSection
    market_urgency: ReportMarketUrgencySection
    action_plan: ReportActionPlanSection
    career_identity: ReportCareerIdentitySection
    competencies: list[ReportCompetencyGroup]
    daily_work: ReportDailyWorkSection
