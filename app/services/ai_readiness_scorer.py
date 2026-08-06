"""Deterministic AI Readiness Score (Output A) — explainable 0–100 baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.ai_readiness import (
    AIReadinessResponse,
    ReadinessDimension,
    ReadinessFactor,
    ReadinessImprovement,
    ReadinessStrength,
    ReadinessToolRecommendation,
)

FREQUENCY_SCORES: dict[str, int] = {
    "daily": 95,
    "every day": 95,
    "multiple times a day": 100,
    "weekly": 75,
    "few times a week": 80,
    "monthly": 50,
    "occasionally": 45,
    "rarely": 25,
    "never": 10,
}

AI_ASSISTANCE_SCORES: dict[str, int] = {
    "heavy": 90,
    "extensively": 90,
    "moderate": 70,
    "sometimes": 60,
    "light": 45,
    "minimal": 40,
    "none": 15,
    "not at all": 10,
}

TOOL_FIT_HINTS: dict[str, tuple[str, str]] = {
    "chatgpt": ("General reasoning & drafting", "Brainstorming and first drafts"),
    "claude": ("Long-context analysis", "Documentation and research synthesis"),
    "copilot": ("Inline code assistance", "Boilerplate and unit tests"),
    "cursor": ("AI-native development", "Daily coding and refactoring"),
    "perplexity": ("Cited research", "Exploring new tools and libraries"),
    "gemini": ("Multimodal workspace", "Summaries and slide drafts"),
    "notion ai": ("In-document writing", "Meeting notes and plans"),
    "zapier": ("Workflow automation", "Connecting apps and triggers"),
}


@dataclass
class ScorerInput:
    ai_frequency: str
    ai_tools: list[str]
    ai_comfort_level: int
    digital_skills_count: int
    tasks: list[dict[str, Any]]
    analyses: list[dict[str, Any]]
    competencies: list[dict[str, Any]]


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _lookup_score(mapping: dict[str, int], value: str | None, default: int = 50) -> int:
    normalized = _normalize(value)
    if normalized in mapping:
        return mapping[normalized]
    for key, score in mapping.items():
        if key in normalized or normalized in key:
            return score
    return default


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def score_tier(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def tier_label(tier: str) -> str:
    return {"High": "Strong", "Medium": "Good", "Low": "Developing"}.get(tier, "Good")


def _portfolio_mix(analyses: list[dict[str, Any]]) -> dict[str, int]:
    mix = {"BUILD": 0, "BLEND": 0, "BOT": 0}
    for row in analyses:
        category = (row.get("category") or "BLEND").upper()
        if category in mix:
            mix[category] += 1
    return mix


def compute_ai_readiness(data: ScorerInput) -> AIReadinessResponse:
    frequency_score = _lookup_score(FREQUENCY_SCORES, data.ai_frequency, 50)
    tools_score = _clamp(35 + len(data.ai_tools) * 12)
    comfort_score = _clamp(data.ai_comfort_level * 10)
    adoption_score = _clamp(frequency_score * 0.45 + tools_score * 0.35 + comfort_score * 0.20)

    assistance_values = [
        _lookup_score(AI_ASSISTANCE_SCORES, task.get("ai_assistance"), 50)
        for task in data.tasks
    ]
    task_usage_score = (
        _clamp(sum(assistance_values) / len(assistance_values))
        if assistance_values
        else 50
    )

    mix = _portfolio_mix(data.analyses)
    total_analyzed = sum(mix.values()) or 1
    bot_pct = mix["BOT"] / total_analyzed
    blend_pct = mix["BLEND"] / total_analyzed
    build_pct = mix["BUILD"] / total_analyzed

    auto_values = [a.get("auto_potential") for a in data.analyses if a.get("auto_potential") is not None]
    avg_auto = sum(auto_values) / len(auto_values) if auto_values else 50

    automation_score = _clamp(bot_pct * 40 + avg_auto * 0.6) if data.analyses else _clamp(avg_auto)

    confidence_values = [
        task.get("confidence_score")
        for task in data.tasks
        if task.get("confidence_score") is not None
    ]
    avg_confidence = (
        sum(confidence_values) / len(confidence_values) if confidence_values else comfort_score
    )
    build_score = _clamp(build_pct * 55 + avg_confidence * 0.45) if data.analyses else _clamp(avg_confidence)

    tool_names = {
        tool.lower()
        for row in data.analyses
        for tool in (row.get("recommended_tools") or [])
    }
    blend_score = _clamp(blend_pct * 50 + min(len(tool_names), 6) * 8 + task_usage_score * 0.25)

    digital_boost = _clamp(min(data.digital_skills_count, 8) * 8)
    learning_score = _clamp(blend_score * 0.6 + digital_boost * 0.4)

    factors = [
        ReadinessFactor(
            key="adoption",
            label="AI Adoption",
            score=adoption_score,
            weight=0.25,
            contribution=round(adoption_score * 0.25, 1),
            summary=_adoption_summary(frequency_score, tools_score, comfort_score),
        ),
        ReadinessFactor(
            key="task_usage",
            label="Task AI Usage",
            score=task_usage_score,
            weight=0.20,
            contribution=round(task_usage_score * 0.20, 1),
            summary=_task_usage_summary(task_usage_score, len(data.tasks)),
        ),
        ReadinessFactor(
            key="automation",
            label="Automation Readiness",
            score=automation_score,
            weight=0.20,
            contribution=round(automation_score * 0.20, 1),
            summary=_automation_summary(mix, avg_auto),
        ),
        ReadinessFactor(
            key="build_strength",
            label="Human Edge (BUILD)",
            score=build_score,
            weight=0.15,
            contribution=round(build_score * 0.15, 1),
            summary=_build_summary(mix, avg_confidence),
        ),
        ReadinessFactor(
            key="blend_fluency",
            label="BLEND Fluency",
            score=blend_score,
            weight=0.20,
            contribution=round(blend_score * 0.20, 1),
            summary=_blend_summary(mix, len(tool_names)),
        ),
    ]

    overall = _clamp(sum(f.contribution for f in factors))
    tier = score_tier(overall)

    dimensions = [
        ReadinessDimension(subject="Awareness", score=_clamp(comfort_score * 0.6 + frequency_score * 0.4)),
        ReadinessDimension(subject="Adoption", score=adoption_score),
        ReadinessDimension(subject="Tool Usage", score=_clamp(tools_score * 0.5 + task_usage_score * 0.5)),
        ReadinessDimension(subject="Confidence", score=_clamp(avg_confidence)),
        ReadinessDimension(subject="Productivity", score=_clamp(blend_score * 0.5 + automation_score * 0.5)),
        ReadinessDimension(subject="Learning Readiness", score=learning_score),
    ]

    strengths = _derive_strengths(factors, data.competencies)
    improvements = _derive_improvements(factors, dimensions, data.competencies)
    insight = _derive_insight(overall, mix, data.ai_tools, task_usage_score)
    risk, risk_detail = _career_risk(mix, build_score, automation_score)
    opportunity, opp_detail = _career_opportunity(blend_score, build_score, overall)
    tools = _recommended_tools(data.analyses, data.ai_tools)
    quick_wins = _quick_wins(data.analyses, improvements)

    return AIReadinessResponse(
        overall_score=overall,
        tier=tier,
        tier_label=tier_label(tier),
        summary=_overall_summary(overall, tier),
        factors=factors,
        dimensions=dimensions,
        strengths=strengths,
        improvements=improvements,
        insight=insight,
        career_risk=risk,
        career_risk_detail=risk_detail,
        career_opportunity=opportunity,
        career_opportunity_detail=opp_detail,
        recommended_tools=tools,
        quick_wins=quick_wins,
        portfolio_mix=mix,
    )


def _adoption_summary(frequency: int, tools: int, comfort: int) -> str:
    if frequency >= 75 and tools >= 60:
        return "Strong daily AI habits with a solid tool stack."
    if comfort >= 70:
        return "Comfortable with AI — expand into more workflows."
    return "Early-stage adoption — consistent usage will lift your score quickly."


def _task_usage_summary(score: int, task_count: int) -> str:
    if score >= 70:
        return f"AI is actively used across {task_count} reviewed tasks."
    if score >= 45:
        return "Mixed AI usage — several tasks still run fully manual."
    return "Most reviewed tasks are still manual — big upside from BLEND workflows."


def _automation_summary(mix: dict[str, int], avg_auto: float) -> str:
    if not mix or sum(mix.values()) == 0:
        return "Complete 3B analysis to quantify automation potential."
    if mix["BOT"] >= 2:
        return f"{mix['BOT']} BOT tasks identified — strong automation runway."
    return f"Average automation potential around {round(avg_auto)}% across tasks."


def _build_summary(mix: dict[str, int], confidence: float) -> str:
    if mix.get("BUILD", 0) >= 3:
        return "Meaningful BUILD work protects your long-term career edge."
    return f"Human-judgment tasks supported by {round(confidence)}% confidence baseline."


def _blend_summary(mix: dict[str, int], tool_count: int) -> str:
    if mix.get("BLEND", 0) >= 3:
        return f"BLEND zone is active with {tool_count} recommended tools in play."
    return "Expand co-pilot workflows — BLEND is your highest leverage zone."


def _overall_summary(score: int, tier: str) -> str:
    if tier == "High":
        return (
            "You are well positioned to leverage AI across your role — "
            "focus on scaling BLEND workflows and selective BOT automation."
        )
    if tier == "Medium":
        return (
            "You have a solid foundation with clear opportunities to deepen AI adoption "
            "and strengthen long-term career resilience."
        )
    return (
        "AI readiness is still developing — prioritise comfort, daily tool use, "
        "and BLEND experiments for the fastest gains."
    )


def _derive_strengths(
    factors: list[ReadinessFactor],
    competencies: list[dict[str, Any]],
) -> list[ReadinessStrength]:
    top_factors = sorted(factors, key=lambda f: f.score, reverse=True)[:2]
    strengths = [
        ReadinessStrength(title=f.label, detail=f.summary) for f in top_factors if f.score >= 60
    ]
    for comp in competencies[:2]:
        name = comp.get("name")
        if name and len(strengths) < 4:
            strengths.append(
                ReadinessStrength(
                    title=name,
                    detail=comp.get("why_it_matters") or comp.get("professional_context"),
                )
            )
    if not strengths:
        strengths.append(ReadinessStrength(title="Profile baseline captured", detail="Complete task review to refine strengths."))
    return strengths[:4]


def _derive_improvements(
    factors: list[ReadinessFactor],
    dimensions: list[ReadinessDimension],
    competencies: list[dict[str, Any]],
) -> list[ReadinessImprovement]:
    weak_factors = sorted(factors, key=lambda f: f.score)[:3]
    weak_dims = sorted(dimensions, key=lambda d: d.score)[:2]
    items: list[ReadinessImprovement] = []

    for factor in weak_factors:
        if factor.score >= 75:
            continue
        items.append(
            ReadinessImprovement(
                title=factor.label,
                difficulty="Medium" if factor.score >= 50 else "High",
                impact="High" if factor.weight >= 0.2 else "Medium",
            )
        )

    for dim in weak_dims:
        if dim.score >= 70:
            continue
        if not any(i.title == dim.subject for i in items):
            items.append(
                ReadinessImprovement(
                    title=dim.subject,
                    difficulty="Medium" if dim.score >= 45 else "High",
                    impact="High",
                )
            )

    for comp in competencies:
        if len(items) >= 5:
            break
        name = comp.get("name")
        if name and not any(i.title == name for i in items):
            items.append(ReadinessImprovement(title=name, difficulty="Medium", impact="Medium"))

    return items[:5]


def _derive_insight(
    overall: int,
    mix: dict[str, int],
    ai_tools: list[str],
    task_usage: int,
) -> str:
    tool_phrase = ", ".join(ai_tools[:3]) if ai_tools else "general-purpose assistants"
    if mix.get("BLEND", 0) >= mix.get("BOT", 0) and task_usage < 65:
        return (
            f"You already use tools like {tool_phrase}, but many reviewed tasks still run manually. "
            "Expanding AI into documentation, planning, and review loops could unlock significant productivity."
        )
    if mix.get("BOT", 0) >= 2:
        return (
            "Your portfolio has clear automation candidates. Prioritise one BOT workflow this month "
            "while protecting BUILD tasks that define your professional edge."
        )
    return (
        f"Your readiness score of {overall} reflects steady progress. "
        "Double down on BLEND co-pilot habits before pushing deeper into full automation."
    )


def _career_risk(mix: dict[str, int], build_score: int, automation_score: int) -> tuple[str, str]:
    bot = mix.get("BOT", 0)
    build = mix.get("BUILD", 0)
    total = sum(mix.values()) or 1
    if bot / total > 0.45 and build_score < 55:
        return (
            "Elevated Risk",
            "A large share of your tasks is automatable while BUILD strengths are still developing — invest in irreplaceable skills.",
        )
    if bot / total > 0.3:
        return (
            "Medium Risk",
            "Routine work is increasingly AI-assisted, but judgment-heavy BUILD responsibilities remain valuable.",
        )
    return (
        "Lower Risk",
        "Your role balances human mastery with selective automation — maintain BUILD depth as AI tools evolve.",
    )


def _career_opportunity(blend: int, build: int, overall: int) -> tuple[str, str]:
    if blend >= 65 and build >= 60:
        return (
            "High Growth Potential",
            "Strong BLEND fluency plus BUILD depth positions you for AI-augmented leadership paths.",
        )
    if overall >= 55:
        return (
            "Strong Upside",
            "Consistent AI adoption and task clarity create a clear path to higher-impact work.",
        )
    return (
        "Emerging Potential",
        "Foundational readiness is forming — targeted upskilling can accelerate your trajectory quickly.",
    )


def _recommended_tools(
    analyses: list[dict[str, Any]],
    profile_tools: list[str],
) -> list[ReadinessToolRecommendation]:
    seen: set[str] = set()
    results: list[ReadinessToolRecommendation] = []

    for tool in profile_tools + [
        t for row in analyses for t in (row.get("recommended_tools") or [])
    ]:
        key = tool.strip()
        if not key:
            continue
        lower = key.lower()
        if lower in seen:
            continue
        seen.add(lower)
        fit, use_case = TOOL_FIT_HINTS.get(lower, ("Matched to your task portfolio", "Start with one recurring workflow"))
        results.append(ReadinessToolRecommendation(name=key, fit=fit, use_case=use_case))
        if len(results) >= 5:
            break

    if not results:
        results.append(
            ReadinessToolRecommendation(
                name="ChatGPT",
                fit="General reasoning & drafting",
                use_case="Brainstorming and first drafts",
            )
        )
    return results


def _quick_wins(
    analyses: list[dict[str, Any]],
    improvements: list[ReadinessImprovement],
) -> list[str]:
    wins: list[str] = []
    for row in analyses:
        for action in (row.get("next_actions") or [])[:1]:
            if action and action not in wins:
                wins.append(action)
            if len(wins) >= 3:
                break
        if len(wins) >= 3:
            break

    for imp in improvements:
        if len(wins) >= 5:
            break
        suggestion = f"Improve {imp.title.lower()}"
        if suggestion not in wins:
            wins.append(suggestion)

    defaults = [
        "Automate one repetitive weekly task",
        "Create a BLEND checklist for AI-assisted reviews",
        "Block 30 minutes weekly for AI tool experimentation",
    ]
    for item in defaults:
        if len(wins) >= 5:
            break
        if item not in wins:
            wins.append(item)
    return wins[:5]
