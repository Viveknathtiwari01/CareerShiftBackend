from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

AI_FREQUENCY_SCORES = {
    "never": 10,
    "rarely": 25,
    "occasionally": 40,
    "weekly": 55,
    "several times a week": 70,
    "daily": 85,
    "multiple times a day": 95,
}

AI_ASSISTANCE_SCORES = {
    "never": 10,
    "sometimes": 45,
    "frequently": 75,
    "always": 90,
}


@dataclass
class ReadinessInput:
    ai_frequency: str
    ai_tools: list[str]
    ai_comfort_level: int
    task_ai_assistance: list[str]
    build_count: int
    bot_count: int
    blend_count: int
    task_count: int
    avg_auto_potential: float | None


@dataclass
class ReadinessDimension:
    name: str
    score: int
    weight: float


@dataclass
class ReadinessResult:
    overall_score: int
    tier_label: str
    tier_description: str
    dimensions: list[ReadinessDimension]
    strengths: list[str]
    improvement_areas: list[str]
    factors: list[dict[str, str | int]]


def _normalize_frequency(value: str) -> str:
    return value.strip().lower()


def _score_frequency(value: str) -> int:
    normalized = _normalize_frequency(value)
    for key, score in AI_FREQUENCY_SCORES.items():
        if key in normalized:
            return score
    return 40


def _score_ai_assistance(values: list[str]) -> int:
    if not values:
        return 30
    scores = []
    for raw in values:
        normalized = raw.strip().lower()
        matched = next(
            (score for label, score in AI_ASSISTANCE_SCORES.items() if label in normalized),
            40,
        )
        scores.append(matched)
    return round(sum(scores) / len(scores))


def _tier_for_score(score: int) -> tuple[str, str]:
    if score >= 70:
        return (
            "High",
            "You can leverage AI immediately to amplify productivity and career resilience.",
        )
    if score >= 40:
        return (
            "Medium",
            "You have a solid foundation — focused upskilling over 3–6 months will raise your readiness significantly.",
        )
    return (
        "Low",
        "AI adoption is still early — prioritizing tool fluency and workflow design will unlock high upside.",
    )


def compute_ai_readiness(data: ReadinessInput) -> ReadinessResult:
    adoption = _score_frequency(data.ai_frequency)
    tool_usage = min(100, 20 + len(data.ai_tools) * 8)
    comfort = max(0, min(100, data.ai_comfort_level * 10))
    task_usage = _score_ai_assistance(data.task_ai_assistance)

    total_tasks = max(data.task_count, 1)
    bot_pct = data.bot_count / total_tasks
    build_pct = data.build_count / total_tasks
    blend_pct = data.blend_count / total_tasks

    bot_exposure = round(min(100, bot_pct * 100))
    build_strength = round(min(100, build_pct * 100 + (data.avg_auto_potential or 0) * 0.15))
    blend_fluency = round(min(100, blend_pct * 100 + tool_usage * 0.2))

    dimensions = [
        ReadinessDimension("AI Adoption", adoption, 0.2),
        ReadinessDimension("Tool Usage", tool_usage, 0.15),
        ReadinessDimension("Comfort Level", comfort, 0.15),
        ReadinessDimension("Task AI Usage", task_usage, 0.15),
        ReadinessDimension("Automation Exposure", bot_exposure, 0.15),
        ReadinessDimension("Human Mastery", build_strength, 0.1),
        ReadinessDimension("Blend Fluency", blend_fluency, 0.1),
    ]

    weighted = sum(d.score * d.weight for d in dimensions)
    overall = max(0, min(100, round(weighted)))

    tier_label, tier_description = _tier_for_score(overall)

    strengths: list[str] = []
    improvements: list[str] = []
    if adoption >= 60:
        strengths.append("Regular AI usage in your daily workflow")
    else:
        improvements.append("Increase consistent AI usage frequency")

    if len(data.ai_tools) >= 3:
        strengths.append("Diverse AI tool portfolio")
    else:
        improvements.append("Expand your AI tool stack beyond one assistant")

    if build_pct >= 0.25:
        strengths.append("Strong portfolio of human-mastery (BUILD) tasks")
    if bot_pct >= 0.2:
        improvements.append("High automation exposure — prioritize upskilling on judgment-heavy work")

    if blend_pct >= 0.3:
        strengths.append("Healthy mix of human-AI collaboration tasks")
    else:
        improvements.append("Practice blending AI into more daily tasks with clear review checkpoints")

    if not strengths:
        strengths.append("Clear baseline to measure progress from")
    if not improvements:
        improvements.append("Deepen advanced AI workflow design for leadership roles")

    factors = [
        {"label": "AI frequency", "impact": adoption - 50},
        {"label": "Tools in use", "impact": tool_usage - 50},
        {"label": "Comfort level", "impact": comfort - 50},
        {"label": "Task-level AI usage", "impact": task_usage - 50},
        {"label": "BOT task exposure", "impact": bot_exposure - 50},
    ]

    return ReadinessResult(
        overall_score=overall,
        tier_label=tier_label,
        tier_description=tier_description,
        dimensions=dimensions,
        strengths=strengths[:4],
        improvement_areas=improvements[:4],
        factors=factors,
    )
