from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.services.ai_readiness_scorer import ReadinessInput, compute_ai_readiness

REPORT_VERSION = "1.0.0"


@dataclass
class ReportGeneratorInput:
    assessment_id: UUID
    profile: dict
    profession_summary: str | None
    competencies: list[dict]
    tasks: list[dict]
    analyses: list[dict]
    toolkit: list[dict] | None = None


def _risk_from_bot_pct(bot_pct: float) -> str:
    if bot_pct >= 0.45:
        return "High"
    if bot_pct >= 0.25:
        return "Medium"
    return "Low"


def _group_competencies(competencies: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in competencies:
        category = item.get("category") or "General"
        grouped[category].append(
            {
                "name": item.get("name"),
                "importance": item.get("importance"),
                "expected_level": item.get("expected_level"),
                "what_it_is": item.get("what_it_is"),
                "why_it_matters": item.get("why_it_matters"),
            }
        )
    return [{"category": cat, "items": items} for cat, items in grouped.items()]


_IMPACT_SCORE = {"High": 3, "Medium": 2, "Low": 1}
_RISK_SCORE = {"High": 3, "Medium": 2, "Low": 1}
_CATEGORY_SCORE = {"BOT": 3, "BLEND": 2, "BUILD": 1}


def _level_score(value: str | None, mapping: dict[str, int]) -> int:
    return mapping.get(str(value or "Medium").capitalize(), 2)


def _collect_tool_task_entries(analyses_or_routing: list[dict]) -> dict[str, list[dict]]:
    tool_entries: dict[str, list[dict]] = {}
    for row in analyses_or_routing:
        task_title = (row.get("task_title") or "").strip()
        for tool in row.get("recommended_tools") or []:
            if not tool:
                continue
            entries = tool_entries.setdefault(tool, [])
            if any(entry.get("task_title") == task_title for entry in entries):
                continue
            entries.append(
                {
                    "task_title": task_title,
                    "reason": row.get("reason"),
                    "rationale": row.get("rationale"),
                    "category": row.get("category"),
                    "future_impact": row.get("future_impact"),
                    "auto_potential": row.get("auto_potential"),
                    "risk_level": row.get("risk_level"),
                }
            )
    return tool_entries


def _tool_reason_from_task_entries(entries: list[dict]) -> str:
    if not entries:
        return "Recommended based on your 3B task analysis."

    parts: list[str] = []
    for entry in entries[:3]:
        task_title = entry.get("task_title") or ""
        reason = (entry.get("reason") or entry.get("rationale") or "").strip()
        category = entry.get("category") or ""

        if reason:
            parts.append(f"{task_title}: {reason}" if task_title else reason)
        elif task_title and category:
            parts.append(
                f'Recommended for "{task_title}" ({category}) based on your 3B task classification.'
            )
        elif task_title:
            parts.append(f'Recommended for "{task_title}" based on your 3B task classification.')

    if not parts:
        return "Recommended based on your 3B task analysis."

    result = " ".join(parts)
    if len(entries) > 3:
        result += f" Also applies to {len(entries) - 3} additional task(s)."
    return result


def _tool_priority_score(entries: list[dict]) -> int:
    score = 0
    for entry in entries:
        impact = _level_score(entry.get("future_impact"), _IMPACT_SCORE)
        risk = _level_score(entry.get("risk_level"), _RISK_SCORE)
        category = _CATEGORY_SCORE.get(str(entry.get("category") or "BLEND").upper(), 2)
        auto = int(entry.get("auto_potential") or 50)
        score += impact * 12 + risk * 6 + category * 5 + auto // 5
    score += len(entries) * 10
    return score


def _priority_label(rank: int) -> str:
    if rank == 1:
        return "Critical"
    if rank <= 3:
        return "High"
    if rank <= 6:
        return "Medium"
    return "Supporting"


def _priority_reason_from_entries(entries: list[dict], rank: int) -> str:
    if not entries:
        return "Recommended based on impact across your assessed responsibilities."

    bot_count = sum(1 for entry in entries if str(entry.get("category") or "").upper() == "BOT")
    high_impact = sum(
        1 for entry in entries if str(entry.get("future_impact") or "").capitalize() == "High"
    )
    avg_auto = sum(int(entry.get("auto_potential") or 0) for entry in entries) / len(entries)
    task_count = len(entries)

    details: list[str] = []
    if task_count > 1:
        details.append(f"recommended across {task_count} of your core tasks")
    if bot_count:
        details.append(
            f"linked to {bot_count} automatable (BOT) task{'s' if bot_count > 1 else ''}"
        )
    if high_impact:
        details.append(
            f"supports {high_impact} high future-impact responsibilit{'ies' if high_impact > 1 else 'y'}"
        )
    if avg_auto >= 60:
        details.append("strong automation ROI for your role trajectory")

    if rank == 1:
        lead = "Highest priority for your career shift"
    elif rank <= 3:
        lead = "High priority for near-term impact"
    elif rank <= 6:
        lead = "Medium priority — adopt after top tools"
    else:
        lead = "Supporting tool for specific workflows"

    if not details:
        return f"{lead}."
    return f"{lead}: {', '.join(details)}."


def _build_toolkit_item(
    name: str,
    *,
    entries: list[dict],
    rank: int,
    category: str = "Recommended",
    source: str = "3B Analysis",
) -> dict:
    return {
        "name": name,
        "category": category,
        "use_case": _tool_reason_from_task_entries(entries),
        "source": source,
        "priority_rank": rank,
        "priority_label": _priority_label(rank),
        "priority_reason": _priority_reason_from_entries(entries, rank),
    }


def ensure_toolkit_priorities(tools: list[dict], analyses_or_routing: list[dict]) -> list[dict]:
    if not tools:
        return tools

    entries_by_tool = _collect_tool_task_entries(analyses_or_routing)
    ranked_3b: list[tuple[dict, int]] = []
    profile_tools: list[dict] = []

    for tool in tools:
        if tool.get("source") == "Profile" and tool.get("name") not in entries_by_tool:
            profile_tools.append(dict(tool))
            continue
        name = tool.get("name") or ""
        entries = entries_by_tool.get(name, [])
        ranked_3b.append((dict(tool), _tool_priority_score(entries)))

    ranked_3b.sort(key=lambda item: (-item[1], item[0].get("name", "")))

    result: list[dict] = []
    for rank, (tool, _score) in enumerate(ranked_3b, start=1):
        name = tool.get("name") or ""
        entries = entries_by_tool.get(name, [])
        item = _build_toolkit_item(name, entries=entries, rank=rank)
        item["category"] = tool.get("category") or item["category"]
        item["source"] = tool.get("source") or item["source"]
        if tool.get("use_case"):
            item["use_case"] = tool["use_case"]
        result.append(item)

    start_rank = len(result) + 1
    for offset, tool in enumerate(profile_tools):
        rank = start_rank + offset
        result.append(
            {
                **tool,
                "priority_rank": rank,
                "priority_label": "Existing",
                "priority_reason": (
                    tool.get("priority_reason")
                    or "Already in your profile — keep building on familiar tools as you expand AI workflows."
                ),
            }
        )

    return result


def needs_toolkit_priority_backfill(tools: list[dict]) -> bool:
    return bool(tools) and any(tool.get("priority_rank") is None for tool in tools)


def enrich_ai_toolkit(tools: list[dict], task_routing: list[dict]) -> list[dict]:
    if not tools or not task_routing:
        return tools

    entries_by_tool = _collect_tool_task_entries(task_routing)
    enriched: list[dict] = []
    for tool in tools:
        item = dict(tool)
        name = item.get("name") or ""
        task_entries = entries_by_tool.get(name, [])
        if task_entries:
            item["use_case"] = _tool_reason_from_task_entries(task_entries)
        enriched.append(item)
    return enriched


def needs_legacy_toolkit_enrichment(tools: list[dict]) -> bool:
    return any("Mentioned in" in (tool.get("use_case") or "") for tool in tools)


def build_toolkit_from_analyses(analyses: list[dict]) -> list[dict]:
    return _aggregate_tools(analyses)


def analysis_dicts_from_rows(
    rows: list,
    *,
    task_title_for,
) -> list[dict]:
    return [
        {
            "task_id": str(row.task_id),
            "task_title": task_title_for(row),
            "category": row.category,
            "rationale": row.rationale,
            "reason": row.reason,
            "future_impact": row.future_impact,
            "auto_potential": row.auto_potential,
            "risk_level": row.risk_level,
            "recommended_tools": list(row.recommended_tools or []),
        }
        for row in rows
    ]


def _aggregate_tools(analyses: list[dict]) -> list[dict]:
    entries_by_tool = _collect_tool_task_entries(analyses)
    scored = [
        (name, entries, _tool_priority_score(entries))
        for name, entries in entries_by_tool.items()
    ]
    scored.sort(key=lambda item: (-item[2], item[0]))
    return [
        _build_toolkit_item(name, entries=entries, rank=rank)
        for rank, (name, entries, _score) in enumerate(scored[:12], start=1)
    ]


def generate_career_intelligence_report(data: ReportGeneratorInput) -> dict:
    profile = data.profile
    selected_tasks = [t for t in data.tasks if t.get("selected", True)]
    analyses = data.analyses

    build_count = sum(1 for a in analyses if a.get("category") == "BUILD")
    bot_count = sum(1 for a in analyses if a.get("category") == "BOT")
    blend_count = sum(1 for a in analyses if a.get("category") == "BLEND")
    task_count = max(len(analyses), len(selected_tasks), 1)

    auto_potentials = [a.get("auto_potential") for a in analyses if a.get("auto_potential") is not None]
    avg_auto = sum(auto_potentials) / len(auto_potentials) if auto_potentials else None

    readiness = compute_ai_readiness(
        ReadinessInput(
            ai_frequency=profile.get("ai_frequency") or "Never",
            ai_tools=profile.get("ai_tools") or [],
            ai_comfort_level=int(profile.get("ai_comfort_level") or 5),
            task_ai_assistance=[t.get("ai_assistance") or "Never" for t in selected_tasks],
            build_count=build_count,
            bot_count=bot_count,
            blend_count=blend_count,
            task_count=task_count,
            avg_auto_potential=avg_auto,
        )
    )

    bot_pct = bot_count / task_count
    automation_pct = round(bot_pct * 100)
    career_risk = _risk_from_bot_pct(bot_pct)

    job_title = profile.get("job_title") or "Professional"
    industry = profile.get("industry") or "General"
    experience_years = int(profile.get("experience_years") or 0)

    overview = {
        "overall_score": readiness.overall_score,
        "tasks_analyzed": len(analyses) or len(selected_tasks),
        "competency_count": len(data.competencies),
        "ai_tools_count": len(profile.get("ai_tools") or []),
        "automation_pct": automation_pct,
        "career_risk": career_risk,
        "job_title": job_title,
        "industry": industry,
        "experience_years": experience_years,
        "profession_summary": data.profession_summary,
        "reading_time_minutes": max(8, min(20, 6 + len(analyses) // 2)),
    }

    ai_readiness_json = {
        "overall_score": readiness.overall_score,
        "tier_label": readiness.tier_label,
        "tier_description": readiness.tier_description,
        "dimensions": [{"name": d.name, "score": d.score} for d in readiness.dimensions],
        "strengths": readiness.strengths,
        "improvement_areas": readiness.improvement_areas,
        "factors": readiness.factors,
    }

    daily_work_tasks = [
        {
            "title": t.get("title"),
            "hours_per_week": float(t.get("hours_per_week") or 0),
            "category": t.get("category"),
            "complexity": t.get("complexity") or "medium",
            "ai_assistance": t.get("ai_assistance"),
        }
        for t in selected_tasks
    ]
    total_hours = sum(t["hours_per_week"] for t in daily_work_tasks) or 40.0

    task_routing = [
        {
            "task_id": str(a.get("task_id")),
            "task_title": a.get("task_title") or "",
            "category": a.get("category"),
            "rationale": a.get("rationale"),
            "reason": a.get("reason"),
            "next_actions": a.get("next_actions") or [],
            "auto_potential": a.get("auto_potential"),
            "risk_level": a.get("risk_level"),
            "future_impact": a.get("future_impact"),
            "recommended_tools": a.get("recommended_tools") or [],
        }
        for a in analyses
    ]

    identity_title = f"AI-Augmented {job_title}"
    career_identity = {
        "identity_title": identity_title,
        "confidence_pct": min(98, max(55, readiness.overall_score + 10)),
        "executive_summary": (
            f"Your profile as a {job_title} in {industry} shows {readiness.tier_label.lower()} AI readiness "
            f"({readiness.overall_score}/100). {readiness.tier_description}"
        ),
        "ideal_roles": [
            f"AI-Augmented {job_title}",
            f"Senior {job_title}",
            f"{profile.get('business_function') or 'Cross-functional'} AI Lead",
        ],
        "superpowers": readiness.strengths[:3],
        "blind_spots": readiness.improvement_areas[:3],
        "growth_strategy": (
            "Focus on deepening BUILD tasks while piloting AI workflows on BLEND tasks. "
            "Automate repetitive BOT work to free time for high-judgment responsibilities."
        ),
    }

    roadmap = [
        {
            "horizon": "30 days",
            "title": "Quick wins",
            "items": [
                action
                for a in analyses[:3]
                for action in (a.get("next_actions") or [])[:1]
            ][:4]
            or ["Document your top 3 weekly tasks and identify one BOT candidate"],
        },
        {
            "horizon": "90 days",
            "title": "Capability building",
            "items": readiness.improvement_areas[:4],
        },
        {
            "horizon": "365 days",
            "title": "Career positioning",
            "items": [
                f"Position as {identity_title}",
                "Lead an AI workflow pilot in your team",
                "Build a portfolio of AI-augmented outcomes",
            ],
        },
    ]

    toolkit = list(data.toolkit) if data.toolkit else _aggregate_tools(analyses)
    if not toolkit and profile.get("ai_tools"):
        toolkit = [
            {
                "name": tool,
                "category": "Profile",
                "use_case": "Listed in your assessment profile as a tool you already use.",
                "source": "Profile",
                "priority_rank": index,
                "priority_label": "Existing",
                "priority_reason": (
                    "Already in your profile — continue building on familiar tools as you expand AI workflows."
                ),
            }
            for index, tool in enumerate(profile.get("ai_tools", [])[:8], start=1)
        ]

    automate_actions = [
        f"Automate: {a.get('task_title')}"
        for a in analyses
        if a.get("category") == "BOT"
    ][:4]
    learn_actions = [
        action
        for a in analyses
        if a.get("category") == "BUILD"
        for action in (a.get("next_actions") or [])[:1]
    ][:4]

    action_plan = {
        "start": readiness.strengths[:3],
        "stop": ["Manual rework on tasks already classified as BOT"] if bot_count else [],
        "automate": automate_actions,
        "learn": learn_actions or readiness.improvement_areas[:3],
    }

    strategic_note = (
        f"{job_title} in {industry}: AI readiness {readiness.overall_score}/100 ({readiness.tier_label}). "
        f"{bot_count} BOT, {blend_count} BLEND, {build_count} BUILD tasks analyzed. "
        f"Prioritize {readiness.improvement_areas[0].lower() if readiness.improvement_areas else 'targeted upskilling'}."
    )

    now = datetime.now(timezone.utc)

    return {
        "assessment_id": str(data.assessment_id),
        "report_version": REPORT_VERSION,
        "generated_at": now.isoformat(),
        "strategic_note": strategic_note,
        "overview": overview,
        "ai_readiness": ai_readiness_json,
        "competencies": _group_competencies(data.competencies),
        "daily_work": {"tasks": daily_work_tasks, "total_hours_per_week": total_hours},
        "task_routing": task_routing,
        "career_identity": career_identity,
        "learning_roadmap": roadmap,
        "ai_toolkit": toolkit,
        "action_plan": action_plan,
        "before_after": {
            "current_role": job_title,
            "future_role": identity_title,
            "shift_summary": strategic_note,
        },
        "cost_roi": {
            "hours_automatable_per_week": round(
                sum(
                    float(t.get("hours_per_week") or 0)
                    for t, a in zip(selected_tasks, analyses)
                    if a.get("category") == "BOT"
                ),
                1,
            ),
            "note": "Estimated from BOT-classified task hours",
        },
        "market_urgency": {
            "risk_level": career_risk,
            "automation_pct": automation_pct,
            "message": f"{career_risk} displacement exposure based on current task mix",
        },
        "_persist": {
            "ai_readiness_json": ai_readiness_json,
            "task_routing_json": {"items": task_routing, "daily_tasks": daily_work_tasks},
            "before_after_json": {
                "current_role": job_title,
                "future_role": identity_title,
                "shift_summary": strategic_note,
            },
            "upskill_roadmap_json": {"phases": roadmap},
            "ai_toolkit_json": {"tools": toolkit},
            "cost_roi_json": {
                "hours_automatable_per_week": round(
                    sum(
                        float(t.get("hours_per_week") or 0)
                        for t, a in zip(selected_tasks, analyses)
                        if a.get("category") == "BOT"
                    ),
                    1,
                ),
                "note": "Estimated from BOT-classified task hours",
            },
            "market_urgency_json": {"risk_level": career_risk, "automation_pct": automation_pct},
            "overview_json": {
                **overview,
                "competency_groups": _group_competencies(data.competencies),
                "total_hours_per_week": total_hours,
            },
            "career_identity_json": career_identity,
            "action_plan_json": action_plan,
            "strategic_note": strategic_note,
            "report_version": REPORT_VERSION,
            "generated_at": now,
        },
    }
