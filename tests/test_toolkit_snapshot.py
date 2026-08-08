from app.services.report_generator import (
    build_toolkit_from_analyses,
    needs_legacy_toolkit_enrichment,
)


def test_build_toolkit_from_analyses_is_stable():
    analyses = [
        {
            "task_title": "Weekly reporting",
            "category": "BOT",
            "rationale": "Template-driven output",
            "reason": "Highly repetitive data pulls suitable for automation.",
            "recommended_tools": ["Power BI"],
        },
        {
            "task_title": "Stakeholder updates",
            "category": "BLEND",
            "rationale": "Draft with AI, refine manually",
            "reason": "AI can draft summaries while you keep the narrative voice.",
            "recommended_tools": ["Power BI", "ChatGPT"],
        },
    ]

    first = build_toolkit_from_analyses(analyses)
    second = build_toolkit_from_analyses(analyses)

    assert first == second
    assert first[0]["use_case"].startswith("Weekly reporting:")
    assert "Highly repetitive data pulls suitable for automation." in first[0]["use_case"]
    assert first[0]["priority_rank"] == 1
    assert first[0]["priority_label"] == "Critical"


def test_toolkit_priority_ranks_by_impact():
    analyses = [
        {
            "task_title": "Weekly reporting",
            "category": "BOT",
            "reason": "Highly repetitive data pulls suitable for automation.",
            "future_impact": "High",
            "auto_potential": 90,
            "risk_level": "High",
            "recommended_tools": ["Power BI"],
        },
        {
            "task_title": "Stakeholder updates",
            "category": "BLEND",
            "reason": "AI can draft summaries while you keep the narrative voice.",
            "future_impact": "Medium",
            "auto_potential": 45,
            "risk_level": "Medium",
            "recommended_tools": ["ChatGPT"],
        },
        {
            "task_title": "Budget review",
            "category": "BOT",
            "reason": "Template-driven spreadsheet work.",
            "future_impact": "High",
            "auto_potential": 85,
            "risk_level": "High",
            "recommended_tools": ["Power BI", "Notion"],
        },
    ]

    tools = build_toolkit_from_analyses(analyses)

    assert tools[0]["name"] == "Power BI"
    assert tools[0]["priority_rank"] == 1
    assert tools[0]["priority_label"] == "Critical"
    assert tools[0]["priority_reason"]
    assert all(tool["priority_rank"] for tool in tools)
    assert tools[0]["priority_rank"] < tools[-1]["priority_rank"]


def test_legacy_toolkit_detection():
    assert needs_legacy_toolkit_enrichment(
        [{"name": "Power BI", "use_case": "Mentioned in 3 task recommendation(s)"}]
    )
    assert not needs_legacy_toolkit_enrichment(
        [{"name": "Power BI", "use_case": "Weekly reporting: Highly repetitive data pulls."}]
    )
