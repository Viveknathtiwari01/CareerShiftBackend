from pydantic import BaseModel, Field, UUID4
from typing import List, Optional
from datetime import datetime

class UserProfileBase(BaseModel):
    job_title: str = Field(..., description="Current Job Title")
    industry: str = Field(..., description="Current Company / Industry")
    business_function: str = Field(..., description="Department / Business Function")
    domain: str = Field(..., description="Functional Domain")
    specialization: str = Field(..., description="Specialization")
    
    experience_years: int = Field(..., ge=0, description="Total Experience in years")
    salary: Optional[str] = Field(None, description="Current Salary")    
    technical_skills: List[str] = Field(default_factory=list, description="Technical Skills")
    professional_skills: List[str] = Field(default_factory=list, description="Professional Skills")
    soft_skills: List[str] = Field(default_factory=list, description="Soft Skills")
    behavioural_skills: List[str] = Field(default_factory=list, description="Behavioural Skills")
    digital_skills: List[str] = Field(default_factory=list, description="Digital Skills")
    
    ai_frequency: str = Field(..., description="AI Usage Frequency")
    ai_tools: List[str] = Field(default_factory=list, description="AI Tools Used")
    ai_comfort_level: int = Field(..., ge=1, le=10, description="AI Comfort Level")

class UserProfileCreate(UserProfileBase):
    pass

class UserProfileUpdate(BaseModel):
    job_title: Optional[str] = None
    industry: Optional[str] = None
    business_function: Optional[str] = None
    domain: Optional[str] = None
    specialization: Optional[str] = None
    
    experience_years: Optional[int] = Field(None, ge=0)
    salary: Optional[str] = None    
    technical_skills: Optional[List[str]] = None
    professional_skills: Optional[List[str]] = None
    soft_skills: Optional[List[str]] = None
    behavioural_skills: Optional[List[str]] = None
    digital_skills: Optional[List[str]] = None
    
    ai_frequency: Optional[str] = None
    ai_tools: Optional[List[str]] = None
    ai_comfort_level: Optional[int] = Field(None, ge=1, le=10)

class UserProfileResponse(UserProfileBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GenerateSkillsRequest(BaseModel):
    job_title: str
    industry: str
    business_function: str
    functional_domain: str
    specialization: str
    experience: str

