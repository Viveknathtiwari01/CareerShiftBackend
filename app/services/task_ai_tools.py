"""Generate task-specific AI tools for 3B work components."""

import asyncio
import json
import logging
import re
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
MAX_TOOLS_PER_COMPONENT = 2
MAX_TOOLS_PER_TASK = 5
_PLACEHOLDER_NAMES = {"ai tool", "tool", "n/a", "na", "none", "unknown", "tbd", "todo"}
_CONTEXT_STOPWORDS = {
    "with", "that", "this", "from", "your", "into", "and", "the", "for", "task",
    "tasks", "review", "analysis", "update", "data", "work", "team", "plan",
    "planning", "report", "reports", "process", "support", "manage", "management",
    "identify", "create", "using", "help", "helps", "weekly", "monthly", "user",
    "users", "need", "needs",
}


def _tool_blob(tool: dict[str, Any]) -> str:
    return " ".join(
        str(tool.get(key) or "")
        for key in (
            "why_this_tool",
            "how_to_use",
            "task_connection",
            "fit_description",
            "expected_benefit",
            "starting_point",
        )
    ).lower()


def _context_tokens(*sources: str) -> set[str]:
    tokens: set[str] = set()
    for source in sources:
        for word in re.findall(r"[a-z0-9]{4,}", (source or "").lower()):
            if word not in _CONTEXT_STOPWORDS:
                tokens.add(word)
    return tokens


def _mentions_work(tool: dict[str, Any], *sources: str) -> bool:
    tokens = _context_tokens(*sources)
    if not tokens:
        return True
    blob = _tool_blob(tool)
    return any(token in blob for token in tokens)


def _is_actionable(tool: dict[str, Any]) -> bool:
    name = str(tool.get("name") or "").strip().lower()
    if not name or name in _PLACEHOLDER_NAMES:
        return False
    why = str(tool.get("why_this_tool") or tool.get("fit_description") or "").strip()
    how = str(tool.get("how_to_use") or tool.get("fit_description") or "").strip()
    return len(why) >= 20 and len(how) >= 40


def prepare_tool_recommendations(raw_tasks: list[Any]) -> list[dict[str, Any]]:
    """Validate model output into task-scoped, de-duplicated tool recommendations.

    Tools whose explanation does not mention the task or component are dropped
    when at least one tool on that task does mention the work. If none match,
    the actionable tools are kept so a thin title does not wipe the result.
    """
    prepared: list[dict[str, Any]] = []
    for task in raw_tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("task_id") or "").strip()
        if not task_id:
            continue
        title = str(task.get("title") or "").strip()
        kept_components: list[dict[str, Any]] = []
        candidates: list[tuple[str, dict[str, Any], bool]] = []
        component_order: list[str] = []

        for component in task.get("components") or []:
            if not isinstance(component, dict):
                continue
            name = str(component.get("name") or "").strip()
            if not name:
                continue
            component_order.append(name)
            description = str(component.get("description") or "")
            for item in component.get("tools") or []:
                if not isinstance(item, dict):
                    continue
                tool = _sanitize_tool_option(item)
                if not tool or not _is_actionable(tool):
                    continue
                if not tool.get("how_to_use"):
                    tool["how_to_use"] = tool.get("fit_description") or ""
                if not tool.get("why_this_tool"):
                    tool["why_this_tool"] = tool.get("fit_description") or ""
                candidates.append((name, tool, _mentions_work(tool, title, name, description)))

        matching = [item for item in candidates if item[2]]
        chosen = matching if matching else candidates

        by_component: dict[str, list[dict[str, Any]]] = {name: [] for name in component_order}
        seen_names: dict[str, set[str]] = {name: set() for name in component_order}
        task_count = 0
        for component_name, tool, _matched in chosen:
            if task_count >= MAX_TOOLS_PER_TASK:
                break
            bucket = by_component.setdefault(component_name, [])
            if len(bucket) >= MAX_TOOLS_PER_COMPONENT:
                continue
            key = str(tool.get("name") or "").strip().lower()
            seen = seen_names.setdefault(component_name, set())
            if key in seen:
                continue
            seen.add(key)
            bucket.append(tool)
            task_count += 1

        for component_name in component_order:
            kept_components.append(
                {"name": component_name, "tools": by_component.get(component_name, [])}
            )
        prepared.append(
            {
                "task_id": task_id,
                "title": title,
                "components": kept_components,
            }
        )
    return prepared


def apply_tool_recommendations(
    components: list[dict[str, Any]],
    recommended_components: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Copy recommended tools onto the matching work components. Unknown components are ignored."""
    tools_by_name: dict[str, list[dict[str, Any]]] = {}
    for component in recommended_components or []:
        if not isinstance(component, dict):
            continue
        key = str(component.get("name") or "").strip().lower()
        if key:
            tools_by_name[key] = list(component.get("tools") or [])

    recommended: list[str] = []
    updated: list[dict[str, Any]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        comp = dict(component)
        key = str(comp.get("name") or "").strip().lower()
        tools = tools_by_name.get(key) or []
        comp["tools"] = tools
        for tool in tools:
            name = tool.get("name")
            if name and name not in recommended:
                recommended.append(name)
        updated.append(comp)
    return updated, recommended


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
    return prepare_tool_recommendations(raw_tasks)


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
