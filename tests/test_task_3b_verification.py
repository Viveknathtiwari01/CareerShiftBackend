"""Tests for 3B tool verification pipeline."""

from app.services.task_3b_verification import sanitize_llm_analyses


def test_forces_unverified_on_tools():
    raw = [
        {
            "task_index": 0,
            "category": "BOT",
            "rationale": "High frequency",
            "reason": "Repetitive data work",
            "next_actions": ["a", "b", "c"],
            "components": [
                {
                    "name": "Extract data",
                    "description": "Pull from systems",
                    "is_automatable": True,
                    "capability": "data extraction",
                    "solution_pattern": "scheduled pipeline",
                    "tools": [
                        {
                            "name": "Power Automate",
                            "cost_band": "freemium",
                            "pros": ["Microsoft integration"],
                            "cons": ["Learning curve"],
                            "credibility_note": "Widely used in enterprise",
                            "feasibility": "company_tech",
                            "verification_status": "VERIFIED",
                            "verified_at": "2026-01-01",
                        }
                    ],
                }
            ],
        }
    ]
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
