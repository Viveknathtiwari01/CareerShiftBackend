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

_FIELD_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "value": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["value", "confidence", "reason"],
}

_IDENTITY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {key: _FIELD_JSON_SCHEMA for key in _FIELD_KEYS},
    "required": list(_FIELD_KEYS),
}

# Enough for low-effort reasoning plus the JSON object. A 1024 cap was
# truncating resume responses mid-object, which json.loads then rejected.
_IDENTITY_MAX_TOKENS = 4096
_IDENTITY_RETRY_MAX_TOKENS = 8192

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
# Resume text sometimes appends code-like noise, and the model copies it into a reason.
_GLUED_JUNK_RE = re.compile(r"(?:\.is[A-Z]\w*|(?:\.0){3,}).*")


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


def _repair_json_text(text: str) -> str:
    """Fix the JSON mistakes Claude commonly makes around an otherwise valid object."""
    repaired = (
        text.replace("\ufeff", "")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )
    repaired = _escape_controls_in_strings(repaired)
    return _TRAILING_COMMA_RE.sub(r"\1", repaired)


def _escape_controls_in_strings(text: str) -> str:
    """Escape raw newlines and tabs that appear inside JSON strings."""
    out: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                out.append(char)
                escaped = False
                continue
            if char == "\\":
                out.append(char)
                escaped = True
                continue
            if char == '"':
                in_string = False
                out.append(char)
                continue
            if char == "\n":
                out.append("\\n")
                continue
            if char == "\r":
                out.append("\\r")
                continue
            if char == "\t":
                out.append("\\t")
                continue
            out.append(char)
            continue
        if char == '"':
            in_string = True
        out.append(char)
    return "".join(out)


def _json_candidates(output_text: str) -> list[str]:
    raw = output_text.strip().lstrip("\ufeff")
    candidates: list[str] = []
    for block in _FENCE_RE.findall(raw):
        cleaned = block.strip()
        if cleaned:
            candidates.append(cleaned)
    candidates.append(raw)
    return candidates


def loads_model_json(output_text: str) -> Any:
    """
    Parse a model response that should be one JSON object.

    Accepts markdown fences, leading or trailing prose, trailing commas,
    smart quotes, and raw newlines inside strings.
    """
    if not output_text or not output_text.strip():
        raise json.JSONDecodeError("Expecting value", output_text or "", 0)

    decoder = json.JSONDecoder()
    last_error: json.JSONDecodeError | None = None
    fallback: Any = None
    seen: set[str] = set()

    for candidate in _json_candidates(output_text):
        for variant in (candidate, _repair_json_text(candidate)):
            if variant in seen:
                continue
            seen.add(variant)
            index = 0
            while True:
                start = variant.find("{", index)
                if start < 0:
                    break
                try:
                    value, end = decoder.raw_decode(variant, start)
                except json.JSONDecodeError as exc:
                    last_error = exc
                    index = start + 1
                    continue
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError as exc:
                        last_error = exc
                if isinstance(value, dict):
                    return value
                if fallback is None:
                    fallback = value
                index = max(end, start + 1)

    if fallback is not None:
        return fallback
    if last_error is not None:
        raise last_error
    raise json.JSONDecodeError("Expecting value", output_text, 0)


def _normalize_field_payload(raw: Any) -> Any:
    """Normalize empty values, numeric confidence, and overlong reasons."""
    if not isinstance(raw, dict):
        return raw
    normalized = dict(raw)
    value = normalized.get("value")
    if isinstance(value, str) and not value.strip():
        normalized["value"] = None
    elif isinstance(value, str):
        normalized["value"] = value.strip()

    confidence = normalized.get("confidence")
    if isinstance(confidence, str):
        try:
            normalized["confidence"] = float(confidence.strip())
        except ValueError:
            pass
    elif isinstance(confidence, bool):
        pass
    elif isinstance(confidence, (int, float)):
        normalized["confidence"] = float(confidence)

    reason = normalized.get("reason")
    if isinstance(reason, str):
        normalized["reason"] = _clean_reason(reason)
    return normalized


def _clean_reason(reason: str) -> str:
    """Keep the user-facing sentence and drop glued-on junk such as `.isEqual.0.0.0`."""
    collapsed = " ".join(reason.split()).strip()
    if not _GLUED_JUNK_RE.search(collapsed):
        if len(collapsed) > 160:
            return collapsed[:160].rstrip()
        return collapsed

    cleaned = _GLUED_JUNK_RE.sub("", collapsed).strip(" .")
    if not cleaned:
        if len(collapsed) > 160:
            return collapsed[:160].rstrip()
        return collapsed
    cleaned = f"{cleaned}."
    if len(cleaned) > 160:
        cleaned = cleaned[:160].rstrip()
    return cleaned


def _attach_identity_json_schema(request_kwargs: dict[str, Any]) -> None:
    """Force the identity response to match the five-field object schema."""
    output_config = dict(request_kwargs.get("output_config") or {})
    output_config["format"] = {
        "type": "json_schema",
        "schema": _IDENTITY_JSON_SCHEMA,
    }
    request_kwargs["output_config"] = output_config


def _parse_failure_detail(exc: Exception) -> str:
    """Metadata only. Never include field values or model text."""
    cause = exc.__cause__
    if isinstance(cause, json.JSONDecodeError):
        return f"json_error={cause.msg} line={cause.lineno} col={cause.colno}"
    if isinstance(cause, ValidationError):
        kinds = ",".join(sorted({str(err.get("type", "")) for err in cause.errors()}))
        return f"schema_errors={kinds}"
    return "detail=unavailable"


def parse_and_validate_identity_payload(output_text: str) -> SuggestIdentityResponse:
    """Parse model text into SuggestIdentityResponse. Raises typed AI* errors."""
    try:
        parsed = loads_model_json(output_text)
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
    # replace(), not format(): resume text often contains braces.
    user_prompt = USER_PROMPT_TEMPLATE.replace(
        "{professional_background}", professional_background
    )
    messages: list[dict[str, str]] = [{"role": "user", "content": user_prompt}]
    max_tokens = _IDENTITY_MAX_TOKENS
    use_schema = True

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
    result: SuggestIdentityResponse | None = None

    for attempt in (1, 2):
        request_kwargs = build_messages_create_kwargs(
            model,
            max_tokens=max_tokens,
            temperature=get_anthropic_temperature(),
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        if use_schema:
            _attach_identity_json_schema(request_kwargs)
        try:
            response = await asyncio.wait_for(
                client.messages.create(**request_kwargs),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "suggest_identity timeout request_id=%s user_id=%s model=%s input_chars=%s duration_ms=%s attempt=%s",
                request_id,
                user_id,
                model,
                input_len,
                duration_ms,
                attempt,
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
            message = exc.message or str(exc)
            lowered = message.lower()
            if (
                use_schema
                and attempt == 1
                and exc.status_code == 400
                and any(token in lowered for token in ("json_schema", "output_config", "schema"))
            ):
                logger.warning(
                    "suggest_identity schema_rejected request_id=%s user_id=%s model=%s status=%s duration_ms=%s",
                    request_id,
                    user_id,
                    model,
                    exc.status_code,
                    duration_ms,
                )
                use_schema = False
                continue
            logger.exception(
                "suggest_identity api_error request_id=%s user_id=%s model=%s status=%s duration_ms=%s",
                request_id,
                user_id,
                model,
                exc.status_code,
                duration_ms,
            )
            if "credit balance" in lowered:
                raise AIUnavailableError(
                    "AI service is temporarily unavailable due to billing limits."
                ) from exc
            raise AIUnavailableError("AI service is temporarily unavailable.") from exc
        except (AITimeoutError, AIUnavailableError):
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
        stop_reason = getattr(response, "stop_reason", None)
        try:
            result = parse_and_validate_identity_payload(output_text)
        except (AIParseError, AISchemaValidationError) as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.warning(
                "suggest_identity validation_failed request_id=%s user_id=%s model=%s "
                "input_chars=%s output_chars=%s duration_ms=%s error_category=%s "
                "attempt=%s stop_reason=%s %s",
                request_id,
                user_id,
                model,
                input_len,
                output_len,
                duration_ms,
                type(exc).__name__,
                attempt,
                stop_reason,
                _parse_failure_detail(exc),
            )
            if attempt == 2:
                raise
            correction = (
                "Your previous response could not be parsed as the required JSON object. "
                "Return only that JSON object, with all five fields. "
                "Keep each reason to one sentence of 160 characters or fewer."
            )
            prior = (output_text or "").strip()
            if prior:
                messages = [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": prior[:4000]},
                    {"role": "user", "content": correction},
                ]
            else:
                messages = [{"role": "user", "content": f"{user_prompt}\n\n{correction}"}]
            if stop_reason in {"max_tokens", "length"}:
                max_tokens = _IDENTITY_RETRY_MAX_TOKENS
            continue

        duration_ms = int((time.monotonic() - started) * 1000)
        logger.info(
            "suggest_identity success request_id=%s user_id=%s model=%s "
            "input_chars=%s output_chars=%s duration_ms=%s attempt=%s stop_reason=%s",
            request_id,
            user_id,
            model,
            input_len,
            output_len,
            duration_ms,
            attempt,
            stop_reason,
        )
        return result

    if result is None:
        raise AIParseError("AI returned invalid JSON for career identity suggestions.")
    return result


# Re-export for tests that build FieldSuggestion directly
__all__ = [
    "AITimeoutError",
    "AIUnavailableError",
    "AIParseError",
    "AISchemaValidationError",
    "FieldSuggestion",
    "loads_model_json",
    "parse_and_validate_identity_payload",
    "suggest_career_identity_from_ai",
]
