"""Shared weekly/annual hour calculations for tasks and 3B summaries."""

from __future__ import annotations

from typing import Any

from app.core.constants import CATEGORY_BUILD, CATEGORY_BLEND, CATEGORY_BOT

# Review UI buckets (assessment_tasks.time_allocation) → weekly hours.
REVIEW_TIME_TO_WEEKLY_HOURS: dict[float, float] = {
    0.25: 1.0,
    0.5: 2.0,
    1.0: 4.0,
    2.0: 4.0,
    4.0: 8.0,
    8.0: 10.0,
}

HOURS_PER_YEAR = 52


def effective_task_hours(task: dict[str, Any] | Any) -> float:
    """Prefer reviewed time_allocation (mapped to weekly hours); else AI hours_per_week."""
    if isinstance(task, dict):
        time_allocation = task.get("time_allocation")
        hours_per_week = task.get("hours_per_week")
    else:
        time_allocation = getattr(task, "time_allocation", None)
        hours_per_week = getattr(task, "hours_per_week", None)

    if time_allocation is not None:
        raw = float(time_allocation or 0)
        for bucket, weekly in REVIEW_TIME_TO_WEEKLY_HOURS.items():
            if abs(raw - bucket) < 1e-9:
                return weekly
        return raw
    return float(hours_per_week or 0)


def annual_hours_from_weekly(weekly_hours: float) -> float:
    return round(weekly_hours * HOURS_PER_YEAR, 1)


def task_to_hours_dict(task: dict[str, Any] | Any) -> dict[str, float]:
    weekly = effective_task_hours(task)
    return {
        "weekly_hours": round(weekly, 1),
        "annual_hours": annual_hours_from_weekly(weekly),
    }


def _normalize_category_key(category: str | None) -> str:
    upper = (category or "").upper()
    if "BUILD" in upper:
        return CATEGORY_BUILD
    if "BOT" in upper:
        return CATEGORY_BOT
    return CATEGORY_BLEND


def compute_hours_summary(
    tasks_with_categories: list[tuple[Any, str | None]],
) -> dict[str, Any]:
    """
    Aggregate weekly and annual hours by BUILD / BLEND / BOT.

    Each item is (task, category) where task is a model or dict with time fields.
    """
    buckets: dict[str, dict[str, float | int]] = {
        CATEGORY_BUILD: {"weekly_hours": 0.0, "annual_hours": 0.0, "task_count": 0},
        CATEGORY_BLEND: {"weekly_hours": 0.0, "annual_hours": 0.0, "task_count": 0},
        CATEGORY_BOT: {"weekly_hours": 0.0, "annual_hours": 0.0, "task_count": 0},
    }
    total_weekly = 0.0

    for task, category in tasks_with_categories:
        weekly = effective_task_hours(task)
        annual = annual_hours_from_weekly(weekly)
        key = _normalize_category_key(category)
        bucket = buckets[key]
        bucket["weekly_hours"] = round(float(bucket["weekly_hours"]) + weekly, 1)
        bucket["annual_hours"] = round(float(bucket["annual_hours"]) + annual, 1)
        bucket["task_count"] = int(bucket["task_count"]) + 1
        total_weekly += weekly

    total_annual = annual_hours_from_weekly(total_weekly)
    return {
        "BUILD": buckets[CATEGORY_BUILD],
        "BLEND": buckets[CATEGORY_BLEND],
        "BOT": buckets[CATEGORY_BOT],
        "total": {
            "weekly_hours": round(total_weekly, 1),
            "annual_hours": total_annual,
            "task_count": sum(int(b["task_count"]) for b in buckets.values()),
        },
    }
