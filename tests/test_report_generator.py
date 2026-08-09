from uuid import uuid4

from app.services.report_generator import ReportGeneratorInput, generate_career_intelligence_report


def _sample_input() -> ReportGeneratorInput:
    return ReportGeneratorInput(
        assessment_id=uuid4(),
        profile={
            "job_title": "HR Manager",
            "industry": "Healthcare",
            "business_function": "Human Resources",
            "domain": "Talent Management",
            "specialization": "Employee Relations",
            "experience_years": 8,
            "salary": "$90,000 - $110,000",
            "digital_skills": ["Excel", "HRIS", "Slack"],
            "ai_frequency": "weekly",
            "ai_tools": ["ChatGPT"],
            "ai_comfort_level": 6,
        },
        tasks=[
            {
                "task_id": uuid4(),
                "title": "Policy drafting",
                "category": "Documentation",
                "hours_per_week": 6,
                "business_criticality": "High",
                "ai_assistance": "sometimes",
                "confidence_score": 80,
                "category_3b": "BLEND",
            },
            {
                "task_id": uuid4(),
                "title": "Interview scheduling",
                "category": "Operations",
                "hours_per_week": 4,
                "business_criticality": "Medium",
                "ai_assistance": "never",
                "confidence_score": 90,
                "category_3b": "BOT",
            },
        ],
        analyses=[
            {
                "task_id": uuid4(),
                "task_title": "Policy drafting",
                "category": "BLEND",
                "rationale": "AI can draft, human approves",
                "reason": "Requires judgment on tone and compliance.",
                "next_actions": ["Pilot AI templates", "Create approval checklist", "Track time saved"],
                "auto_potential": 55,
                "recommended_tools": ["ChatGPT", "Notion AI"],
            },
            {
                "task_id": uuid4(),
                "task_title": "Interview scheduling",
                "category": "BOT",
                "rationale": "Repetitive coordination work",
                "reason": "Calendar coordination follows predictable rules.",
                "next_actions": ["Connect scheduling bot", "Define escalation rules", "Measure hours saved"],
                "auto_potential": 80,
                "recommended_tools": ["Zapier"],
            },
        ],
        competencies=[
            {
                "name": "Employee Relations",
                "category": "Business",
                "importance": "High",
                "expected_level": "Advanced",
            },
            {
                "name": "Prompt Engineering",
                "category": "Technical",
                "importance": "High",
                "expected_level": "Beginner",
            },
        ],
        profession_summary="Experienced HR leader focused on employee experience.",
    )


def test_generate_report_returns_all_sections():
    report = generate_career_intelligence_report(_sample_input())

    assert report.ai_readiness.overall_score >= 0
    assert len(report.task_routing.analyses) == 2
    assert report.before_after.hours_freed_per_week >= 0
    assert len(report.upskill_roadmap) == 3
    assert len(report.ai_toolkit) >= 1
    assert any("Policy drafting" in tool.use_case for tool in report.ai_toolkit)
    assert any(tool.task_links for tool in report.ai_toolkit)
    assert report.cost_roi.ld_investment > 0
    assert report.market_urgency.urgency_score >= 20
    assert report.action_plan.start_doing
    assert report.career_identity.title.startswith("AI-Augmented")
    assert report.competencies
    assert report.daily_work.total_hours == 10
    assert report.strategic_note


def test_generate_report_competency_growth_labels():
    report = generate_career_intelligence_report(_sample_input())
    items = [item for group in report.competencies for item in group.items]
    growth_values = {item.growth for item in items}
    assert "Critical Focus" in growth_values or "Develop" in growth_values
