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
        "accent": "#5b21b6",
        "accent_light": "#ede9fe",
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
        "tagline": "Automate within 30 days",
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


def _draw_brand_wordmark(canvas: Any, x: float, y: float, size: float = 15) -> float:
    """Draw 'Career' (navy) + 'Shift' (gold). Returns total width."""
    from reportlab.lib import colors

    font = "Helvetica-Bold"
    canvas.setFont(font, size)
    canvas.setFillColor(colors.HexColor(BRAND_NAVY))
    canvas.drawString(x, y, "Career")
    career_w = canvas.stringWidth("Career", font, size)
    canvas.setFillColor(colors.HexColor(BRAND_GOLD))
    canvas.drawString(x + career_w, y, "Shift")
    shift_w = canvas.stringWidth("Shift", font, size)
    return career_w + shift_w


def _draw_page_chrome(canvas: Any, context: dict[str, Any]) -> None:
    """Draw repeating header/footer with branded CareerShift wordmark."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4

    _, page_height = A4
    margin_left = 42
    content_width = 511
    margin_right = margin_left + content_width
    meta = context["category_meta"]
    accent = colors.HexColor(meta["accent"])

    canvas.saveState()

    # ── Header: CareerShift wordmark ──
    header_y = page_height - 38
    _draw_brand_wordmark(canvas, margin_left, header_y, size=16)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(margin_left, header_y - 12, "AI CAREER INTELLIGENCE")

    doc_title = f"3B Analysis · {meta['title']}"
    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(accent)
    title_w = canvas.stringWidth(doc_title, "Helvetica-Bold", 9)
    canvas.drawString(margin_right - title_w, header_y, doc_title)

    tagline = meta["tagline"].upper()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    tag_w = canvas.stringWidth(tagline, "Helvetica", 7)
    canvas.drawString(margin_right - tag_w, header_y - 12, tagline)

    rule_y = header_y - 24
    canvas.setStrokeColor(colors.HexColor(BRAND_GOLD))
    canvas.setLineWidth(1.5)
    canvas.line(margin_left, rule_y, margin_right, rule_y)
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(0.5)
    canvas.line(margin_left, rule_y - 2, margin_right, rule_y - 2)

    # ── Footer ──
    footer_line_y = 28
    canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
    canvas.setLineWidth(0.5)
    canvas.line(margin_left, footer_line_y, margin_right, footer_line_y)

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(margin_left, 16, "© ")
    prefix_w = canvas.stringWidth("© ", "Helvetica", 7.5)
    brand_w = _draw_brand_wordmark(canvas, margin_left + prefix_w, 16, size=7.5)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawString(
        margin_left + prefix_w + brand_w,
        16,
        f" · Confidential · {context['generated_at']}",
    )

    footer_right = f"3B {context['category']} Report"
    footer_right_w = canvas.stringWidth(footer_right, "Helvetica", 7.5)
    canvas.drawString(margin_right - footer_right_w, 16, footer_right)

    canvas.restoreState()


class _BrandedCanvas:
    """Canvas wrapper that stamps CareerShift header/footer on every page."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        from reportlab.pdfgen import canvas

        self._context = kwargs.pop("branding_context")
        self._canvas = canvas.Canvas(*args, **kwargs)
        self._page_states: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._canvas, name)

    def showPage(self) -> None:
        self._page_states.append(dict(self._canvas.__dict__))
        self._canvas._startPage()  # noqa: SLF001 — reportlab internal API

    def save(self) -> None:
        # Capture the final page (showPage is not called after the last one).
        self._page_states.append(dict(self._canvas.__dict__))
        page_count = len(self._page_states)
        for index, state in enumerate(self._page_states):
            self._canvas.__dict__.update(state)
            _draw_page_chrome(self._canvas, self._context)
            if index < page_count - 1:
                self._canvas.showPage()
        self._canvas.save()


def _make_branded_canvas(context: dict[str, Any]) -> type:
    def _factory(*args: Any, **kwargs: Any) -> _BrandedCanvas:
        return _BrandedCanvas(*args, branding_context=context, **kwargs)

    return _factory


def html_to_pdf(html: str, context: dict[str, Any]) -> bytes:
    from xhtml2pdf import pisa

    buffer = BytesIO()
    pisa.CreatePDF(html, dest=buffer, canvasmaker=_make_branded_canvas(context))
    return buffer.getvalue()


def render_category_pdf(context: dict[str, Any]) -> bytes:
    return html_to_pdf(render_category_html(context), context)
