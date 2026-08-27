"""Server-side derivations for 3B analysis fields."""

from __future__ import annotations

from typing import Any

from app.core.constants import (
    CATEGORY_BUILD,
    CATEGORY_BOT,
    CATEGORY_BLEND,
)
from app.models.assessment_task import AssessmentTask
from app.services.task_hours import annual_hours_from_weekly, effective_task_hours

_FEASIBILITY_PRIORITY = {
    "self_serve": 0,
    "company_tech": 1,
    "org_must_enable": 2,
    "stays_human_led": 3,
}

_IMPORTANCE_MAP = {
    "critical": "Mission Critical",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


def derive_importance(task: AssessmentTask) -> str:
    raw = (task.business_criticality or "").strip().lower()
    if raw in _IMPORTANCE_MAP:
        return _IMPORTANCE_MAP[raw]
    if raw:
        return raw.replace("_", " ").title()
    return "Medium"


def _collect_tool_feasibilities(components: list[dict[str, Any]]) -> list[str]:
    tiers: list[str] = []
    for comp in components:
        if not comp.get("is_automatable"):
            continue
        for tool in comp.get("tools") or []:
            tier = tool.get("feasibility")
            if tier:
                tiers.append(str(tier))
    return tiers


def derive_feasibility(
    category: str,
    components: list[dict[str, Any]],
) -> tuple[str, str]:
    if category == CATEGORY_BUILD:
        return (
            "stays_human_led",
            "The core value of this task stays with you — technology can support around the edges, "
            "but judgment and accountability should remain human-led.",
        )

    tiers = _collect_tool_feasibilities(components)
    if not tiers:
        if category == CATEGORY_BOT:
            return (
                "self_serve",
                "Look for automation you can test yourself first — start with one repetitive step "
                "before asking IT for broader integration.",
            )
        return (
            "self_serve",
            "Identify the mechanical portion you can augment with AI on your own, then expand "
            "once you see time saved.",
        )

    best = min(tiers, key=lambda t: _FEASIBILITY_PRIORITY.get(t, 99))
    notes = {
        "self_serve": (
            "You can likely act on this yourself — pick one tool option and test it on a single "
            "workflow before scaling up."
        ),
        "company_tech": (
            "These options fit licensed tools many employers already provide — confirm what your "
            "organization makes available before adopting."
        ),
        "org_must_enable": (
            "Some options require IT, security review, or purchasing — raise the opportunity with "
            "your manager or IT rather than implementing alone."
        ),
        "stays_human_led": (
            "Technology can assist, but the accountable work should stay with you."
        ),
    }
    return best, notes.get(best, notes["self_serve"])


def enrich_cost_of_staying_as_is(
    cost_raw: dict[str, Any] | None,
    *,
    weekly_hours: float,
) -> dict[str, Any] | None:
    if not cost_raw or not isinstance(cost_raw, dict):
        return None
    narrative = str(cost_raw.get("narrative") or "").strip()
    if not narrative:
        return None
    cost_type = str(cost_raw.get("type") or "reclaimable_time").strip()
    return {
        "type": cost_type,
        "narrative": narrative,
        "annual_hours": round(annual_hours_from_weekly(weekly_hours), 1),
    }


def merge_market_reality(ai_result: dict[str, Any]) -> dict[str, Any]:
    market = ai_result.get("market_reality")
    if not isinstance(market, dict):
        market = {}
    pivot = market.get("pivot_roles")
    if not pivot and ai_result.get("pivot_roles"):
        pivot = ai_result["pivot_roles"]
    trend = str(market.get("trend_text") or "").strip()
    roles = pivot if isinstance(pivot, list) else []
    if not trend and not roles:
        return {}
    return {"trend_text": trend, "pivot_roles": roles}


def recommended_build_task_id(
    rows: list[Any],
    *,
    task_for_row,
) -> str | None:
    """Return task_id of top BUILD task by weekly_hours × importance weight."""
    best_id: str | None = None
    best_score = -1.0
    weight = {"Mission Critical": 4, "High": 3, "Medium": 2, "Low": 1}

    for row in rows:
        if row.category != CATEGORY_BUILD:
            continue
        task = task_for_row(row)
        if not task:
            continue
        hrs = effective_task_hours(task)
        imp = derive_importance(task)
        score = hrs * weight.get(imp, 2)
        if score > best_score:
            best_score = score
            best_id = str(row.task_id)
    return best_id
