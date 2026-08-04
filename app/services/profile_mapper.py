from typing import Any

from app.models.profile import UserProfile

PIPELINE_PROFILE_FIELDS = (
    "job_title",
    "industry",
    "business_function",
    "domain",
    "specialization",
    "technical_skills",
    "experience_years",
)


def profile_to_pipeline_input(profile: UserProfile) -> dict[str, Any]:
    """Map UserProfile to the career assessment input expected by RoleUnderstandingService."""
    return {
        "job_title": profile.job_title,
        "industry": profile.industry,
        "business_function": profile.business_function,
        "domain": profile.domain,
        "specialization": profile.specialization,
        "technical_skills": profile.technical_skills or [],
        "experience_years": profile.experience_years,
    }
