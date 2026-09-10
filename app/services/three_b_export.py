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

# CareerShift design tokens + 3B category accents (aligned with Frontend styles.css)
BRAND_NAVY = "#0a121f"
BRAND_GOLD = "#c9a84c"
BRAND_TEAL = "#0d9488"

CATEGORY_META: dict[str, dict[str, str]] = {
    "BUILD": {
        "title": "Build",
        "tagline": "Deepen human mastery",
        "description": "Judgment, relationships, and expertise AI cannot replace.",
        "accent": "#1e3a5f",
        "accent_light": "#eef3fa",
    },
    "BLEND": {
        "title": "Blend",
        "tagline": "Human + AI co-pilot",
        "description": "AI drafts and analyzes — you decide and own the outcome.",
        "accent": BRAND_GOLD,
        "accent_light": "#faf6eb",
    },
    "BOT": {
        "title": "Bot",
        "tagline": "Automate within 90 days",
        "description": "Repetitive work — delegate to AI and reclaim hours.",
        "accent": BRAND_TEAL,
        "accent_light": "#ecfdf5",
    },
}

_LABEL_MAP: dict[str, str] = {
    "self_serve": "Self-serve",
    "company_tech": "Company tech",
    "org_must_enable": "Org must enable",
    "stays_human_led": "Stays human-led",
    "free": "Free",
    "freemium": "Freemium",
    "paid_individual": "Paid (individual)",
    "paid_team": "Paid (team)",
    "enterprise": "Enterprise",
}


def _format_generated_at(value: datetime | None) -> str:
    if not value:
        return datetime.utcnow().strftime("%B %d, %Y")
    return value.strftime("%B %d, %Y at %H:%M UTC")


def _format_label(value: str) -> str:
    if not value:
        return ""
    return _LABEL_MAP.get(value, value.replace("_", " ").title())


def _enrich_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(analysis)
    components = []
    for comp in enriched.get("components") or []:
        comp_copy = dict(comp)
        tools = []
        for tool in comp_copy.get("tools") or []:
            tool_copy = dict(tool)
            tool_copy["cost_band_label"] = _format_label(str(tool_copy.get("cost_band", "")))
            tool_copy["feasibility_label"] = _format_label(str(tool_copy.get("feasibility", "")))
            tools.append(tool_copy)
        comp_copy["tools"] = tools
        components.append(comp_copy)
    enriched["components"] = components
    return enriched


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

    meta = CATEGORY_META.get(cat, CATEGORY_META["BLEND"])

    return {
        "category": cat,
        "category_meta": meta,
        "brand": {
            "navy": BRAND_NAVY,
            "gold": BRAND_GOLD,
            "teal": BRAND_TEAL,
        },
        "profile": profile,
        "generated_at": _format_generated_at(analysis.generated_at),
        "hours": {
            "weekly": bucket.weekly_hours,
            "annual": bucket.annual_hours,
            "task_count": bucket.task_count,
        },
        "analyses": [_enrich_analysis(a.model_dump(mode="json")) for a in filtered],
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
    import re

    header_match = re.search(r'<div id="header_content" style="display: none;">(.*?)</div>', html, re.DOTALL)
    header_html = header_match.group(1) if header_match else "<span></span>"
    
    footer_match = re.search(r'<div id="footer_content" style="display: none;">(.*?)</div>', html, re.DOTALL)
    footer_html = footer_match.group(1) if footer_match else "<span></span>"

    header_template = f'<div style="width: 100%; font-family: Helvetica, Arial, sans-serif; padding: 0 1.4cm; -webkit-print-color-adjust: exact;">{header_html}</div>'
    footer_template = f'<div style="width: 100%; font-family: Helvetica, Arial, sans-serif; padding: 0 1.4cm; -webkit-print-color-adjust: exact;">{footer_html}</div>'

    def _generate_pdf() -> bytes:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_content(html)
            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template=header_template,
                footer_template=footer_template,
                margin={"top": "2.4cm", "right": "1.4cm", "bottom": "1.9cm", "left": "1.4cm"},
            )
            browser.close()
            return pdf_bytes

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_generate_pdf).result()


def render_category_pdf(context: dict[str, Any]) -> bytes:
    from app.services.report_cover import render_cover_pdf
    from app.services.report_export import merge_cover_and_body

    profile = context.get("profile", {})
    recipient_name = profile.get("name") or "Professional"
    experience_years = str(profile.get("experience_years") or "—")
    category = context.get("category", "")

    cover_pdf = render_cover_pdf(
        recipient_name=recipient_name,
        role_line=f"3B Analysis: {category}",
        generated_date=context.get("generated_at", ""),
        report_version="1.0",
        experience_years=experience_years,
        overall_score=None,
    )
    body_pdf = html_to_pdf(render_category_html(context))
    return merge_cover_and_body(cover_pdf, body_pdf)


def build_task_export_context(
    analysis: TaskAnalysisRunResponse,
    task_id: str,
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    task = next((a for a in analysis.analyses if str(a.task_id) == task_id), None)
    if not task:
        return None
    cat = task.category.upper()
    meta = CATEGORY_META.get(cat, CATEGORY_META["BLEND"])
    return {
        "category": cat,
        "category_meta": meta,
        "profile": profile,
        "generated_at": _format_generated_at(analysis.generated_at),
        "task": _enrich_analysis(task.model_dump(mode="json")),
        "disclaimer": (
            "Tool suggestions are AI-generated for your profile at analysis time. "
            "All tools are unverified — confirm fit, cost, and employer policy before adopting."
        ),
    }


def render_task_html(context: dict[str, Any]) -> str:
    template = _jinja.get_template("three_b_task.html")
    return template.render(**context)


def render_task_pdf(context: dict[str, Any]) -> bytes:
    return html_to_pdf(render_task_html(context))

