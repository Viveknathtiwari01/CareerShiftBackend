"""Resume text extraction and profile-detail parsing. No live AI calls."""

from __future__ import annotations

import json
from io import BytesIO

import pytest

from app.schemas.profile import FieldSuggestion, SuggestIdentityResponse
from app.services.ai_career_identity import AIParseError
from app.services.resume_profile import (
    build_resume_profile_response,
    experience_level_for_years,
    parse_resume_details_payload,
)
from app.services.resume_text import ResumeReadError, extract_resume_text


def _field(value: str, confidence: float = 0.9) -> FieldSuggestion:
    return FieldSuggestion(value=value, confidence=confidence, reason="Stated in the resume.")


def _identity() -> SuggestIdentityResponse:
    return SuggestIdentityResponse(
        industry=_field("Healthcare"),
        department=_field("Clinical Operations"),
        functional_domain=_field("Nursing"),
        specialization=_field("Pediatric Critical Care"),
        job_title=_field("Pediatric ICU Nurse"),
    )


def _pdf_bytes(text: str) -> bytes:
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.save()
    return buffer.getvalue()


def _docx_bytes(text: str) -> bytes:
    from docx import Document

    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


RESUME_SENTENCE = (
    "Pediatric ICU Nurse with 8 years in healthcare clinical operations, "
    "focused on pediatric critical care. Tools include Excel and Epic."
)


def test_extract_pdf_text():
    text = extract_resume_text(_pdf_bytes(RESUME_SENTENCE), "resume.pdf")
    assert "Pediatric ICU Nurse" in text
    assert "Excel" in text


def test_extract_docx_text():
    text = extract_resume_text(_docx_bytes(RESUME_SENTENCE), "Resume.DOCX")
    assert "pediatric critical care" in text.lower()


def test_rejects_wrong_type_and_empty_scan():
    with pytest.raises(ResumeReadError, match="PDF or DOCX"):
        extract_resume_text(b"not a resume but long enough text " * 5, "notes.txt")

    with pytest.raises(ResumeReadError, match="enough text"):
        extract_resume_text(_pdf_bytes("Hi"), "scan.pdf")


def test_rejects_oversized_file():
    payload = b"%PDF" + b"x" * (5 * 1024 * 1024)
    with pytest.raises(ResumeReadError, match="5 MB"):
        extract_resume_text(payload, "big.pdf")


@pytest.mark.parametrize(
    ("years", "level"),
    [
        (None, None),
        (0, "0-1 Years"),
        (1, "0-1 Years"),
        (2, "1-3 Years"),
        (3, "1-3 Years"),
        (5, "3-5 Years"),
        (8, "5-8 Years"),
        (12, "8-12 Years"),
        (13, "12+ Years"),
        (-1, None),
        (61, None),
    ],
)
def test_experience_level_buckets(years, level):
    assert experience_level_for_years(years) == level


def test_parse_resume_details_normalizes_lists_and_years():
    payload = {
        "experience_years": "8 years",
        "tools": [" Excel ", "Excel", "SAP", 12, "x" * 80],
        "technical_skills": ["Critical care protocols"],
        "professional_skills": ["Shift coordination"],
        "soft_skills": [],
        "behavioural_skills": ["Ownership"],
        "digital_skills": ["Microsoft 365"],
        "ai_tools": ["ChatGPT"],
    }
    details = parse_resume_details_payload(json.dumps(payload))
    assert details.experience_years == 8
    assert details.experience_level == "5-8 Years"
    assert details.tools == ["Excel", "SAP"]
    assert details.ai_tools == ["ChatGPT"]
    assert details.technical_skills == ["Critical care protocols"]


def test_parse_resume_details_accepts_fenced_json_with_preamble():
    payload = json.dumps({"experience_years": 6, "tools": ["Excel"]})
    details = parse_resume_details_payload(f"Extracted details:\n```json\n{payload}\n```")
    assert details.experience_years == 6
    assert details.tools == ["Excel"]


def test_parse_resume_details_rejects_invalid_json():
    with pytest.raises(AIParseError):
        parse_resume_details_payload("not json")


def test_build_response_keeps_identity_and_details():
    details = parse_resume_details_payload(
        json.dumps({"experience_years": 4, "tools": ["Figma"], "ai_tools": []})
    )
    response = build_resume_profile_response(_identity(), details)
    assert response.job_title.value == "Pediatric ICU Nurse"
    assert response.resume_details.experience_level == "3-5 Years"
    assert response.resume_details.tools == ["Figma"]
