"""Export 3B analysis by category (BUILD / BLEND / BOT)."""

from __future__ import annotations

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.assessment_task_analysis import TaskAnalysisRunResponse

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "export"

_jinja = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _format_generated_at(value: datetime | None) -> str:
    if not value:
        return datetime.utcnow().strftime("%B %d, %Y")
    return value.strftime("%B %d, %Y at %H:%M UTC")


def build_category_export_context(
    analysis: TaskAnalysisRunResponse,
    category: str,
    profile: dict[str, Any],
) -> dict[str, Any]:
    cat = category.upper()
    filtered = [a for a in analysis.analyses if a.category.upper() == cat]
    bucket = analysis.hours_summary.BUILD
    if cat == "BLEND":
        bucket = analysis.hours_summary.BLEND
    elif cat == "BOT":
        bucket = analysis.hours_summary.BOT

    return {
        "category": cat,
        "profile": profile,
        "generated_at": _format_generated_at(analysis.generated_at),
        "hours": {
            "weekly": bucket.weekly_hours,
            "annual": bucket.annual_hours,
            "task_count": bucket.task_count,
        },
        "analyses": [a.model_dump(mode="json") for a in filtered],
        "disclaimer": (
            "Tool suggestions are AI-generated for your profile at analysis time. "
            "All tools are unverified — confirm fit, cost, and employer policy before adopting."
        ),
    }


def render_category_html(context: dict[str, Any]) -> str:
    template = _jinja.get_template("three_b_category.html")
    return template.render(**context)


def render_category_json(context: dict[str, Any]) -> bytes:
    return json.dumps(context, indent=2, default=str).encode("utf-8")


def html_to_pdf(html: str) -> bytes:
    from xhtml2pdf import pisa

    buffer = BytesIO()
    pisa.CreatePDF(html, dest=buffer)
    return buffer.getvalue()


def render_category_pdf(context: dict[str, Any]) -> bytes:
    return html_to_pdf(render_category_html(context))
