"""Build user-centric grounding payload for 3B analysis."""

from __future__ import annotations

from typing import Any

from app.models.assessment_task import AssessmentTask
from app.models.profile import UserProfile


def _compact_competency(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": item.get("name"),
        "category": item.get("category"),
        "importance": item.get("importance"),
        "expected_level": item.get("expected_level"),
        "what_it_is": item.get("what_it_is"),
        "why_it_matters": item.get("why_it_matters"),
        "professional_context": item.get("professional_context"),
    }


def build_profile_grounding(profile: UserProfile) -> dict[str, Any]:
    """Identity + experience only — no skills or AI fields."""
    return {
        "job_title": profile.job_title,
        "industry": profile.industry,
        "business_function": profile.business_function,
        "domain": profile.domain,
        "specialization": profile.specialization,
        "experience_years": profile.experience_years,
    }


def _level_score(value: str | None, *, high_values: set[str]) -> float:
    if not value:
        return 0.5
    normalized = str(value).strip().lower()
    if normalized in high_values:
        return 1.0
    if normalized in {"medium", "moderate", "sometimes", "occasionally"}:
        return 0.5
    return 0.0


def _classification_signals(task: AssessmentTask) -> dict[str, Any]:
    """Server-computed hints to nudge LLM classification — not decisions."""
    repetition = (
        _level_score(task.frequency, high_values={"daily", "weekly", "very_high", "high"})
        + _level_score(task.creativity, high_values={"low", "minimal"})
        + _level_score(str(task.ai_assistance or ""), high_values={"high", "very_high", "extensive"})
    ) / 3.0
    if task.time_allocation and task.time_allocation >= 0.3:
        repetition = min(1.0, repetition + 0.2)

    judgment = (
        _level_score(task.human_touch, high_values={"high", "very_high", "critical"})
        + _level_score(task.business_criticality, high_values={"critical", "high"})
        + (1.0 - _level_score(str(task.ai_assistance or ""), high_values={"high", "very_high", "extensive"}))
    ) / 3.0
    if task.confidence_score is not None and task.confidence_score >= 70:
        judgment = min(1.0, judgment + 0.15)

    return {
        "repetition_signal": round(repetition, 2),
        "judgment_signal": round(judgment, 2),
        "hours_per_week": task.hours_per_week,
        "confidence_score": task.confidence_score,
        "business_criticality": task.business_criticality,
    }


def build_task_grounding(task: AssessmentTask) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "source": task.source,
        "hours_per_week": task.hours_per_week,
        "complexity": task.complexity,
        "creativity": task.creativity,
        "human_touch": task.human_touch,
        "frequency": task.frequency,
        "business_criticality": task.business_criticality,
        "time_allocation": task.time_allocation,
        "ai_assistance": task.ai_assistance,
        "confidence_score": task.confidence_score,
        "classification_signals": _classification_signals(task),
    }
    if task.manual_notes and str(task.manual_notes).strip():
        payload["manual_notes"] = str(task.manual_notes).strip()
    return payload


def build_3b_grounding_payload(
    profile: UserProfile,
    competency_final_output: dict[str, Any] | None,
    selected_tasks: list[AssessmentTask],
) -> dict[str, Any]:
    competencies_raw = []
    profession_summary = None
    if competency_final_output:
        profession_summary = competency_final_output.get("profession_summary")
        for item in competency_final_output.get("competencies") or []:
            if isinstance(item, dict):
                competencies_raw.append(_compact_competency(item))

    return {
        "user_profile": build_profile_grounding(profile),
        "career_assessment": {
            "profession_summary": profession_summary,
            "competencies": competencies_raw,
        },
        "reviewed_tasks": [build_task_grounding(t) for t in selected_tasks],
    }
