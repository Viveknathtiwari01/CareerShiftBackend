"""Validate, sanitize, and enforce UNVERIFIED tool suggestions from 3B LLM output."""

from __future__ import annotations

import re
from typing import Any

from app.core.constants import (
    CATEGORY_BLEND,
    CATEGORY_BOT,
    CATEGORY_BUILD,
    COST_BANDS,
    FEASIBILITY_TIERS,
    VERIFICATION_UNVERIFIED,
    VALID_3B_CATEGORIES,
)
from app.schemas.assessment_task_analysis import (
    ToolOptionSchema,
    WorkComponentSchema,
)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_text(value: str | None, max_len: int) -> str:
    if not value:
        return ""
    text = _CONTROL_CHARS.sub("", str(value)).strip()
    return text[:max_len]


def _normalize_cost_band(value: str | None) -> str:
    if not value:
        return "paid_individual"
    normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "free": "free",
        "freemium": "freemium",
        "paid_individual": "paid_individual",
        "paid_team": "paid_team",
        "enterprise": "enterprise",
        "professional": "paid_individual",
        "paid": "paid_individual",
        "team": "paid_team",
    }
    for key, mapped in aliases.items():
        if normalized == key or normalized.endswith(key):
            return mapped if mapped in COST_BANDS else "paid_individual"
    return normalized if normalized in COST_BANDS else "paid_individual"


def _normalize_feasibility(value: str | None) -> str:
    if not value:
        return "self_serve"
    raw = str(value).strip().lower()
    aliases = {
        "self_serve": "self_serve",
        "self serve": "self_serve",
        "company_tech": "company_tech",
        "company tech": "company_tech",
        "org_must_enable": "org_must_enable",
        "org must enable": "org_must_enable",
        "stays_human_led": "stays_human_led",
        "stays human-led": "stays_human_led",
        "stays human led": "stays_human_led",
    }
    for alias, mapped in aliases.items():
        if raw == alias:
            return mapped
    snake = raw.replace(" ", "_").replace("-", "_")
    return snake if snake in FEASIBILITY_TIERS else "self_serve"


def _normalize_category(value: str | None) -> str:
    if not value:
        return CATEGORY_BLEND
    upper = str(value).upper().strip()
    if upper in VALID_3B_CATEGORIES:
        return upper
    if upper == CATEGORY_BUILD or upper.startswith("BUILD"):
        return CATEGORY_BUILD
    if upper == CATEGORY_BOT or (upper.startswith("BOT") and upper != CATEGORY_BLEND):
        return CATEGORY_BOT
    if upper == CATEGORY_BLEND or "BLEND" in upper:
        return CATEGORY_BLEND
    return CATEGORY_BLEND


def _normalize_level(value: str | None, default: str = "Medium") -> str:
    if not value:
        return default
    normalized = str(value).strip().capitalize()
    return normalized if normalized in {"Low", "Medium", "High"} else default


def _sanitize_tool_option(raw: dict[str, Any]) -> dict[str, Any] | None:
    name = _sanitize_text(raw.get("name"), 120)
    if not name:
        return None
    pros = [
        _sanitize_text(p, 200)
        for p in (raw.get("pros") or [])
        if _sanitize_text(p, 200)
    ][:4]
    cons = [
        _sanitize_text(c, 200)
        for c in (raw.get("cons") or [])
        if _sanitize_text(c, 200)
    ][:4]
    if isinstance(raw.get("pros"), str) and not pros:
        pros = [_sanitize_text(raw.get("pros"), 200)]
    if isinstance(raw.get("cons"), str) and not cons:
        cons = [_sanitize_text(raw.get("cons"), 200)]

    return {
        "name": name,
        "cost_band": _normalize_cost_band(raw.get("cost_band") or raw.get("cost_tier")),
        "pros": pros,
        "cons": cons,
        "credibility_note": _sanitize_text(raw.get("credibility_note"), 500),
        "feasibility": _normalize_feasibility(raw.get("feasibility")),
        "verification_status": VERIFICATION_UNVERIFIED,
        "verified_at": None,
        "verified_by": None,
    }


def _enforce_tool_mix(tools: list[dict[str, Any]], *, is_automatable: bool) -> list[dict[str, Any]]:
    """Cap tool count; free+paid mix is enforced via LLM prompt."""
    _ = is_automatable
    return tools[:4]


def _sanitize_component(raw: dict[str, Any]) -> dict[str, Any] | None:
    name = _sanitize_text(raw.get("name"), 200)
    if not name:
        return None
    tools_raw = raw.get("tools") or raw.get("tool_options") or []
    tools: list[dict[str, Any]] = []
    if isinstance(tools_raw, list):
        for item in tools_raw[:4]:
            if isinstance(item, dict):
                tool = _sanitize_tool_option(item)
                if tool:
                    tools.append(tool)

    is_automatable = bool(raw.get("is_automatable", False))
    tools = _enforce_tool_mix(tools, is_automatable=is_automatable)

    return {
        "name": name,
        "description": _sanitize_text(raw.get("description"), 1000),
        "is_automatable": is_automatable,
        "capability": _sanitize_text(raw.get("capability"), 300),
        "solution_pattern": _sanitize_text(raw.get("solution_pattern"), 300),
        "tools": tools,
    }


def sanitize_llm_analyses(raw_analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize LLM output without catalog; enforce verification and caps."""
    normalized: list[dict[str, Any]] = []
    for item in raw_analyses:
        if not isinstance(item, dict):
            continue

        actions = item.get("next_actions") or []
        if isinstance(actions, list):
            actions = [str(a).strip() for a in actions if str(a).strip()][:3]
        while len(actions) < 3:
            actions.append("Review how this task fits your weekly priorities.")

        auto_potential = item.get("auto_potential")
        try:
            auto_potential = max(0, min(100, int(auto_potential))) if auto_potential is not None else None
        except (TypeError, ValueError):
            auto_potential = None

        components: list[dict[str, Any]] = []
        raw_components = item.get("components") or []
        if isinstance(raw_components, list):
            for comp in raw_components[:4]:
                if isinstance(comp, dict):
                    sanitized = _sanitize_component(comp)
                    if sanitized:
                        components.append(sanitized)

        recommended_tools: list[str] = []
        for comp in components:
            for tool in comp.get("tools") or []:
                name = tool.get("name")
                if name and name not in recommended_tools:
                    recommended_tools.append(name)

        normalized.append(
            {
                "task_index": int(item.get("task_index", 0)),
                "category": _normalize_category(item.get("category")),
                "rationale": _sanitize_text(item.get("rationale"), 500) or None,
                "reason": _sanitize_text(item.get("reason"), 2000) or None,
                "next_actions": actions,
                "auto_potential": auto_potential,
                "risk_level": _normalize_level(item.get("risk_level")),
                "future_impact": _normalize_level(item.get("future_impact")),
                "recommended_tools": recommended_tools,
                "components": components,
            }
        )
    return normalized


def validate_analyses_with_pydantic(analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Optional strict validation via Pydantic models after sanitization."""
    validated: list[dict[str, Any]] = []
    for item in analyses:
        components = []
        for comp in item.get("components") or []:
            tools = [ToolOptionSchema.model_validate(t) for t in comp.get("tools") or []]
            components.append(
                WorkComponentSchema(
                    name=comp["name"],
                    description=comp.get("description") or "",
                    is_automatable=comp.get("is_automatable", False),
                    capability=comp.get("capability") or "",
                    solution_pattern=comp.get("solution_pattern") or "",
                    tools=tools,
                )
            )
        item_copy = dict(item)
        item_copy["components"] = [c.model_dump() for c in components]
        validated.append(item_copy)
    return validated
