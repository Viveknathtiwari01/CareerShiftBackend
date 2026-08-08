from pydantic import BaseModel, Field


class ReportScorecardResponse(BaseModel):
    assessment_id: str
    score: int
    tier_label: str
    job_title: str
    industry: str
    automation_pct: int
    career_risk: str
    headline: str
    linkedin_text: str
    twitter_text: str
    report_url: str


class ReportExportJsonResponse(BaseModel):
    assessment_id: str
    report_version: str
    generated_at: str
    payload: dict = Field(default_factory=dict)
