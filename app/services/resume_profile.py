"""Map an uploaded resume onto career identity, tools, skills, and experience."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic, AuthenticationError

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
from app.schemas.profile import ResumeExtractedDetails, ResumeProfileResponse, SuggestIdentityResponse
from app.services.ai_career_identity import (
    AIParseError,
    AISchemaValidationError,
    AITimeoutError,
    AIUnavailableError,
    loads_model_json,
    suggest_career_identity_from_ai,
)
from app.services.resume_text import extract_resume_text
from promppts.ResumeDetailsExtractService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

EXPERIENCE_LEVELS = (
    "0-1 Years",
    "1-3 Years",
    "3-5 Years",
    "5-8 Years",
    "8-12 Years",
    "12+ Years",
)
_LIST_KEYS = (
    "tools",
    "technical_skills",
    "professional_skills",
    "soft_skills",
    "behavioural_skills",
    "digital_skills",
    "ai_tools",
)
_MAX_ITEMS = 12
_MAX_ITEM_CHARS = 60


def experience_level_for_years(years: int | None) -> str | None:
    """Map a total-years integer onto the profile experience choices."""
    if years is None or years < 0 or years > 60:
        return None
    if years <= 1:
        return "0-1 Years"
    if years <= 3:
        return "1-3 Years"
    if years <= 5:
        return "3-5 Years"
    if years <= 8:
        return "5-8 Years"
    if years <= 12:
        return "8-12 Years"
    return "12+ Years"


def empty_resume_details() -> ResumeExtractedDetails:
    return ResumeExtractedDetails()


def _clean_item_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    items: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            continue
        value = " ".join(entry.split()).strip(" -•|,;")
        if not value or len(value) > _MAX_ITEM_CHARS:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(value)
        if len(items) >= _MAX_ITEMS:
            break
    return items


def _parse_years(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        years = raw
    elif isinstance(raw, float):
        years = int(round(raw))
    elif isinstance(raw, str):
        match = re.search(r"\d+", raw)
        if not match:
            return None
        years = int(match.group(0))
    else:
        return None
    if years < 0 or years > 60:
        return None
    return years


def parse_resume_details_payload(output_text: str) -> ResumeExtractedDetails:
    """Parse model text into resume details. Raises AIParseError on invalid JSON."""
    try:
        parsed = loads_model_json(output_text)
    except json.JSONDecodeError as exc:
        raise AIParseError("AI returned invalid JSON for resume details.") from exc
    if not isinstance(parsed, dict):
        raise AIParseError("AI response was not a JSON object.")

    years = _parse_years(parsed.get("experience_years"))
    payload = {key: _clean_item_list(parsed.get(key)) for key in _LIST_KEYS}
    return ResumeExtractedDetails(
        experience_years=years,
        experience_level=experience_level_for_years(years),
        **payload,
    )


def build_resume_profile_response(
    identity: SuggestIdentityResponse,
    details: ResumeExtractedDetails | None = None,
) -> ResumeProfileResponse:
    extracted = details or empty_resume_details()
    return ResumeProfileResponse(
        industry=identity.industry,
        department=identity.department,
        functional_domain=identity.functional_domain,
        specialization=identity.specialization,
        job_title=identity.job_title,
        resume_details=extracted,
    )


async def _extract_details_from_ai(
    resume_text: str,
    *,
    request_id: str | None,
    user_id: str | None,
) -> ResumeExtractedDetails:
    get_anthropic_api_key()
    model = get_anthropic_model()
    user_prompt = USER_PROMPT_TEMPLATE.replace("{resume_text}", resume_text)
    request_kwargs = build_messages_create_kwargs(
        model,
        max_tokens=2048,
        temperature=get_anthropic_temperature(),
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if model_supports_sampling_params(model):
        logger.info(
            "resume_details start request_id=%s user_id=%s model=%s input_chars=%s",
            request_id,
            user_id,
            model,
            len(resume_text),
        )
    else:
        logger.info(
            "resume_details start request_id=%s user_id=%s model=%s effort=%s input_chars=%s",
            request_id,
            user_id,
            model,
            get_anthropic_effort(),
            len(resume_text),
        )

    client: AsyncAnthropic = create_async_client()
    started = time.monotonic()
    timeout_seconds = float(settings.SUGGEST_IDENTITY_LLM_TIMEOUT_SECONDS)
    try:
        response = await asyncio.wait_for(
            client.messages.create(**request_kwargs),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise AITimeoutError("AI service timed out. Please try again.") from exc
    except AuthenticationError as exc:
        raise AIUnavailableError(
            "AI service authentication failed. Please contact support."
        ) from exc
    except APIStatusError as exc:
        message = exc.message or str(exc)
        if "credit balance" in message.lower():
            raise AIUnavailableError(
                "AI service is temporarily unavailable due to billing limits."
            ) from exc
        raise AIUnavailableError("AI service is temporarily unavailable.") from exc
    except (AITimeoutError, AIUnavailableError):
        raise
    except Exception as exc:
        raise AIUnavailableError("AI service is temporarily unavailable.") from exc

    output_text = extract_response_text(response)
    details = parse_resume_details_payload(output_text or "")
    logger.info(
        "resume_details success request_id=%s user_id=%s duration_ms=%s",
        request_id,
        user_id,
        int((time.monotonic() - started) * 1000),
    )
    return details


async def suggest_profile_from_resume(
    data: bytes,
    filename: str | None,
    *,
    request_id: str | None = None,
    user_id: str | None = None,
) -> ResumeProfileResponse:
    """
    Read a resume and map identity the same way as written background,
    plus experience, tools, and skills when the resume states them.
    """
    resume_text = extract_resume_text(data, filename)
    logger.info(
        "resume_profile start request_id=%s user_id=%s extension=%s input_chars=%s",
        request_id,
        user_id,
        filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else "",
        len(resume_text),
    )

    identity_task = asyncio.create_task(
        suggest_career_identity_from_ai(
            resume_text,
            request_id=request_id,
            user_id=user_id,
        )
    )
    details_task = asyncio.create_task(
        _extract_details_from_ai(
            resume_text,
            request_id=request_id,
            user_id=user_id,
        )
    )

    try:
        identity = await identity_task
    except Exception:
        details_task.cancel()
        try:
            await details_task
        except (asyncio.CancelledError, Exception):
            pass
        raise

    try:
        details = await details_task
    except (AITimeoutError, AIUnavailableError, AIParseError, AISchemaValidationError) as exc:
        logger.warning(
            "resume_details fallback request_id=%s user_id=%s error_category=%s",
            request_id,
            user_id,
            type(exc).__name__,
        )
        details = empty_resume_details()
    except Exception:
        logger.exception(
            "resume_details unexpected_fallback request_id=%s user_id=%s",
            request_id,
            user_id,
        )
        details = empty_resume_details()

    return build_resume_profile_response(identity, details)
