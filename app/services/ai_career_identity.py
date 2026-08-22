"""Suggest career identity fields from free-text professional background via Anthropic."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic, AuthenticationError
from pydantic import ValidationError

from app.core.anthropic_client import (
    build_messages_create_kwargs,
    create_async_client,
    extract_response_text,
    get_anthropic_api_key,
    get_anthropic_effort,
    get_anthropic_model,
    get_anthropic_temperature,
    model_supports_sampling_params,
)
from app.core.config import settings
from app.schemas.profile import FieldSuggestion, SuggestIdentityResponse
from promppts.CareerIdentitySuggestService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

_FIELD_KEYS = (
    "industry",
    "department",
    "functional_domain",
    "specialization",
    "job_title",
)


class AITimeoutError(Exception):
    """LLM call exceeded configured timeout."""


class AIUnavailableError(Exception):
    """Anthropic auth/API/network/config failure."""


class AIParseError(Exception):
    """Assistant output was not valid JSON."""


class AISchemaValidationError(Exception):
    """Assistant JSON failed strict schema validation."""


def _get_client() -> AsyncAnthropic:
    return create_async_client()


def _strip_markdown_json(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def _normalize_field_payload(raw: Any) -> Any:
    """Normalize empty string values to null; do not invent or clamp confidence."""
    if not isinstance(raw, dict):
        return raw
    normalized = dict(raw)
    value = normalized.get("value")
    if isinstance(value, str) and not value.strip():
        normalized["value"] = None
    elif isinstance(value, str):
        normalized["value"] = value.strip()
    return normalized


def parse_and_validate_identity_payload(output_text: str) -> SuggestIdentityResponse:
    """Parse model text into SuggestIdentityResponse. Raises typed AI* errors."""
    try:
        clean = _strip_markdown_json(output_text)
        parsed = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise AIParseError("AI returned invalid JSON for career identity suggestions.") from exc

    if not isinstance(parsed, dict):
        raise AIParseError("AI response was not a JSON object.")

    for key in _FIELD_KEYS:
        if key not in parsed:
            raise AISchemaValidationError(f"AI response missing required field: {key}")

    try:
        prepared = {key: _normalize_field_payload(parsed[key]) for key in _FIELD_KEYS}
        return SuggestIdentityResponse.model_validate(prepared)
    except ValidationError as exc:
        raise AISchemaValidationError(
            "AI returned an invalid career identity schema. Please try again."
        ) from exc


async def suggest_career_identity_from_ai(
    professional_background: str,
    *,
    request_id: str | None = None,
    user_id: str | None = None,
) -> SuggestIdentityResponse:
    """
    Call Anthropic to extract career identity fields from professional background text.

    Logs metadata only never raw background, field values, reasons, or full AI JSON.
    """
    input_len = len(professional_background)
    started = time.monotonic()

    try:
        get_anthropic_api_key()
    except ValueError as exc:
        raise AIUnavailableError("ANTHROPIC_API_KEY is not configured on the server.") from exc

    model = get_anthropic_model()
    user_prompt = USER_PROMPT_TEMPLATE.format(professional_background=professional_background)

    request_kwargs = build_messages_create_kwargs(
        model,
        max_tokens=1024,
        temperature=get_anthropic_temperature(),
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    if model_supports_sampling_params(model):
        logger.info(
            "suggest_identity start request_id=%s user_id=%s model=%s temperature=%s input_chars=%s",
            request_id,
            user_id,
            model,
            get_anthropic_temperature(),
            input_len,
        )
    else:
        logger.info(
            "suggest_identity start request_id=%s user_id=%s model=%s effort=%s input_chars=%s",
            request_id,
            user_id,
            model,
            get_anthropic_effort(),
            input_len,
        )

    client = _get_client()
    timeout_seconds = float(settings.SUGGEST_IDENTITY_LLM_TIMEOUT_SECONDS)
    try:
        response = await asyncio.wait_for(
            client.messages.create(**request_kwargs),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "suggest_identity timeout request_id=%s user_id=%s model=%s input_chars=%s duration_ms=%s",
            request_id,
            user_id,
            model,
            input_len,
            duration_ms,
        )
        raise AITimeoutError("AI service timed out. Please try again.") from exc
    except AuthenticationError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.error(
            "suggest_identity auth_failed request_id=%s user_id=%s model=%s duration_ms=%s",
            request_id,
            user_id,
            model,
            duration_ms,
        )
        raise AIUnavailableError(
            "AI service authentication failed. Please contact support."
        ) from exc
    except APIStatusError as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.exception(
            "suggest_identity api_error request_id=%s user_id=%s model=%s status=%s duration_ms=%s",
            request_id,
            user_id,
            model,
            exc.status_code,
            duration_ms,
        )
        message = exc.message or str(exc)
        if "credit balance" in message.lower():
            raise AIUnavailableError(
                "AI service is temporarily unavailable due to billing limits."
            ) from exc
        raise AIUnavailableError("AI service is temporarily unavailable.") from exc
    except AITimeoutError:
        raise
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.exception(
            "suggest_identity unexpected_error request_id=%s user_id=%s model=%s duration_ms=%s",
            request_id,
            user_id,
            model,
            duration_ms,
        )
        raise AIUnavailableError("AI service is temporarily unavailable.") from exc

    output_text = extract_response_text(response)
    output_len = len(output_text or "")

    try:
        result = parse_and_validate_identity_payload(output_text)
    except (AIParseError, AISchemaValidationError) as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        logger.warning(
            "suggest_identity validation_failed request_id=%s user_id=%s model=%s "
            "input_chars=%s output_chars=%s duration_ms=%s error_category=%s",
            request_id,
            user_id,
            model,
            input_len,
            output_len,
            duration_ms,
            type(exc).__name__,
        )
        raise

    duration_ms = int((time.monotonic() - started) * 1000)
    logger.info(
        "suggest_identity success request_id=%s user_id=%s model=%s "
        "input_chars=%s output_chars=%s duration_ms=%s",
        request_id,
        user_id,
        model,
        input_len,
        output_len,
        duration_ms,
    )
    return result


# Re-export for tests that build FieldSuggestion directly
__all__ = [
    "AITimeoutError",
    "AIUnavailableError",
    "AIParseError",
    "AISchemaValidationError",
    "FieldSuggestion",
    "parse_and_validate_identity_payload",
    "suggest_career_identity_from_ai",
]
