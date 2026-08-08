from app.services.report_generator import enrich_ai_toolkit, _tool_reason_from_task_entries


def test_tool_reason_uses_task_analysis_reason():
    entries = [
        {
            "task_title": "Roadmap planning",
            "reason": "Requires stakeholder judgment and trade-off decisions.",
            "rationale": "AI can draft, human decides",
            "category": "BLEND",
        }
    ]
    assert _tool_reason_from_task_entries(entries) == (
        "Roadmap planning: Requires stakeholder judgment and trade-off decisions."
    )


def test_enrich_ai_toolkit_replaces_legacy_use_case():
    task_routing = [
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
    tools = [
        {
            "name": "Power BI",
            "category": "Recommended",
            "use_case": "Mentioned in 3 task recommendation(s)",
            "source": "3B Analysis",
        }
    ]

    enriched = enrich_ai_toolkit(tools, task_routing)

    assert enriched[0]["use_case"].startswith("Weekly reporting:")
    assert "Highly repetitive data pulls suitable for automation." in enriched[0]["use_case"]
    assert "Stakeholder updates:" in enriched[0]["use_case"]
    assert "Mentioned in 3 task recommendation(s)" not in enriched[0]["use_case"]
