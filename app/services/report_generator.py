"""Assemble Career Intelligence Report sections A–G from assessment artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.schemas.ai_readiness import AIReadinessResponse
from app.schemas.assessment_task_analysis import TaskAnalysisItem, TaskAnalysisRunResponse
from app.schemas.career_intelligence_report import (
    CareerIntelligenceReportResponse,
    ReportActionItem,
    ReportActionPlanSection,
    ReportBeforeAfterSection,
    ReportCareerIdentitySection,
    ReportCareerNode,
    ReportCompetencyGroup,
    ReportCompetencyItem,
    ReportCostRoiSection,
    ReportDailyWorkSection,
    ReportDailyWorkTask,
    ReportIdealRole,
    ReportKpi,
    ReportMarketUrgencySection,
    ReportOverviewSection,
    ReportRoadmapItem,
    ReportRoadmapPhase,
    ReportSnapshotItem,
    ReportTimeSlice,
    ReportToolkitCategory,
    ReportToolkitTool,
    ReportUrgencyBar,
)
from app.services.ai_readiness_scorer import ScorerInput, compute_ai_readiness

REPORT_VERSION = "1.0"

CATEGORY_ICONS: dict[str, str] = {
    "technical": "technical",
    "business": "business",
    "leadership": "leadership",
    "behavioral": "behavioral",
}

LEVEL_SCORES: dict[str, int] = {
    "expert": 90,
    "advanced": 78,
    "intermediate": 62,
    "beginner": 42,
    "foundational": 35,
    "entry": 35,
}

INDUSTRY_URGENCY: dict[str, dict[str, int]] = {
    "technology": {"demand": 82, "risk": 38, "premium": 18, "score": 72},
    "healthcare": {"demand": 68, "risk": 32, "premium": 12, "score": 58},
    "finance": {"demand": 74, "risk": 45, "premium": 15, "score": 65},
    "marketing": {"demand": 79, "risk": 52, "premium": 14, "score": 70},
    "education": {"demand": 55, "risk": 28, "premium": 8, "score": 48},
    "default": {"demand": 65, "risk": 40, "premium": 10, "score": 55},
}

TOOL_CATALOG: dict[str, dict[str, str]] = {
    "chatgpt": {
        "description": "General-purpose reasoning and drafting assistant.",
        "use_cases": "Brainstorming, first drafts, summarization, Q&A.",
        "why": "Fast baseline for daily knowledge work augmentation.",
        "efficiency_gain": "25%",
        "category": "productivity",
    },
    "claude": {
        "description": "Advanced reasoning model with a large context window.",
        "use_cases": "Long documents, analysis, structured writing.",
        "why": "Strong at nuanced reasoning across complex material.",
        "efficiency_gain": "30%",
        "category": "productivity",
    },
    "copilot": {
        "description": "Inline AI assistance inside your existing tools.",
        "use_cases": "Code completion, email drafts, spreadsheet formulas.",
        "why": "Low-friction adoption inside daily workflows.",
        "efficiency_gain": "25%",
        "category": "development",
    },
    "cursor": {
        "description": "AI-native editor for pair-programming style development.",
        "use_cases": "Refactoring, boilerplate, in-context debugging.",
        "why": "Accelerates technical delivery without leaving the IDE.",
        "efficiency_gain": "40%",
        "category": "development",
    },
    "perplexity": {
        "description": "AI-powered research with cited sources.",
        "use_cases": "Tool evaluation, troubleshooting, market scans.",
        "why": "Faster than traditional search for professional research.",
        "efficiency_gain": "35%",
        "category": "productivity",
    },
    "notion ai": {
        "description": "Connected workspace assistant for notes and docs.",
        "use_cases": "Meeting notes, specs, project plans.",
        "why": "Keeps AI output inside your knowledge base.",
        "efficiency_gain": "20%",
        "category": "productivity",
    },
    "zapier": {
        "description": "Workflow automation across business apps.",
        "use_cases": "Triggers, handoffs, repetitive multi-step tasks.",
        "why": "Turns BOT recommendations into repeatable automations.",
        "efficiency_gain": "45%",
        "category": "automation",
    },
    "gamma": {
        "description": "AI presentation and document generator.",
        "use_cases": "Decks, stakeholder updates, visual summaries.",
        "why": "Speeds up communication-heavy BLEND tasks.",
        "efficiency_gain": "50%",
        "category": "productivity",
    },
}

CATEGORY_TITLES: dict[str, str] = {
    "development": "Development Tools",
    "productivity": "Business & Productivity",
    "automation": "Automation & Workflows",
    "general": "Recommended AI Tools",
}


@dataclass
class ReportGeneratorInput:
    assessment_id: UUID
    profile: dict[str, Any]
    tasks: list[dict[str, Any]]
    analyses: list[dict[str, Any]]
    competencies: list[dict[str, Any]]
    profession_summary: str | None = None


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def _growth_label(proficiency: int, importance: str | None) -> str:
    importance_norm = (importance or "Medium").strip()
    if importance_norm == "High" and proficiency < 50:
        return "Critical Focus"
    if proficiency >= 85:
        return "Mastery"
    if proficiency >= 70:
        return "Leverage" if importance_norm == "High" else "Optimize"
    if proficiency >= 55:
        return "Develop" if importance_norm == "High" else "Expand"
    return "Maintain"


def _proficiency_from_competency(comp: dict[str, Any], ai_comfort: int) -> int:
    level = _normalize(comp.get("expected_level"))
    base = 55
    for key, score in LEVEL_SCORES.items():
        if key in level:
            base = score
            break
    name = _normalize(comp.get("name"))
    if any(token in name for token in ("ai", "prompt", "automation", "digital")):
        base = round((base * 0.6) + (ai_comfort * 10 * 0.4))
    return max(20, min(95, base))


def _ai_usage_label(ai_assistance: str | None) -> str:
    normalized = _normalize(ai_assistance)
    if any(token in normalized for token in ("always", "heavy", "frequently", "extensively")):
        return "High"
    if any(token in normalized for token in ("sometimes", "moderate", "light")):
        return "Medium"
    if any(token in normalized for token in ("never", "none", "not")):
        return "None"
    return "Low"


def _parse_salary_midpoint(salary: str | None) -> float | None:
    if not salary:
        return None
    numbers = [float(n.replace(",", "")) for n in re.findall(r"[\d,]+(?:\.\d+)?", salary)]
    if not numbers:
        return None
    if len(numbers) >= 2:
        return (numbers[0] + numbers[1]) / 2
    value = numbers[0]
    if value < 500:
        return value * 1000
    return value


def _tool_key(name: str) -> str:
    return _normalize(name).replace("github ", "").replace("microsoft ", "")


def _lookup_tool(name: str) -> dict[str, str]:
    key = _tool_key(name)
    for catalog_key, meta in TOOL_CATALOG.items():
        if catalog_key in key or key in catalog_key:
            return meta
    return {
        "description": f"AI tool recommended for your workflow: {name}.",
        "use_cases": "Task augmentation, drafting, and workflow support.",
        "why": "Surfaced from your 3B analysis as a strong fit for your tasks.",
        "efficiency_gain": "20%",
        "category": "general",
    }


def _build_readiness(data: ReportGeneratorInput) -> AIReadinessResponse:
    scorer_input = ScorerInput(
        ai_frequency=data.profile.get("ai_frequency") or "",
        ai_tools=list(data.profile.get("ai_tools") or []),
        ai_comfort_level=int(data.profile.get("ai_comfort_level") or 5),
        digital_skills_count=len(data.profile.get("digital_skills") or []),
        tasks=[
            {
                "ai_assistance": task.get("ai_assistance"),
                "confidence_score": task.get("confidence_score") or task.get("confidence"),
            }
            for task in data.tasks
        ],
        analyses=data.analyses,
        competencies=data.competencies,
    )
    return compute_ai_readiness(scorer_input)


def _build_task_routing(data: ReportGeneratorInput) -> TaskAnalysisRunResponse:
    analyses = [
        TaskAnalysisItem(
            task_id=row["task_id"],
            task_title=row.get("task_title") or "",
            task_description=row.get("task_description"),
            task_category=row.get("task_category"),
            category=row.get("category") or "BLEND",
            rationale=row.get("rationale"),
            reason=row.get("reason"),
            next_actions=list(row.get("next_actions") or [])[:3],
            auto_potential=row.get("auto_potential"),
            risk_level=row.get("risk_level"),
            future_impact=row.get("future_impact"),
            recommended_tools=list(row.get("recommended_tools") or []),
        )
        for row in data.analyses
    ]
    confidences = [row.auto_potential for row in analyses if row.auto_potential is not None]
    summary = round(sum(confidences) / len(confidences)) if confidences else None
    return TaskAnalysisRunResponse(analyses=analyses, summary_confidence=summary, regenerated=False)


def _build_competencies(data: ReportGeneratorInput) -> list[ReportCompetencyGroup]:
    grouped: dict[str, list[ReportCompetencyItem]] = {
        "technical": [],
        "business": [],
        "leadership": [],
        "behavioral": [],
    }
    ai_comfort = int(data.profile.get("ai_comfort_level") or 5)
    for comp in data.competencies:
        category = _normalize(comp.get("category"))
        bucket = "behavioral"
        if "tech" in category:
            bucket = "technical"
        elif "business" in category or "domain" in category:
            bucket = "business"
        elif "lead" in category or "manage" in category:
            bucket = "leadership"
        proficiency = _proficiency_from_competency(comp, ai_comfort)
        grouped[bucket].append(
            ReportCompetencyItem(
                name=comp.get("name") or "Competency",
                importance=comp.get("importance"),
                proficiency=proficiency,
                growth=_growth_label(proficiency, comp.get("importance")),
            )
        )

    titles = {
        "technical": "Technical",
        "business": "Business",
        "leadership": "Leadership",
        "behavioral": "Behavioral",
    }
    return [
        ReportCompetencyGroup(title=f"{titles[key]} Competencies", category_key=key, items=items)
        for key, items in grouped.items()
        if items
    ]


def _build_daily_work(data: ReportGeneratorInput) -> ReportDailyWorkSection:
    palette = ["brand", "primary", "accent", "muted"]
    tasks: list[ReportDailyWorkTask] = []
    allocation: dict[str, float] = {}
    total_hours = 0.0

    for task in data.tasks:
        hours = float(task.get("hours_per_week") or 0)
        total_hours += hours
        category = task.get("category") or "General"
        allocation[category] = allocation.get(category, 0) + hours
        confidence = task.get("confidence_score") or task.get("confidence")
        tasks.append(
            ReportDailyWorkTask(
                name=task.get("title") or "Task",
                hours_per_week=hours,
                time_label=f"{hours:g}h",
                criticality=task.get("business_criticality"),
                ai_usage=_ai_usage_label(task.get("ai_assistance")),
                confidence=f"{confidence}%" if confidence is not None else None,
                category_3b=task.get("category_3b"),
            )
        )

    slices: list[ReportTimeSlice] = []
    for idx, (name, value) in enumerate(sorted(allocation.items(), key=lambda item: item[1], reverse=True)):
        slices.append(
            ReportTimeSlice(
                name=name,
                value=round(value, 1),
                color=palette[idx % len(palette)],
            )
        )

    top_category = slices[0].name if slices else "your core responsibilities"
    summary = (
        f"Based on {len(tasks)} confirmed tasks totaling {total_hours:g} hours per week, "
        f"most of your time goes to {top_category}."
    )
    return ReportDailyWorkSection(
        tasks=tasks,
        time_allocation=slices,
        total_hours=round(total_hours, 1),
        summary=summary,
    )


def _automation_pct(readiness: AIReadinessResponse, analyses: list[dict[str, Any]]) -> int | None:
    mix = readiness.portfolio_mix
    total = sum(mix.values())
    if total > 0:
        return round((mix.get("BOT", 0) / total) * 100)
    potentials = [row.get("auto_potential") for row in analyses if row.get("auto_potential") is not None]
    if potentials:
        return round(sum(potentials) / len(potentials))
    return None


def _build_overview(
    data: ReportGeneratorInput,
    readiness: AIReadinessResponse,
    daily_work: ReportDailyWorkSection,
) -> ReportOverviewSection:
    automation = _automation_pct(readiness, data.analyses)
    kpis = [
        ReportKpi(label="Overall Score", value=str(readiness.overall_score), tone="brand"),
        ReportKpi(label="Tasks Analyzed", value=str(len(data.tasks)), tone="primary"),
        ReportKpi(label="Competencies", value=str(len(data.competencies)), tone="primary"),
        ReportKpi(
            label="AI Tools Used",
            value=str(len(data.profile.get("ai_tools") or [])),
            tone="primary",
        ),
        ReportKpi(
            label="Automation %",
            value=f"{automation}%" if automation is not None else "—",
            tone="brand",
        ),
        ReportKpi(label="Career Risk", value=readiness.career_risk, tone="primary"),
    ]
    snapshot = [
        ReportSnapshotItem(label="Current Role", value=data.profile.get("job_title") or "—"),
        ReportSnapshotItem(label="Industry", value=data.profile.get("industry") or "—"),
        ReportSnapshotItem(label="Experience", value=f"{data.profile.get('experience_years', '—')} years"),
        ReportSnapshotItem(label="Domain", value=data.profile.get("domain") or "—"),
        ReportSnapshotItem(label="Weekly Hours", value=f"{daily_work.total_hours:g}h"),
        ReportSnapshotItem(label="AI Comfort", value=f"{data.profile.get('ai_comfort_level', '—')}/10"),
    ]
    return ReportOverviewSection(
        kpis=kpis,
        career_snapshot=snapshot,
        insight=readiness.insight,
    )


def _hours_freed(data: ReportGeneratorInput) -> float:
    freed = 0.0
    for row in data.analyses:
        if (row.get("category") or "").upper() != "BOT":
            continue
        task = next((t for t in data.tasks if t.get("task_id") == row.get("task_id")), None)
        hours = float(task.get("hours_per_week") or 0) if task else 0
        potential = float(row.get("auto_potential") or 50) / 100
        freed += hours * potential * 0.65
    return round(freed, 1)


def _build_before_after(data: ReportGeneratorInput, readiness: AIReadinessResponse) -> ReportBeforeAfterSection:
    job_title = data.profile.get("job_title") or "Professional"
    hours_freed = _hours_freed(data)
    role_future = f"AI-Augmented {job_title}"
    narrative = (
        f"Today you operate as a {job_title} with a {readiness.tier_label.lower()} AI readiness baseline. "
        f"Over the next 12 months, automating BOT tasks and blending AI into high-value work could free "
        f"approximately {hours_freed:g} hours per week for strategic impact."
    )
    shifts = [
        "More time on judgment-heavy BUILD work that differentiates your role.",
        "BOT tasks handled by workflows and AI assistants instead of manual repetition.",
        "BLEND tasks executed as human + AI partnerships with documented playbooks.",
    ]
    return ReportBeforeAfterSection(
        role_today=job_title,
        role_future=role_future,
        hours_freed_per_week=hours_freed,
        narrative=narrative,
        shifts=shifts,
    )


def _build_roadmap(data: ReportGeneratorInput, readiness: AIReadinessResponse) -> list[ReportRoadmapPhase]:
    quick = [
        ReportRoadmapItem(title=item, priority="High", effort="5–10h", impact="High")
        for item in readiness.quick_wins[:3]
    ]
    if not quick and readiness.improvements:
        quick = [
            ReportRoadmapItem(
                title=item.title,
                priority="High",
                effort="10–15h",
                impact=item.impact,
            )
            for item in readiness.improvements[:3]
        ]

    ninety_day: list[ReportRoadmapItem] = []
    for row in data.analyses:
        if (row.get("category") or "").upper() != "BLEND":
            continue
        for action in (row.get("next_actions") or [])[:1]:
            ninety_day.append(
                ReportRoadmapItem(
                    title=action,
                    priority="High",
                    effort="15–25h",
                    impact="High",
                )
            )
        if len(ninety_day) >= 3:
            break

    build_items = [
        comp.get("name")
        for comp in data.competencies
        if _normalize(comp.get("category")).find("tech") >= 0 or _normalize(comp.get("importance")) == "high"
    ][:3]
    twelve_month = [
        ReportRoadmapItem(title=f"Deepen {name}", priority="High", effort="Ongoing", impact="Transformational")
        for name in build_items
    ] or [
        ReportRoadmapItem(
            title="Lead AI-enabled delivery in your function",
            priority="High",
            effort="Ongoing",
            impact="Transformational",
        )
    ]

    return [
        ReportRoadmapPhase(period="Next 30 Days", items=quick[:3] or [ReportRoadmapItem(title="Pilot one AI workflow on a recurring task", priority="High", effort="8h", impact="High")]),
        ReportRoadmapPhase(period="Next 90 Days", items=ninety_day[:3] or quick[:3]),
        ReportRoadmapPhase(period="Next 12 Months", items=twelve_month[:3]),
    ]


def _build_toolkit(data: ReportGeneratorInput, readiness: AIReadinessResponse) -> list[ReportToolkitCategory]:
    seen: set[str] = set()
    buckets: dict[str, list[ReportToolkitTool]] = {}

    def add_tool(name: str, why_override: str | None = None) -> None:
        key = _tool_key(name)
        if key in seen:
            return
        seen.add(key)
        meta = _lookup_tool(name)
        category = meta.get("category", "general")
        buckets.setdefault(category, []).append(
            ReportToolkitTool(
                name=name.strip(),
                description=meta["description"],
                use_cases=meta["use_cases"],
                why=why_override or meta["why"],
                efficiency_gain=meta["efficiency_gain"],
            )
        )

    for row in data.analyses:
        for tool in row.get("recommended_tools") or []:
            add_tool(str(tool), why_override=row.get("rationale"))

    for tool in readiness.recommended_tools[:3]:
        add_tool(tool.name, why_override=tool.fit)

    for tool in data.profile.get("ai_tools") or []:
        add_tool(str(tool))

    if not buckets:
        add_tool("ChatGPT")
        add_tool("Claude")

    return [
        ReportToolkitCategory(
            title=CATEGORY_TITLES.get(key, "Recommended AI Tools"),
            category_key=key,
            tools=tools[:4],
        )
        for key, tools in buckets.items()
    ]


def _build_cost_roi(data: ReportGeneratorInput, hours_saved: float) -> ReportCostRoiSection:
    salary = _parse_salary_midpoint(data.profile.get("salary"))
    ld_investment = 1200.0
    ai_tools_cost = 480.0
    hourly_rate = (salary / 2080) if salary else 45.0
    annual_value = hours_saved * hourly_rate * 52
    total_investment = ld_investment + ai_tools_cost
    payback = round((total_investment / (annual_value / 12)), 1) if annual_value > 0 else None
    roi_summary = (
        f"Investing roughly ${total_investment:,.0f} in learning and AI tools can reclaim "
        f"{hours_saved:g} hours weekly — about ${annual_value:,.0f} in annual capacity at your current level."
    )
    breakdown = [
        ReportSnapshotItem(label="L&D Investment", value=f"${ld_investment:,.0f}"),
        ReportSnapshotItem(label="AI Tools (Annual)", value=f"${ai_tools_cost:,.0f}"),
        ReportSnapshotItem(label="Hours Saved Weekly", value=f"{hours_saved:g}h"),
        ReportSnapshotItem(label="Estimated Annual Value", value=f"${annual_value:,.0f}"),
    ]
    return ReportCostRoiSection(
        annual_salary_estimate=salary,
        ld_investment=ld_investment,
        ai_tools_cost=ai_tools_cost,
        hours_saved_weekly=hours_saved,
        payback_months=payback,
        roi_summary=roi_summary,
        breakdown=breakdown,
    )


def _build_market_urgency(data: ReportGeneratorInput, readiness: AIReadinessResponse) -> ReportMarketUrgencySection:
    industry = _normalize(data.profile.get("industry"))
    benchmark = INDUSTRY_URGENCY["default"]
    for key, values in INDUSTRY_URGENCY.items():
        if key in industry:
            benchmark = values
            break

    risk_adjust = 8 if readiness.tier == "Low" else (-5 if readiness.tier == "High" else 0)
    score = max(20, min(95, benchmark["score"] + risk_adjust))
    bars = [
        ReportUrgencyBar(label="AI Role Demand", value=benchmark["demand"], tone="primary"),
        ReportUrgencyBar(label="Tasks at Risk", value=benchmark["risk"] + risk_adjust, tone="brand"),
        ReportUrgencyBar(label="AI Salary Premium", value=benchmark["premium"], tone="primary"),
        ReportUrgencyBar(label="Overall Urgency", value=score, tone="brand"),
    ]
    summary = (
        f"In {data.profile.get('industry') or 'your industry'}, AI adoption is reshaping roles like "
        f"{data.profile.get('job_title') or 'yours'}. Acting within the next 90 days protects relevance "
        f"while capturing an estimated {benchmark['premium']}% compensation premium for AI-fluent professionals."
    )
    return ReportMarketUrgencySection(
        urgency_score=score,
        demand_pct=benchmark["demand"],
        roles_at_risk_pct=max(10, benchmark["risk"] + risk_adjust),
        salary_premium_pct=benchmark["premium"],
        urgency_bars=bars,
        summary=summary,
    )


def _impact_from_auto(potential: int | None) -> str:
    if potential is None:
        return "Medium"
    if potential >= 75:
        return "High"
    if potential >= 45:
        return "Medium"
    return "Low"


def _build_action_plan(data: ReportGeneratorInput, readiness: AIReadinessResponse) -> ReportActionPlanSection:
    start_doing: list[ReportActionItem] = []
    stop_doing: list[ReportActionItem] = []
    automate: list[ReportActionItem] = []
    learn_next: list[ReportActionItem] = []

    for row in data.analyses:
        category = (row.get("category") or "BLEND").upper()
        actions = list(row.get("next_actions") or [])[:3]
        title = row.get("task_title") or "task"
        potential = row.get("auto_potential")

        if category == "BLEND" and actions:
            start_doing.append(
                ReportActionItem(
                    text=actions[0],
                    priority="High",
                    impact="High",
                    time="2–4h/wk",
                    difficulty="Medium",
                )
            )
        if category == "BOT":
            stop_doing.append(
                ReportActionItem(
                    text=f"Manual repetition on {title.lower()}",
                    priority="High",
                    impact=_impact_from_auto(potential),
                    time="Instant",
                    difficulty="Low",
                )
            )
            automate.append(
                ReportActionItem(
                    text=actions[0] if actions else f"Automate {title.lower()} with recommended AI tools",
                    priority="High",
                    impact="High",
                    time=f"{max(1, round((potential or 50) / 25))}h/wk saved",
                    difficulty="Medium",
                )
            )

    for item in readiness.improvements[:2]:
        learn_next.append(
            ReportActionItem(
                text=item.title,
                priority="High",
                impact=item.impact,
                time="10–20h",
                difficulty=item.difficulty,
            )
        )

    if not start_doing:
        start_doing = [
            ReportActionItem(
                text="Use AI for one recurring weekly deliverable",
                priority="High",
                impact="High",
                time="2h/wk",
                difficulty="Low",
            )
        ]

    return ReportActionPlanSection(
        start_doing=start_doing[:3],
        stop_doing=stop_doing[:3],
        automate_with_ai=automate[:3],
        learn_next=learn_next[:3],
    )


def _build_career_identity(
    data: ReportGeneratorInput,
    readiness: AIReadinessResponse,
) -> ReportCareerIdentitySection:
    job_title = data.profile.get("job_title") or "Professional"
    domain = data.profile.get("domain") or data.profile.get("specialization") or "your field"
    strengths = [item.title for item in readiness.strengths[:4]]
    blind_spots = [item.title for item in readiness.improvements[:4]]
    if not strengths:
        strengths = ["Domain expertise", "Problem solving", "Professional reliability"]
    if not blind_spots:
        blind_spots = ["Advanced AI workflow design", "Cross-team AI change leadership"]

    narrative = (
        data.profession_summary
        or readiness.summary
        or f"You are a capable {job_title} operating in {domain} with room to expand AI-native delivery."
    )
    nodes = [
        ReportCareerNode(label="Current", role=job_title),
        ReportCareerNode(label="Target (Near Term)", role=f"AI-Augmented {job_title}"),
        ReportCareerNode(label="Future (Mid Term)", role=f"Strategic {job_title}"),
    ]
    ideal_roles = [
        ReportIdealRole(
            role=f"AI-Enabled {job_title}",
            reason="Builds on your current scope while integrating AI into daily delivery.",
        ),
        ReportIdealRole(
            role=f"{data.profile.get('business_function') or 'Functional'} Lead",
            reason="Leverages domain depth plus improved AI fluency.",
        ),
        ReportIdealRole(
            role="AI Workflow Architect",
            reason="Natural progression if you automate and blend high-volume tasks successfully.",
        ),
    ]
    closing = (
        "AI is not replacing your career. It is changing how exceptional professionals create value. "
        "Your strongest advantage comes from combining deep domain expertise with intelligent AI collaboration."
    )
    return ReportCareerIdentitySection(
        title=f"AI-Augmented {job_title}",
        subtitle=f"{domain} Specialist",
        narrative=narrative,
        strengths=strengths,
        blind_spots=blind_spots,
        roadmap_nodes=nodes,
        ideal_roles=ideal_roles,
        closing_note=closing,
    )


def _build_strategic_note(
    data: ReportGeneratorInput,
    readiness: AIReadinessResponse,
    before_after: ReportBeforeAfterSection,
) -> str:
    job_title = data.profile.get("job_title") or "professional"
    return (
        f"As a {job_title}, your AI readiness score of {readiness.overall_score}/100 ({readiness.tier_label}) "
        f"signals a clear path forward: automate BOT work, blend AI into daily delivery, and deepen BUILD strengths. "
        f"Executing the recommended actions could free {before_after.hours_freed_per_week:g} hours weekly within 12 months."
    )


def generate_career_intelligence_report(data: ReportGeneratorInput) -> CareerIntelligenceReportResponse:
    readiness = _build_readiness(data)
    task_routing = _build_task_routing(data)
    competencies = _build_competencies(data)
    daily_work = _build_daily_work(data)
    overview = _build_overview(data, readiness, daily_work)
    before_after = _build_before_after(data, readiness)
    upskill_roadmap = _build_roadmap(data, readiness)
    ai_toolkit = _build_toolkit(data, readiness)
    cost_roi = _build_cost_roi(data, before_after.hours_freed_per_week)
    market_urgency = _build_market_urgency(data, readiness)
    action_plan = _build_action_plan(data, readiness)
    career_identity = _build_career_identity(data, readiness)
    strategic_note = _build_strategic_note(data, readiness, before_after)

    return CareerIntelligenceReportResponse(
        assessment_id=data.assessment_id,
        report_version=REPORT_VERSION,
        generated_at=datetime.now(timezone.utc),
        strategic_note=strategic_note,
        overview=overview,
        ai_readiness=readiness,
        task_routing=task_routing,
        before_after=before_after,
        upskill_roadmap=upskill_roadmap,
        ai_toolkit=ai_toolkit,
        cost_roi=cost_roi,
        market_urgency=market_urgency,
        action_plan=action_plan,
        career_identity=career_identity,
        competencies=competencies,
        daily_work=daily_work,
    )
