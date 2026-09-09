"""Pixel-accurate Career Intelligence Report cover page (ReportLab)."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


NAVY = HexColor("#0B1D3A")
NAVY_PANEL = HexColor("#16304F")
GOLD = HexColor("#FDCF58")
WHITE = HexColor("#FFFFFF")
MUTED = HexColor("#94A3B8")
MUTED_SOFT = HexColor("#C5CEDA")
RING_TRACK = HexColor("#1E3558")


def _tracked(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    tracking: float,
    *,
    font: str,
    size: float,
) -> None:
    c.setFont(font, size)
    for ch in text:
        c.drawString(x, y, ch)
        x += c.stringWidth(ch, font, size) + (tracking if ch != " " else tracking * 1.4)


def _draw_progress_ring(
    c: canvas.Canvas,
    cx: float,
    cy: float,
    radius: float,
    stroke: float,
    score: int,
) -> None:
    """Draw a circular readiness gauge matching the reference cover."""
    score = max(0, min(int(score or 0), 100))

    c.setStrokeColor(RING_TRACK)
    c.setLineWidth(stroke)
    c.setLineCap(1)
    c.circle(cx, cy, radius, stroke=1, fill=0)

    # Gold arc: ~4 o'clock start, clockwise (matches reference segment)
    if score > 0:
        c.setStrokeColor(GOLD)
        c.setLineWidth(stroke)
        c.setLineCap(1)
        c.arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            startAng=-40,
            extent=-3.6 * score,
        )

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 44)
    c.drawCentredString(cx, cy - 4, str(score))

    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 6.2)
    c.drawCentredString(cx, cy - 26, "OVERALL")
    c.drawCentredString(cx, cy - 35, "AI READINESS")


def render_cover_pdf(
    *,
    recipient_name: str,
    role_line: str,
    generated_date: str,
    report_version: str,
    experience_years: str,
    overall_score: int | None = None,
    site_url: str = "www.careershift3b.com",
) -> bytes:
    """Render the dark navy cover page to match the reference design."""
    buffer = BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    # Full-page navy background
    c.setFillColor(NAVY)
    c.rect(0, 0, width, height, stroke=0, fill=1)

    # Gold top rule
    c.setStrokeColor(GOLD)
    c.setLineWidth(2.4)
    c.line(0, height - 1.2, width, height - 1.2)

    # Bottom-right diagonal panel
    c.setFillColor(NAVY_PANEL)
    path = c.beginPath()
    path.moveTo(width * 0.38, 0)
    path.lineTo(width, 0)
    path.lineTo(width, height * 0.48)
    path.close()
    c.drawPath(path, stroke=0, fill=1)

    left = 52
    top = height - 54

    # Brand
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(left, top, "CareerShift")
    brand_w = c.stringWidth("CareerShift", "Helvetica-Bold", 17)
    c.setFillColor(GOLD)
    c.drawString(left + brand_w, top, "3B")

    c.setFillColor(MUTED_SOFT)
    _tracked(c, "AI CAREER INTELLIGENCE", left, top - 15, 1.6, font="Helvetica", size=7)

    # Title block — ~1/3 down the page
    title_y = height - 250
    c.setFillColor(GOLD)
    _tracked(
        c,
        "CAREER INTELLIGENCE REPORT",
        left,
        title_y,
        1.15,
        font="Helvetica-Bold",
        size=8.5,
    )

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 36)
    line_h = 42
    c.drawString(left, title_y - 44, "Your AI")
    c.drawString(left, title_y - 44 - line_h, "Readiness")
    c.drawString(left, title_y - 44 - line_h * 2, "Blueprint")

    rule_y = title_y - 44 - line_h * 2 - 16
    c.setStrokeColor(GOLD)
    c.setLineWidth(3.4)
    c.line(left, rule_y, left + 54, rule_y)

    # Prepared for
    prep_y = rule_y - 46
    c.setFillColor(MUTED)
    _tracked(c, "PREPARED FOR", left, prep_y, 1.25, font="Helvetica", size=7)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(left, prep_y - 20, recipient_name or "Professional")

    c.setFillColor(MUTED_SOFT)
    c.setFont("Helvetica", 9.5)
    role = role_line or ""
    max_role_w = width * 0.56
    while role and c.stringWidth(role, "Helvetica", 9.5) > max_role_w:
        role = role[:-2]
    c.drawString(left, prep_y - 37, role)

    # Meta row
    meta_y = prep_y - 92
    experience_display = (
        f"{experience_years} years"
        if experience_years and experience_years != "—"
        else "—"
    )
    meta_items = [
        ("GENERATED", generated_date or "—"),
        ("VERSION", str(report_version or "—")),
        ("EXPERIENCE", experience_display),
    ]
    col_x = left
    for label, value in meta_items:
        c.setFillColor(MUTED)
        _tracked(c, label, col_x, meta_y, 1.05, font="Helvetica", size=6.5)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(col_x, meta_y - 15, value)
        
        val_width = c.stringWidth(value, "Helvetica-Bold", 10)
        col_x += max(120, val_width + 30)

    # Score gauge (optional)
    if overall_score is not None:
        gauge_cx = width - 122
        gauge_cy = 175
        _draw_progress_ring(c, gauge_cx, gauge_cy, radius=62, stroke=12, score=overall_score)

    # Footer
    footer_y = 30
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawString(
        left,
        footer_y,
        f"© CareerShift - Confidential - Prepared exclusively for {recipient_name}",
    )
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawRightString(width - 42, footer_y, site_url or "www.careershift3b.com")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
