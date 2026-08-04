import json
import logging
import re
from typing import Any

from anthropic import AsyncAnthropic, AuthenticationError, APIStatusError

from app.core.anthropic_client import (
    create_async_client,
    get_anthropic_model,
    get_anthropic_temperature,
)
from prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def _get_client() -> AsyncAnthropic:
    return create_async_client()


def _strip_markdown_json(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def _parse_skills_json(output_text: str) -> dict[str, Any]:
    clean = _strip_markdown_json(output_text)
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("AI response was not a JSON object.")

    expected_keys = (
        "technicalSkills",
        "professionalSkills",
        "softSkills",
        "behaviouralSkills",
        "digitalSkills",
        "aiTools",
    )
    for key in expected_keys:
        parsed.setdefault(key, [])
    return parsed


async def generate_skills_from_ai(
    job_title: str,
    industry: str,
    business_function: str,
    functional_domain: str,
    specialization: str,
    experience: str,
) -> dict[str, Any]:
    """Call Anthropic to generate skill categories for the user's career profile."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        job_title=job_title,
        industry=industry,
        business_function=business_function,
        functional_domain=functional_domain,
        specialization=specialization,
        experience=experience,
    )

    from app.core.anthropic_client import get_anthropic_api_key

    try:
        get_anthropic_api_key()
    except ValueError as exc:
        raise ValueError("ANTHROPIC_API_KEY is not configured on the server.") from exc

    model = get_anthropic_model()
    temperature = get_anthropic_temperature()
    api_key = get_anthropic_api_key()
    masked_key = api_key[:12] + "****" if api_key.startswith("sk-") else "****"
    logger.info("Generating skills with model=%s temperature=%s key=%s", model, temperature, masked_key)

    client = _get_client()
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=2048,
            temperature=temperature,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except AuthenticationError as exc:
        logger.error("Anthropic authentication failed: %s", exc)
        raise ValueError(
            "AI service authentication failed. The ANTHROPIC_API_KEY in Backend/.env is invalid or revoked."
        ) from exc
    except APIStatusError as exc:
        logger.exception("Anthropic API error status=%s", exc.status_code)
        message = exc.message or str(exc)
        if "credit balance" in message.lower():
            raise ValueError(
                "Anthropic API credit balance is too low. Add credits at console.anthropic.com/settings/billing."
            ) from exc
        raise ValueError(f"AI service error: {message}") from exc
    except Exception as exc:
        logger.exception("Unexpected error calling Anthropic API")
        raise ValueError("AI service is temporarily unavailable.") from exc

    output_text = response.content[0].text
    logger.info("Raw model output (first 200 chars): %s", output_text[:200])

    try:
        return _parse_skills_json(output_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse skills JSON: %s", output_text[:500])
        raise ValueError("AI returned an invalid skills response. Please try again.") from exc
