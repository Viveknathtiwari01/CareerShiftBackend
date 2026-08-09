from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.ai_readiness import AIReadinessResponse
from app.schemas.assessment_task_analysis import TaskAnalysisRunResponse
from app.schemas.career_intelligence_report import (
    CareerIntelligenceReportResponse,
    ReportActionPlanSection,
    ReportBeforeAfterSection,
    ReportCareerIdentitySection,
    ReportCostRoiSection,
    ReportDailyWorkSection,
    ReportMarketUrgencySection,
    ReportOverviewSection,
)
from app.services.report_export import generate_scorecard, render_report_html, render_toolkit_html


def _sample_report() -> CareerIntelligenceReportResponse:
    return CareerIntelligenceReportResponse(
        assessment_id=uuid4(),
        report_version="1.0",
        generated_at=datetime.now(timezone.utc),
        strategic_note="Focus on BLEND workflows this quarter to capture quick productivity gains.",
        overview=ReportOverviewSection(kpis=[], career_snapshot=[], insight="Strong foundation."),
        ai_readiness=AIReadinessResponse(
            overall_score=72,
            tier="High",
            tier_label="Strong",
            summary="Solid AI adoption with room to automate repetitive tasks.",
            factors=[],
            dimensions=[],
            strengths=[],
            improvements=[],
            insight="Keep momentum.",
            career_risk="Moderate",
            career_risk_detail="Some tasks exposed to automation.",
            career_opportunity="High",
            career_opportunity_detail="BLEND tasks offer leverage.",
            recommended_tools=[],
            quick_wins=["Pilot AI on weekly reporting"],
            portfolio_mix={"BUILD": 3, "BLEND": 4, "BOT": 2},
        ),
        task_routing=TaskAnalysisRunResponse(analyses=[], regenerated=False),
        before_after=ReportBeforeAfterSection(
            role_today="HR Manager",
            role_future="AI-Augmented HR Manager",
            hours_freed_per_week=6.5,
            narrative="Your role is shifting toward strategic people leadership.",
            shifts=["More time on employee experience"],
        ),
        upskill_roadmap=[],
        ai_toolkit=[],
        cost_roi=ReportCostRoiSection(
            ld_investment=1200,
            ai_tools_cost=480,
            hours_saved_weekly=6.5,
            roi_summary="Positive ROI within one quarter.",
        ),
        market_urgency=ReportMarketUrgencySection(
            urgency_score=65,
            demand_pct=70,
            roles_at_risk_pct=35,
            salary_premium_pct=12,
            summary="Healthcare HR roles are adopting AI steadily.",
        ),
        action_plan=ReportActionPlanSection(),
        career_identity=ReportCareerIdentitySection(
            title="AI-Augmented HR Manager",
            subtitle="Healthcare Specialist",
            narrative="Experienced HR leader.",
            closing_note="AI augments your impact.",
        ),
        competencies=[],
        daily_work=ReportDailyWorkSection(),
    )


def test_generate_scorecard_linkedin_and_twitter():
    report = _sample_report()
    scorecard = generate_scorecard(report, job_title="HR Manager")

    assert "72/100" in scorecard.linkedin_text
    assert "HR Manager" in scorecard.linkedin_text
    assert len(scorecard.twitter_text) <= 280
    assert scorecard.hashtags


def test_render_report_html_contains_key_sections():
    html = render_report_html(_sample_report(), recipient_name="Alex", job_title="HR Manager")
    assert "Career Intelligence Report" in html
    assert "Alex" in html
    assert "3B Task Analysis" in html
    assert "Strategic Note" in html


def test_render_toolkit_html_empty_categories():
    html = render_toolkit_html(_sample_report(), job_title="HR Manager")
    assert "Personal AI Toolkit" in html
    assert "HR Manager" in html
