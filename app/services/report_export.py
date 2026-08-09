"""HTML/PDF export and social scorecard generation for Career Intelligence Reports."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.career_intelligence_report import CareerIntelligenceReportResponse
from app.schemas.report_export import ReportScorecardResponse

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "export"

_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _format_date(value: datetime | None) -> str:
    if not value:
        return datetime.utcnow().strftime("%B %d, %Y")
    return value.strftime("%B %d, %Y")


def _portfolio_lines(mix: dict[str, int]) -> list[str]:
    total = sum(mix.values()) or 1
    lines = []
    for key in ("BUILD", "BLEND", "BOT"):
        count = mix.get(key, 0)
        if count:
            pct = round((count / total) * 100)
            lines.append(f"{pct}% {key}")
    return lines


def generate_scorecard(
    report: CareerIntelligenceReportResponse,
    *,
    job_title: str | None = None,
) -> ReportScorecardResponse:
    readiness = report.ai_readiness
    role = job_title or report.career_identity.title.replace("AI-Augmented ", "")
    mix = readiness.portfolio_mix
    total = sum(mix.values()) or 1
    bot_pct = round((mix.get("BOT", 0) / total) * 100)
    blend_pct = round((mix.get("BLEND", 0) / total) * 100)
    build_pct = round((mix.get("BUILD", 0) / total) * 100)

    headline = (
        f"AI Readiness {readiness.overall_score}/100 — {readiness.tier_label} "
        f"({role})"
    )
    hashtags = ["AIReadiness", "CareerShift", "FutureOfWork", "AICareer"]

    linkedin_text = (
        f"I just completed my CareerShift AI Career Intelligence Assessment.\n\n"
        f"Score: {readiness.overall_score}/100 ({readiness.tier_label} tier)\n"
        f"Role focus: {role}\n"
        f"3B portfolio mix — BUILD {build_pct}% · BLEND {blend_pct}% · BOT {bot_pct}%\n"
        f"Career risk: {readiness.career_risk} · Opportunity: {readiness.career_opportunity}\n\n"
        f"{report.strategic_note}\n\n"
        f"{' '.join('#' + tag for tag in hashtags)}"
    )

    twitter_text = (
        f"CareerShift AI Readiness: {readiness.overall_score}/100 ({readiness.tier_label}). "
        f"{role} — {bot_pct}% tasks BOT-ready, {blend_pct}% BLEND. "
        f"Building an AI-augmented career. {' '.join('#' + tag for tag in hashtags[:3])}"
    )
    if len(twitter_text) > 280:
        twitter_text = (
            f"AI Readiness {readiness.overall_score}/100 ({readiness.tier_label}). "
            f"{bot_pct}% BOT · {blend_pct}% BLEND · {build_pct}% BUILD. "
            f"#CareerShift #AIReadiness"
        )

    return ReportScorecardResponse(
        headline=headline,
        linkedin_text=linkedin_text.strip(),
        twitter_text=twitter_text.strip(),
        hashtags=hashtags,
    )


def render_report_html(
    report: CareerIntelligenceReportResponse,
    *,
    recipient_name: str | None = None,
    job_title: str | None = None,
) -> str:
    template = _jinja.get_template("career_report.html")
    mix = report.ai_readiness.portfolio_mix
    return template.render(
        report=report,
        recipient_name=recipient_name or "Professional",
        job_title=job_title or report.before_after.role_today,
        generated_date=_format_date(report.generated_at),
        portfolio_lines=_portfolio_lines(mix),
    )


def render_toolkit_html(
    report: CareerIntelligenceReportResponse,
    *,
    job_title: str | None = None,
) -> str:
    template = _jinja.get_template("ai_toolkit.html")
    return template.render(
        report=report,
        job_title=job_title or report.before_after.role_today,
        generated_date=_format_date(report.generated_at),
    )


def html_to_pdf(html: str) -> bytes:
    from xhtml2pdf import pisa

    buffer = BytesIO()
    status = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if status.err:
        raise RuntimeError("PDF generation failed")
    return buffer.getvalue()


def render_report_pdf(
    report: CareerIntelligenceReportResponse,
    *,
    recipient_name: str | None = None,
    job_title: str | None = None,
) -> bytes:
    html = render_report_html(
        report,
        recipient_name=recipient_name,
        job_title=job_title,
    )
    return html_to_pdf(html)
