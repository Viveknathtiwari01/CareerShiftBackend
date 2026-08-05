import json
import logging
import re
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic, AuthenticationError

from app.core.anthropic_client import (
    build_messages_create_kwargs,
    create_async_client,
    get_anthropic_effort,
    get_anthropic_model,
    get_anthropic_temperature,
    model_supports_sampling_params,
)
from app.core.constants import CATEGORY_BLEND, CATEGORY_BOT, CATEGORY_BUILD, VALID_3B_CATEGORIES
from promppts.Task3BClassificationService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


def _strip_markdown_json(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
    return clean.strip()


def _normalize_category(value: str | None) -> str:
    if not value:
        return CATEGORY_BLEND
    upper = str(value).upper().strip()
    if upper in VALID_3B_CATEGORIES:
        return upper
    if "BUILD" in upper:
        return CATEGORY_BUILD
    if "BOT" in upper:
        return CATEGORY_BOT
    return CATEGORY_BLEND


def _normalize_level(value: str | None, default: str = "Medium") -> str:
    if not value:
        return default
    normalized = str(value).strip().capitalize()
    return normalized if normalized in {"Low", "Medium", "High"} else default


def _parse_3b_json(output_text: str) -> dict[str, Any]:
    clean = _strip_markdown_json(output_text)
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("AI response was not a JSON object.")
    parsed.setdefault("analyses", [])
    if not isinstance(parsed["analyses"], list):
        raise ValueError("analyses must be a list")
    return parsed


async def classify_tasks_3b_from_ai(
    *,
    profile_data: dict[str, Any],
    profession_summary: str | None,
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Call Anthropic to classify tasks into BUILD/BOT/BLEND."""
    tasks_payload = [
        {
            "task_index": idx,
            "title": t.get("title"),
            "description": t.get("description"),
            "category": t.get("category"),
            "hours_per_week": t.get("hours_per_week"),
            "complexity": t.get("complexity"),
            "creativity": t.get("creativity"),
            "human_touch": t.get("human_touch"),
            "frequency": t.get("frequency"),
            "business_criticality": t.get("business_criticality"),
            "ai_assistance": t.get("ai_assistance"),
            "confidence_score": t.get("confidence_score"),
        }
        for idx, t in enumerate(tasks)
    ]

    user_prompt = USER_PROMPT_TEMPLATE.format(
        profile_json=json.dumps(profile_data, indent=2),
        profession_summary=profession_summary or "Not available",
        tasks_json=json.dumps(tasks_payload, indent=2),
    )

    model = get_anthropic_model()
    if model_supports_sampling_params(model):
        logger.info("Running 3B classification with model=%s tasks=%d", model, len(tasks))
    else:
        logger.info(
            "Running 3B classification with model=%s effort=%s tasks=%d",
            model,
            get_anthropic_effort(),
            len(tasks),
        )

    request_kwargs = build_messages_create_kwargs(
        model,
        max_tokens=8192,
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

    output_text = response.content[0].text
    logger.info("3B classification raw output (first 200 chars): %s", output_text[:200])

    try:
        parsed = _parse_3b_json(output_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse 3B JSON: %s", output_text[:500])
        raise ValueError("AI returned an invalid 3B analysis response. Please try again.") from exc

    summary_confidence = parsed.get("summary_confidence")
    if summary_confidence is not None:
        try:
            parsed["summary_confidence"] = max(0, min(100, int(summary_confidence)))
        except (TypeError, ValueError):
            parsed["summary_confidence"] = None

    normalized_analyses = []
    for item in parsed["analyses"]:
        if not isinstance(item, dict):
            continue
        actions = item.get("next_actions") or []
        if isinstance(actions, list):
            actions = [str(a).strip() for a in actions if str(a).strip()][:3]
        while len(actions) < 3:
            actions.append("Review AI tools that could support this task.")

        auto_potential = item.get("auto_potential")
        try:
            auto_potential = max(0, min(100, int(auto_potential))) if auto_potential is not None else None
        except (TypeError, ValueError):
            auto_potential = None

        tools = item.get("recommended_tools") or []
        if not isinstance(tools, list):
            tools = []
        tools = [str(t).strip() for t in tools if str(t).strip()][:3]

        normalized_analyses.append(
            {
                "task_index": int(item.get("task_index", 0)),
                "category": _normalize_category(item.get("category")),
                "rationale": (item.get("rationale") or "").strip() or None,
                "reason": (item.get("reason") or "").strip() or None,
                "next_actions": actions,
                "auto_potential": auto_potential,
                "risk_level": _normalize_level(item.get("risk_level")),
                "future_impact": _normalize_level(item.get("future_impact")),
                "recommended_tools": tools,
            }
        )

    parsed["analyses"] = normalized_analyses
    return parsed
