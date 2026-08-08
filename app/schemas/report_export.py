from pydantic import BaseModel, Field


class ReportScorecardResponse(BaseModel):
    headline: str
    linkedin_text: str
    twitter_text: str
    hashtags: list[str] = Field(default_factory=list)
