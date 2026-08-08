import pytest

from app.services.ai_readiness_scorer import ReadinessInput, compute_ai_readiness


def test_high_readiness_profile():
    result = compute_ai_readiness(
        ReadinessInput(
            ai_frequency="Daily",
            ai_tools=["ChatGPT", "Claude", "Copilot"],
            ai_comfort_level=8,
            task_ai_assistance=["Frequently", "Always", "Sometimes"],
            build_count=4,
            bot_count=2,
            blend_count=5,
            task_count=11,
            avg_auto_potential=55.0,
        )
    )
    assert result.overall_score >= 55
    assert result.tier_label in {"High", "Medium", "Low"}
    assert len(result.dimensions) >= 5


def test_low_readiness_profile():
    result = compute_ai_readiness(
        ReadinessInput(
            ai_frequency="Never",
            ai_tools=[],
            ai_comfort_level=2,
            task_ai_assistance=["Never", "Never"],
            build_count=1,
            bot_count=0,
            blend_count=1,
            task_count=2,
            avg_auto_potential=20.0,
        )
    )
    assert result.overall_score < 50
    assert result.improvement_areas
