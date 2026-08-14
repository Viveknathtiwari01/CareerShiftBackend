import json
import logging
import re
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic, AuthenticationError

from app.core.anthropic_client import (
    build_messages_create_kwargs,
    create_async_client,
    extract_response_text,
    get_anthropic_effort,
    get_anthropic_model,
    get_anthropic_temperature,
    model_supports_sampling_params,
)
from promppts.TaskGenerationService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def _strip_markdown_json(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def _normalize_level(value: str | None, default: str = "medium") -> str:
    if not value:
        return default
    normalized = str(value).lower()
    return normalized if normalized in {"low", "medium", "high"} else default


def _parse_task_generation_json(output_text: str) -> dict[str, Any]:
    clean = _strip_markdown_json(output_text)
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("AI response was not a JSON object.")
    parsed.setdefault("tasks", [])
    parsed.setdefault("suggested_additional", [])
    if not isinstance(parsed["tasks"], list):
        raise ValueError("tasks must be a list")
    return parsed


async def generate_tasks_from_ai(
    *,
    profile_data: dict[str, Any],
    competencies: list[dict[str, Any]],
    profession_summary: str | None,
) -> dict[str, Any]:
    """Call Anthropic to generate role-specific daily work tasks."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        profile_json=json.dumps(profile_data, indent=2),
        competencies_json=json.dumps(competencies, indent=2),
        profession_summary=profession_summary or "Not available",
    )

    model = get_anthropic_model()
    if model_supports_sampling_params(model):
        logger.info("Generating tasks with model=%s", model)
    else:
        logger.info("Generating tasks with model=%s effort=%s", model, get_anthropic_effort())

    request_kwargs = build_messages_create_kwargs(
        model,
        max_tokens=4096,
        temperature=get_anthropic_temperature(),
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    client: AsyncAnthropic = create_async_client()
    try:
        response = await client.messages.create(**request_kwargs)
    except AuthenticationError as exc:
        raise ValueError(
            "AI service authentication failed. Check ANTHROPIC_API_KEY in Backend/.env."
        ) from exc
    except APIStatusError as exc:
        message = exc.message or str(exc)
        raise ValueError(f"AI service error: {message}") from exc

    output_text = extract_response_text(response)
    if not output_text:
        raise ValueError("AI returned no text content. Please try again.")
    logger.info("Task generation raw output (first 200 chars): %s", output_text[:200])

    try:
        parsed = _parse_task_generation_json(output_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse task generation JSON: %s", output_text[:500])
        raise ValueError("AI returned an invalid task response. Please try again.") from exc

    for task in parsed["tasks"] + parsed["suggested_additional"]:
        task["complexity"] = _normalize_level(task.get("complexity"))
        task["creativity"] = _normalize_level(task.get("creativity"))
        task["human_touch"] = _normalize_level(task.get("human_touch"))
        hours = task.get("hours_per_week", 0)
        try:
            task["hours_per_week"] = max(0, min(80, float(hours)))
        except (TypeError, ValueError):
            task["hours_per_week"] = 0
        confidence = task.get("confidence")
        if confidence is not None:
            try:
                task["confidence"] = max(0, min(100, int(confidence)))
            except (TypeError, ValueError):
                task["confidence"] = None

    return parsed
