from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.core.config import settings
from app.services.report_generator import enrich_ai_toolkit, ensure_toolkit_priorities, needs_legacy_toolkit_enrichment, needs_toolkit_priority_backfill
from app.schemas.career_intelligence_report import CareerIntelligenceReportResponse
from app.schemas.report_export import ReportScorecardResponse

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "export"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _category_counts(task_routing: list) -> dict[str, int]:
    counts = {"BUILD": 0, "BLEND": 0, "BOT": 0}
    for item in task_routing:
        cat = (item.category if hasattr(item, "category") else item.get("category", "")).upper()
        if cat in counts:
            counts[cat] += 1
    return counts


def build_export_context(
    report: CareerIntelligenceReportResponse,
    *,
    recipient_name: str,
) -> dict:
    payload = report.model_dump(mode="json")
    counts = _category_counts(report.task_routing)
    ai_toolkit = payload["ai_toolkit"]
    if needs_legacy_toolkit_enrichment(ai_toolkit):
        ai_toolkit = enrich_ai_toolkit(ai_toolkit, payload["task_routing"])
    if needs_toolkit_priority_backfill(ai_toolkit):
        ai_toolkit = ensure_toolkit_priorities(ai_toolkit, payload["task_routing"])
    generated = report.generated_at
    if isinstance(generated, str):
        generated_label = datetime.fromisoformat(generated.replace("Z", "+00:00")).strftime("%B %d, %Y")
    else:
        generated_label = generated.strftime("%B %d, %Y")

    return {
        "recipient_name": recipient_name,
        "generated_date": generated_label,
        "report": {**payload, "ai_toolkit": ai_toolkit},
        "overview": payload["overview"],
        "ai_readiness": payload["ai_readiness"],
        "career_identity": payload["career_identity"],
        "competencies": payload["competencies"],
        "daily_work": payload["daily_work"],
        "task_routing": payload["task_routing"],
        "learning_roadmap": payload["learning_roadmap"],
        "ai_toolkit": ai_toolkit,
        "action_plan": payload["action_plan"],
        "strategic_note": payload.get("strategic_note") or "",
        "before_after": payload.get("before_after") or {},
        "cost_roi": payload.get("cost_roi") or {},
        "market_urgency": payload.get("market_urgency") or {},
        "build_count": counts["BUILD"],
        "blend_count": counts["BLEND"],
        "bot_count": counts["BOT"],
        "report_version": report.report_version,
        "assessment_id": str(report.assessment_id),
    }


def render_report_html(report: CareerIntelligenceReportResponse, *, recipient_name: str) -> str:
    context = build_export_context(report, recipient_name=recipient_name)
    template = _env.get_template("report_pdf.html")
    return template.render(**context)


def render_report_pdf(report: CareerIntelligenceReportResponse, *, recipient_name: str) -> bytes:
    html = render_report_html(report, recipient_name=recipient_name)
    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise ValueError("PDF generation failed")
    return buffer.getvalue()


def render_toolkit_html(report: CareerIntelligenceReportResponse, *, recipient_name: str) -> str:
    context = build_export_context(report, recipient_name=recipient_name)
    template = _env.get_template("toolkit.html")
    return template.render(**context)


def generate_scorecard(
    report: CareerIntelligenceReportResponse,
    *,
    recipient_name: str,
) -> ReportScorecardResponse:
    o = report.overview
    r = report.ai_readiness
    report_url = f"{settings.APP_PUBLIC_URL.rstrip('/')}/report?assessmentId={report.assessment_id}"

    headline = (
        f"My CareerShift AI Readiness Score: {r.overall_score}/100 ({r.tier_label}) — "
        f"{o.job_title} in {o.industry}"
    )

    linkedin_text = (
        f"I completed my CareerShift Career Intelligence Assessment.\n\n"
        f"AI Readiness Score: {r.overall_score}/100 ({r.tier_label})\n"
        f"Role: {o.job_title} | Industry: {o.industry}\n"
        f"Tasks analyzed: {o.tasks_analyzed} | Automation exposure: {o.automation_pct}%\n"
        f"Career risk: {o.career_risk}\n\n"
        f"{r.tier_description}\n\n"
        f"View the full framework: {report_url}\n\n"
        f"#AIReadiness #CareerShift #FutureOfWork"
    )

    twitter_text = (
        f"CareerShift AI Readiness: {r.overall_score}/100 ({r.tier_label}) | "
        f"{o.job_title} | {o.automation_pct}% automation exposure | "
        f"Risk: {o.career_risk} {report_url} #CareerShift"
    )
    if len(twitter_text) > 280:
        twitter_text = twitter_text[:277] + "..."

    return ReportScorecardResponse(
        assessment_id=str(report.assessment_id),
        score=r.overall_score,
        tier_label=r.tier_label,
        job_title=o.job_title,
        industry=o.industry,
        automation_pct=o.automation_pct,
        career_risk=o.career_risk,
        headline=headline,
        linkedin_text=linkedin_text,
        twitter_text=twitter_text,
        report_url=report_url,
    )


def export_report_json(report: CareerIntelligenceReportResponse) -> dict:
    return json.loads(report.model_dump_json())
