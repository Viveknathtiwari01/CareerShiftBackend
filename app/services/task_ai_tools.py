"""Generate industry-standard AI tools for 3B work components."""

import asyncio
import json
import logging
from typing import Any

from anthropic import APIConnectionError, APIStatusError, APITimeoutError, AsyncAnthropic, AuthenticationError
from fastapi import HTTPException, status

from app.core.anthropic_client import (
    build_messages_create_kwargs,
    extract_response_text,
    get_anthropic_api_key,
    get_anthropic_effort,
    get_anthropic_model,
    get_anthropic_temperature,
    long_request_timeout,
    model_supports_sampling_params,
)
from app.services.ai_career_identity import loads_model_json
from app.services.task_3b_verification import _sanitize_tool_option
from promppts.TaskAIToolsService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

CHUNK_SIZE = 3


def _parse_tools_json(output_text: str) -> dict[str, Any]:
    """Parse a tools reply. Accepts fences, prose around the object, and common JSON mistakes."""
    parsed = loads_model_json(output_text)
    if isinstance(parsed, list):
        return {"tasks": parsed}
    if not isinstance(parsed, dict):
        raise ValueError("AI response was not a JSON object.")
    if parsed.get("task_id") and "tasks" not in parsed:
        return {"tasks": [parsed]}
    tasks = parsed.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    return parsed


def _parse_failure_detail(exc: Exception) -> str:
    if isinstance(exc, json.JSONDecodeError):
        return f"json_error={exc.msg} line={exc.lineno} col={exc.colno}"
    return f"error={type(exc).__name__}"


def _sanitize_task_tools(raw_tasks: list[Any]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for task in raw_tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if not task_id:
            continue
        components: list[dict[str, Any]] = []
        for component in task.get("components") or []:
            if not isinstance(component, dict):
                continue
            name = str(component.get("name") or "").strip()
            if not name:
                continue
            tools: list[dict[str, Any]] = []
            for item in component.get("tools") or []:
                if not isinstance(item, dict):
                    continue
                tool = _sanitize_tool_option(item)
                if tool and tool.get("name") and tool.get("pros") and tool.get("cons"):
                    tools.append(tool)
            components.append({"name": name, "tools": tools[:3]})
        cleaned.append(
            {
                "task_id": task_id,
                "title": str(task.get("title") or "").strip(),
                "components": components,
            }
        )
    return cleaned


async def _call_tools_chunk(*, profile: dict[str, Any], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    user_prompt = USER_PROMPT_TEMPLATE.format(
        profile_json=json.dumps(profile, indent=2),
        tasks_json=json.dumps(tasks, indent=2),
    )
    model = get_anthropic_model()
    logger.info(
        "Generating AI tools with model=%s tasks=%d",
        model,
        len(tasks),
    )
    request_kwargs = build_messages_create_kwargs(
        model,
        max_tokens=8192,
        temperature=get_anthropic_temperature(),
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if not model_supports_sampling_params(model):
        logger.info("AI tools generation effort=%s", get_anthropic_effort())

    client = AsyncAnthropic(
        api_key=get_anthropic_api_key(),
        timeout=long_request_timeout(),
        max_retries=2,
    )
    max_attempts = 3
    parsed: dict[str, Any] | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.messages.create(**request_kwargs)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI service authentication failed. Check ANTHROPIC_API_KEY in Backend/.env.",
            ) from exc
        except APIStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {exc.message or str(exc)}",
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            logger.warning(
                "AI tools connection issue (attempt %d/%d): %s",
                attempt,
                max_attempts,
                exc,
            )
            if attempt < max_attempts:
                await asyncio.sleep(1.5 * attempt)
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI service did not respond in time while choosing tools. Please try again.",
            ) from exc

        output_text = extract_response_text(response)
        stop_reason = getattr(response, "stop_reason", None)
        if not output_text:
            if attempt < max_attempts:
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned no tool recommendations. Please try again.",
            )
        try:
            parsed = _parse_tools_json(output_text)
            break
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Failed to parse AI tools JSON attempt=%s tasks=%s stop_reason=%s output_chars=%s %s",
                attempt,
                len(tasks),
                stop_reason,
                len(output_text),
                _parse_failure_detail(exc),
            )
            if len(tasks) > 1:
                midpoint = max(1, len(tasks) // 2)
                logger.info(
                    "Splitting AI tools chunk of %s into %s and %s after invalid JSON",
                    len(tasks),
                    midpoint,
                    len(tasks) - midpoint,
                )
                first = await _call_tools_chunk(profile=profile, tasks=tasks[:midpoint])
                second = await _call_tools_chunk(profile=profile, tasks=tasks[midpoint:])
                return first + second
            if attempt < max_attempts:
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned an invalid tool recommendation. Please try again.",
            ) from exc

    if parsed is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned no tool recommendations. Please try again.",
        )
    return _sanitize_task_tools(parsed.get("tasks") or [])


async def recommend_tools_for_tasks(
    *,
    profile: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return sanitized tool recommendations keyed by task_id and component name."""
    if not tasks:
        return []

    merged: list[dict[str, Any]] = []
    for index in range(0, len(tasks), CHUNK_SIZE):
        chunk = tasks[index : index + CHUNK_SIZE]
        merged.extend(await _call_tools_chunk(profile=profile, tasks=chunk))
    return merged
