from pydantic import BaseModel, Field


class ReadinessFactor(BaseModel):
    key: str
    label: str
    score: int = Field(ge=0, le=100)
    weight: float
    contribution: float
    summary: str


class ReadinessDimension(BaseModel):
    subject: str
    score: int = Field(ge=0, le=100)


class ReadinessStrength(BaseModel):
    title: str
    detail: str | None = None


class ReadinessImprovement(BaseModel):
    title: str
    difficulty: str = "Medium"
    impact: str = "High"


class ReadinessToolRecommendation(BaseModel):
    name: str
    fit: str
    use_case: str


class AIReadinessResponse(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    tier: str
    tier_label: str
    summary: str
    factors: list[ReadinessFactor]
    dimensions: list[ReadinessDimension]
    strengths: list[ReadinessStrength]
    improvements: list[ReadinessImprovement]
    insight: str
    career_risk: str
    career_risk_detail: str
    career_opportunity: str
    career_opportunity_detail: str
    recommended_tools: list[ReadinessToolRecommendation]
    quick_wins: list[str]
    portfolio_mix: dict[str, int] = Field(
        default_factory=dict,
        description="BUILD / BLEND / BOT task counts when 3B analysis exists",
    )
