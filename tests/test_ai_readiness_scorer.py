from app.services.ai_readiness_scorer import ScorerInput, compute_ai_readiness, score_tier, tier_label


def test_compute_readiness_high_adoption():
    result = compute_ai_readiness(
        ScorerInput(
            ai_frequency="daily",
            ai_tools=["ChatGPT", "Cursor", "Copilot"],
            ai_comfort_level=8,
            digital_skills_count=5,
            tasks=[
                {"ai_assistance": "heavy", "confidence_score": 85},
                {"ai_assistance": "moderate", "confidence_score": 75},
            ],
            analyses=[
                {
                    "category": "BLEND",
                    "auto_potential": 60,
                    "recommended_tools": ["ChatGPT", "Cursor"],
                    "next_actions": ["Pilot AI drafting"],
                },
                {
                    "category": "BUILD",
                    "auto_potential": 30,
                    "recommended_tools": [],
                    "next_actions": ["Deepen domain expertise"],
                },
            ],
            competencies=[{"name": "Strategic Planning", "why_it_matters": "Core leadership skill"}],
        )
    )

    assert result.overall_score >= 60
    assert result.tier in ("High", "Medium")
    assert result.tier_label == tier_label(result.tier)
    assert len(result.factors) == 5
    assert len(result.dimensions) == 6
    assert result.portfolio_mix["BLEND"] == 1
    assert result.portfolio_mix["BUILD"] == 1


def test_compute_readiness_low_adoption():
    result = compute_ai_readiness(
        ScorerInput(
            ai_frequency="rarely",
            ai_tools=[],
            ai_comfort_level=3,
            digital_skills_count=1,
            tasks=[{"ai_assistance": "none", "confidence_score": 40}],
            analyses=[],
            competencies=[],
        )
    )

    assert result.overall_score < 50
    assert score_tier(result.overall_score) == "Low"
    assert result.recommended_tools[0].name == "ChatGPT"


def test_factor_contributions_sum_to_overall():
    result = compute_ai_readiness(
        ScorerInput(
            ai_frequency="weekly",
            ai_tools=["ChatGPT"],
            ai_comfort_level=6,
            digital_skills_count=3,
            tasks=[{"ai_assistance": "light", "confidence_score": 60}],
            analyses=[
                {
                    "category": "BOT",
                    "auto_potential": 80,
                    "recommended_tools": ["Zapier"],
                    "next_actions": ["Automate reporting"],
                }
            ],
            competencies=[],
        )
    )

    weighted = round(sum(f.contribution for f in result.factors))
    assert abs(weighted - result.overall_score) <= 1
