"""Tests for 3B tool verification pipeline."""

from app.services.task_3b_verification import sanitize_llm_analyses


def _full_llm_item(**overrides):
    base = {
        "task_index": 0,
        "category": "BLEND",
        "rationale": "Weekly reporting mix",
        "reason": "High frequency and moderate AI usage suggest BLEND.",
        "next_action": "Automate data pull and AI-draft the narrative.",
        "human_capability": "Executive interpretation",
        "pace_of_change": "fast-moving",
        "pace_of_change_note": "LLM drafting tools evolve quickly.",
        "cost_of_staying_as_is": {
            "type": "augmentation_opportunity",
            "narrative": "Manual rebuild each week costs recurring time.",
        },
        "learning_implication": {
            "future_requirement": "Executive data storytelling",
            "current_capability": "Strong spreadsheet mechanics",
            "capability_gap": "Executive storytelling gap",
            "practice": ["Draft exec summaries with AI", "Review with manager"],
            "deprioritize": ["Spreadsheet formatting"],
            "where_to_learn": ["Internal comms workshop"],
        },
        "feasibility_assessment": "You can likely test self-serve options this week.",
        "components": [
            {
                "name": "Data extraction",
                "description": "Pull weekly metrics",
                "is_automatable": True,
                "capability": "workflow automation",
                "solution_pattern": "scheduled data pipeline",
                "tools": [
                    {
                        "name": "Power Automate",
                        "cost_band": "freemium",
                        "pricing_note": "Included in many Microsoft 365 plans",
                        "pros": ["Microsoft integration"],
                        "cons": ["Learning curve"],
                        "fit_description": "Fits finance reporting in Microsoft shops",
                        "market_note": "Common workflow tool in enterprise Microsoft environments",
                        "feasibility": "company_tech",
                    }
                ],
            }
        ],
    }
    base.update(overrides)
    return base


def test_forces_unverified_on_tools():
    raw = [_full_llm_item()]
    result = sanitize_llm_analyses(raw)
    tool = result[0]["components"][0]["tools"][0]
    assert tool["verification_status"] == "UNVERIFIED"
    assert tool["verified_at"] is None
    assert tool["verified_by"] is None


def test_empty_components_allowed():
    raw = [
        {
            "task_index": 0,
            "category": "BUILD",
            "rationale": "Judgment",
            "reason": "High criticality",
            "next_actions": ["a", "b", "c"],
            "components": [],
        }
    ]
    result = sanitize_llm_analyses(raw)
    assert result[0]["components"] == []


def test_maps_ui_fields_from_prompt_contract():
    raw = [_full_llm_item()]
    result = sanitize_llm_analyses(raw)
    item = result[0]
    assert item["human_capability"] == "Executive interpretation"
    assert item["next_action"] == "Automate data pull and AI-draft the narrative."
    assert item["velocity"] == "fast-moving"
    assert item["velocity_note"] == "LLM drafting tools evolve quickly."
    assert item["learn_gap"] == "Executive storytelling gap"
    assert item["learn_future"] == "Executive data storytelling"
    assert item["learn_current"] == "Strong spreadsheet mechanics"
    assert "Draft exec summaries" in item["learn_do"]
    assert item["learn_dont"] == "Spreadsheet formatting"
    assert item["where_to_learn"] == "Internal comms workshop"
    assert item["feasibility_note"] == "You can likely test self-serve options this week."
    tool = item["components"][0]["tools"][0]
    assert tool["fit_description"] == "Fits finance reporting in Microsoft shops"
    assert tool["market_note"] == "Common workflow tool in enterprise Microsoft environments"
    assert tool["pricing_note"] == "Included in many Microsoft 365 plans"
    assert item["cost_of_staying_as_is_json"]["type"] == "augmentation_opportunity"
    assert "Manual rebuild" in item["cost_of_staying_as_is_json"]["narrative"]
    assert item["next_actions"][0] == item["next_action"]


def test_build_category_preserved():
    raw = [_full_llm_item(category="BUILD", components=[])]
    result = sanitize_llm_analyses(raw)
    assert result[0]["category"] == "BUILD"
    assert result[0]["components"] == []
