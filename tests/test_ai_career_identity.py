"""Unit tests for career identity AI parse/validate (no live Anthropic calls)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.schemas.profile import FieldSuggestion
from app.services.ai_career_identity import (
    AIParseError,
    AISchemaValidationError,
    parse_and_validate_identity_payload,
)


def _field(value, confidence: float, reason: str = "Explicitly stated in the background.") -> dict:
    return {"value": value, "confidence": confidence, "reason": reason}


def _payload(**overrides) -> dict:
    base = {
        "industry": _field("Healthcare Technology", 0.93),
        "department": _field("Information Technology", 0.88),
        "functional_domain": _field("Software Engineering", 0.95),
        "specialization": _field("Backend Engineering", 0.94),
        "job_title": _field("Senior Software Engineer", 0.98),
    }
    base.update(overrides)
    return base


def test_parse_valid_full_extraction():
    text = json.dumps(_payload())
    result = parse_and_validate_identity_payload(text)
    assert result.job_title.value == "Senior Software Engineer"
    assert result.industry.confidence == 0.93


def test_parse_markdown_fenced_json():
    inner = json.dumps(_payload())
    text = f"```json\n{inner}\n```"
    result = parse_and_validate_identity_payload(text)
    assert result.specialization.value == "Backend Engineering"


def test_parse_partial_null_values_ok():
    text = json.dumps(
        _payload(
            industry=_field(None, 0.4, "Not enough detail in your background to determine this confidently."),
            department=_field(None, 0.2, "Not enough detail in your background to determine this confidently."),
        )
    )
    result = parse_and_validate_identity_payload(text)
    assert result.industry.value is None
    assert result.job_title.value == "Senior Software Engineer"


def test_empty_string_value_normalized_to_null():
    text = json.dumps(_payload(industry=_field("   ", 0.5, "Not enough detail.")))
    result = parse_and_validate_identity_payload(text)
    assert result.industry.value is None


def test_confidence_boundaries_pass_through():
    for conf in (0.79, 0.80, 0.81):
        text = json.dumps(_payload(industry=_field("Healthcare", conf)))
        result = parse_and_validate_identity_payload(text)
        assert result.industry.confidence == conf


@pytest.mark.parametrize(
    "bad_confidence",
    ["0.95", "high", True, 1.5, -0.1],
)
def test_invalid_confidence_rejected(bad_confidence):
    payload = _payload(industry={"value": "Healthcare", "confidence": bad_confidence, "reason": "Stated."})
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


def test_missing_confidence_rejected():
    payload = _payload(industry={"value": "Healthcare", "reason": "Stated."})
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


def test_missing_reason_rejected():
    payload = _payload(industry={"value": "Healthcare", "confidence": 0.9})
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


def test_empty_reason_rejected():
    payload = _payload(industry=_field("Healthcare", 0.9, ""))
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


def test_overlong_reason_rejected():
    payload = _payload(industry=_field("Healthcare", 0.9, "x" * 161))
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


def test_missing_top_level_field_rejected():
    payload = _payload()
    del payload["department"]
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


def test_malformed_json_rejected():
    with pytest.raises(AIParseError):
        parse_and_validate_identity_payload("{not json")


def test_extra_top_level_fields_ignored_via_parse():
    payload = _payload()
    payload["unexpected"] = {"foo": 1}
    result = parse_and_validate_identity_payload(json.dumps(payload))
    assert result.job_title.value == "Senior Software Engineer"


def test_wrong_value_type_rejected():
    payload = _payload(industry={"value": 123, "confidence": 0.9, "reason": "Stated."})
    with pytest.raises(AISchemaValidationError):
        parse_and_validate_identity_payload(json.dumps(payload))


@pytest.mark.asyncio
async def test_suggest_identity_timeout_raises_ai_timeout(monkeypatch):
    import asyncio

    from app.services import ai_career_identity as mod

    class _FakeClient:
        async def messages_create(self, **kwargs):
            await asyncio.sleep(10)
            raise AssertionError("should have timed out")

        @property
        def messages(self):
            return self

        async def create(self, **kwargs):
            await asyncio.sleep(10)
            raise AssertionError("should have timed out")

    monkeypatch.setattr(mod, "get_anthropic_api_key", lambda: "sk-test")
    monkeypatch.setattr(mod, "get_anthropic_model", lambda: "claude-test")
    monkeypatch.setattr(mod, "_get_client", lambda: _FakeClient())
    monkeypatch.setattr(mod.settings, "SUGGEST_IDENTITY_LLM_TIMEOUT_SECONDS", 0.01)

    from app.services.ai_career_identity import AITimeoutError, suggest_career_identity_from_ai

    with pytest.raises(AITimeoutError):
        await suggest_career_identity_from_ai("Senior engineer in healthcare with eight years.")
