"""Tests for 3B grounding payload."""

from uuid import uuid4

from app.models.assessment_task import AssessmentTask
from app.models.profile import UserProfile
from app.services.task_3b_grounding import build_3b_grounding_payload, build_profile_grounding


def test_profile_grounding_identity_and_experience_only():
    profile = UserProfile(
        user_id=uuid4(),
        job_title="Analyst",
        industry="Finance",
        business_function="Operations",
        domain="Risk",
        specialization="Credit",
        experience_years=8,
        ai_frequency="weekly",
        ai_comfort_level=5,
    )
    data = build_profile_grounding(profile)
    assert set(data.keys()) == {
        "job_title",
        "industry",
        "business_function",
        "domain",
        "specialization",
        "experience_years",
    }
    assert "ai_tools" not in data
    assert "technical_skills" not in data


def test_grounding_includes_manual_notes():
    profile = UserProfile(
        user_id=uuid4(),
        job_title="Engineer",
        industry="Tech",
        business_function="Engineering",
        domain="Platform",
        specialization="Backend",
        experience_years=5,
        ai_frequency="daily",
        ai_comfort_level=7,
    )
    task = AssessmentTask(
        assessment_id=uuid4(),
        title="API design",
        description="Design REST APIs",
        hours_per_week=4,
        manual_notes="I spend most time on stakeholder alignment",
    )
    payload = build_3b_grounding_payload(
        profile,
        {"profession_summary": "Platform engineer", "competencies": []},
        [task],
    )
    assert payload["reviewed_tasks"][0]["manual_notes"] == "I spend most time on stakeholder alignment"
