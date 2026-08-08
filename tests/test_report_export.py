from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.career_intelligence_report import CareerIntelligenceReportResponse
from app.services.report_export import (
    export_report_json,
    generate_scorecard,
    render_report_html,
    render_report_pdf,
    render_toolkit_html,
)


def _sample_report() -> CareerIntelligenceReportResponse:
    assessment_id = uuid4()
    return CareerIntelligenceReportResponse(
        assessment_id=assessment_id,
        report_version="1.0.0",
        generated_at=datetime.now(timezone.utc),
        strategic_note="Focus on BLEND workflows and deepen BUILD mastery.",
        overview={
            "overall_score": 72,
            "tasks_analyzed": 3,
            "competency_count": 2,
            "ai_tools_count": 2,
            "automation_pct": 33,
            "career_risk": "Medium",
            "job_title": "Product Manager",
            "industry": "Technology",
            "experience_years": 8,
            "profession_summary": "Leads cross-functional product delivery.",
            "reading_time_minutes": 10,
        },
        ai_readiness={
            "overall_score": 72,
            "tier_label": "High",
            "tier_description": "Strong adoption baseline.",
            "dimensions": [{"name": "AI Adoption", "score": 75}],
            "strengths": ["Regular AI usage"],
            "improvement_areas": ["Expand tool stack"],
            "factors": [{"label": "AI frequency", "impact": 10}],
        },
        competencies=[
            {
                "category": "Business",
                "items": [{"name": "Product Strategy", "importance": "High"}],
            }
        ],
        daily_work={
            "tasks": [
                {
                    "title": "Roadmap planning",
                    "hours_per_week": 8,
                    "complexity": "high",
                    "ai_assistance": "Sometimes",
                }
            ],
            "total_hours_per_week": 8,
        },
        task_routing=[
            {
                "task_id": str(uuid4()),
                "task_title": "Roadmap planning",
                "category": "BLEND",
                "rationale": "AI can draft, human decides",
                "reason": "Requires stakeholder judgment",
                "next_actions": ["Pilot AI drafts", "Define review checklist", "Track time saved"],
                "auto_potential": 45,
                "risk_level": "Medium",
                "recommended_tools": ["ChatGPT"],
            }
        ],
        career_identity={
            "identity_title": "AI-Augmented Product Manager",
            "confidence_pct": 82,
            "executive_summary": "Well positioned for AI-augmented product leadership.",
            "ideal_roles": ["AI-Augmented Product Manager"],
            "superpowers": ["Regular AI usage"],
            "blind_spots": ["Expand tool stack"],
            "growth_strategy": "Deepen BUILD tasks while automating BOT work.",
        },
        learning_roadmap=[
            {"horizon": "30 days", "title": "Quick wins", "items": ["Pilot AI drafts"]},
        ],
        ai_toolkit=[
            {"name": "ChatGPT", "category": "Recommended", "use_case": "Drafting", "source": "3B Analysis"},
        ],
        action_plan={
            "start": ["Regular AI usage"],
            "stop": [],
            "automate": [],
            "learn": ["Expand tool stack"],
        },
        before_after={"current_role": "Product Manager", "future_role": "AI-Augmented Product Manager"},
        cost_roi={"hours_automatable_per_week": 2.5},
        market_urgency={"risk_level": "Medium", "automation_pct": 33},
    )


def test_render_report_html_contains_real_job_title():
    report = _sample_report()
    html = render_report_html(report, recipient_name="Alex Morgan")
    assert "Product Manager" in html
    assert "Alex Morgan" in html
    assert "Roadmap planning" in html
    assert "72/100" in html
    assert "Senior Backend Engineer" not in html


def test_render_report_pdf_produces_bytes():
    report = _sample_report()
    pdf = render_report_pdf(report, recipient_name="Alex Morgan")
    assert pdf[:4] == b"%PDF"


def test_generate_scorecard_uses_report_scores():
    report = _sample_report()
    card = generate_scorecard(report, recipient_name="Alex Morgan")
    assert card.score == 72
    assert "Product Manager" in card.linkedin_text
    assert str(report.assessment_id) in card.report_url


def test_export_json_matches_report():
    report = _sample_report()
    payload = export_report_json(report)
    assert payload["overview"]["job_title"] == "Product Manager"
    assert payload["ai_readiness"]["overall_score"] == 72


def test_toolkit_html_lists_tools_from_report():
    base = _sample_report()
    report = base.model_copy(
        update={
            "ai_toolkit": [
                base.ai_toolkit[0].model_copy(
                    update={"use_case": "Mentioned in 3 task recommendation(s)"}
                )
            ]
        }
    )
    html = render_toolkit_html(report, recipient_name="Alex Morgan")
    assert "ChatGPT" in html
    assert "Product Manager" in html
    assert "Recommended AI Toolkit" in html
    assert "Tool Category" in html
    assert "Why" in html
    assert "Requires stakeholder judgment" in html
    assert "Mentioned in 3 task recommendation(s)" not in html


def test_report_html_uses_task_reason_for_toolkit_why():
    base = _sample_report()
    report = base.model_copy(
        update={
            "ai_toolkit": [
                base.ai_toolkit[0].model_copy(
                    update={"use_case": "Mentioned in 3 task recommendation(s)"}
                )
            ]
        }
    )
    html = render_report_html(report, recipient_name="Alex Morgan")
    assert "Requires stakeholder judgment" in html
    assert "Mentioned in 3 task recommendation(s)" not in html
