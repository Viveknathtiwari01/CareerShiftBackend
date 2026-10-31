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
    create_async_client,
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
MAX_TOOLS_PER_TASK = 8
_PLACEHOLDER_NAMES = {"ai tool", "tool", "n/a", "na", "none", "unknown", "tbd", "todo"}
_CONTEXT_STOPWORDS = {
    "with", "that", "this", "from", "your", "into", "and", "the", "for", "task",
    "tasks", "review", "analysis", "update", "data", "work", "team", "plan",
    "planning", "report", "reports", "process", "support", "manage", "management",
    "identify", "create", "using", "help", "helps", "weekly", "monthly", "user",
    "users", "need", "needs",
}

_STRICT_CONVENTIONAL_UTILITIES: set[str] = {
    # Conventional testing runners, linters, packaging, or dev tools without standalone AI identities
    "jest", "husky", "mocha", "chai", "junit", "pytest", "unittest", "eslint",
    "prettier", "stylelint", "npm", "yarn", "pnpm", "git", "git cli",
    "chrome devtools", "devtools", "lighthouse", "phpmyadmin", "mysql workbench",
    "pgadmin", "dbeaver", "mongodb compass", "curl", "swagger", "swagger ui",
    "webpack", "vite", "rollup", "babel", "gulp", "grunt", "jenkins",
    "circleci", "travis ci", "trello", "asana", "monday com", "slack", "zoom",
    "teams", "outlook",
}

_VENDOR_PLATFORMS_REQUIRING_EXPLICIT_AI_CAPABILITY: set[str] = {
    # Broad platforms where recommending the platform itself without specifying
    # its AI feature is conventional non-AI.
    "postman", "github", "gitlab", "bitbucket", "datadog", "new relic",
    "sonarqube", "snyk", "jira", "confluence", "excel", "word", "powerpoint",
    "salesforce", "servicenow", "workday", "sap", "oracle", "snowflake",
    "docker", "kubernetes",
}

_AI_NAME_INDICATORS: set[str] = {
    "ai", "copilot", "gpt", "llm", "bot", "postbot", "assistant", "intelligence",
    "generative", "agent", "agents", "duo", "composer", "bits", "seer", "smart",
    "cortex", "illuminate", "deepscan", "einstein", "assist", "genius", "grok",
}

_AI_PHRASE_INDICATORS: tuple[str, ...] = (
    "q developer", "now assist", "talent intelligence", "deepcode", "advanced security",
)

_CANONICAL_ALIASES: dict[str, str] = {
    # IDE / Coding
    "cursor": "cursor",
    "cursor ai": "cursor",
    "cursor composer": "cursor",
    "cursor ide": "cursor",
    "github copilot": "github-copilot",
    "copilot": "github-copilot",
    "github copilot for business": "github-copilot",
    "github copilot enterprise": "github-copilot",
    "windsurf": "windsurf",
    "windsurf ide": "windsurf",
    "codeium windsurf": "windsurf",
    "codeium": "codeium",
    "v0": "v0",
    "v0 by vercel": "v0",
    "v0 dev": "v0",
    "claude": "claude",
    "anthropic claude": "claude",
    "claude 3": "claude",
    "claude 3 5 sonnet": "claude",
    "claude 3 7 sonnet": "claude",
    "claude code": "claude-code",
    "chatgpt": "chatgpt",
    "chat gpt": "chatgpt",
    "openai chatgpt": "chatgpt",
    "gpt 4": "chatgpt",
    "gpt 4o": "chatgpt",
    # Testing & Quality
    "qodo": "qodo",
    "qodo gen": "qodo",
    "qodo cover": "qodo",
    "codiumai": "qodo",
    "codium ai": "qodo",
    "postman ai": "postman-postbot",
    "postman postbot": "postman-postbot",
    "postbot": "postman-postbot",
    "postman ai postbot": "postman-postbot",
    "testsprite": "testsprite",
    "diffblue cover": "diffblue-cover",
    "diffblue": "diffblue-cover",
    "sonarqube ai": "sonarqube-ai",
    "sonar ai": "sonarqube-ai",
    "sonar": "sonarqube-ai",
    "snyk ai": "snyk-ai",
    "snyk deepcode ai": "snyk-ai",
    # Observability & Cloud
    "datadog bits ai": "datadog-bits",
    "datadog bits": "datadog-bits",
    "datadog ai": "datadog-bits",
    "new relic apm ai": "newrelic-ai",
    "new relic grok": "newrelic-ai",
    "new relic ai": "newrelic-ai",
    "sentry ai": "sentry-ai",
    "sentry seer": "sentry-ai",
    "amazon q": "amazon-q",
    "amazon q developer": "amazon-q",
    "gitlab duo": "gitlab-duo",
    "github actions copilot": "github-actions-copilot",
    "github advanced security": "ghas-ai",
    "ghas": "ghas-ai",
    # Enterprise & Workforce
    "workday illuminate": "workday-illuminate",
    "workday ai": "workday-illuminate",
    "eightfold ai": "eightfold",
    "eightfold": "eightfold",
    "visier": "visier",
    "visier ai": "visier",
    "cornerstone galaxy ai": "cornerstone-galaxy",
    "cornerstone galaxy": "cornerstone-galaxy",
    "sap successfactors talent intelligence hub": "sap-talent-intelligence",
    "sap successfactors": "sap-talent-intelligence",
    "microsoft 365 copilot": "ms-365-copilot",
    "m365 copilot": "ms-365-copilot",
    "atlassian intelligence": "atlassian-intelligence",
    "jira ai": "atlassian-intelligence",
    "servicenow now assist": "servicenow-now-assist",
    "now assist": "servicenow-now-assist",
    # Specialist & DB
    "outerbase": "outerbase",
    "outerbase ai": "outerbase",
    "supabase ai": "supabase-ai",
    "datagrip ai": "datagrip-ai",
    "supermaven": "supermaven",
    "supermaven ai": "supermaven",
    "lovable": "lovable",
    "lovable dev": "lovable",
    "aider": "aider",
    "aider ai": "aider",
}


def canonical_product_id(name: str) -> str:
    """Return a deterministic canonical identifier for tool deduplication."""
    raw = (name or "").strip().lower()
    if not raw:
        return ""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", raw)
    normalized = " ".join(cleaned.split())

    if normalized in _CANONICAL_ALIASES:
        return _CANONICAL_ALIASES[normalized]

    for vendor_suffix in (
        "by vercel", "by openai", "by google", "by anthropic",
        "by microsoft", "by atlassian", "by amazon",
    ):
        normalized = normalized.replace(vendor_suffix, "").strip()

    normalized = " ".join(normalized.split())
    if normalized in _CANONICAL_ALIASES:
        return _CANONICAL_ALIASES[normalized]

    tokens = normalized.split()
    if len(tokens) > 1 and tokens[-1] in ("ai", "ide", "bot", "assistant", "agent", "platform", "tool", "app", "dev"):
        base = " ".join(tokens[:-1])
        if base in _CANONICAL_ALIASES:
            return _CANONICAL_ALIASES[base]
        return "-".join(base.split())

    return "-".join(tokens)


def _is_conventional_non_ai_tool(tool: dict[str, Any]) -> bool:
    """Identify conventional utilities that lack an active AI product capability."""
    raw_name = str(tool.get("name") or "").strip().lower()
    norm_name = re.sub(r"[^a-z0-9\s]", " ", raw_name)
    name_tokens = set(norm_name.split())

    # 1. Strict conventional utilities are NEVER AI products
    for util in _STRICT_CONVENTIONAL_UTILITIES:
        if (
            raw_name == util
            or raw_name.startswith(f"{util} ")
            or raw_name.endswith(f" {util}")
            or f" {util} " in raw_name
            or f"/{util}" in raw_name
            or f"({util})" in raw_name
        ):
            return True

    # 2. Broad vendor platforms require explicit AI capability in their product identity
    has_ai_indicator = bool(name_tokens & _AI_NAME_INDICATORS) or any(
        phrase in raw_name for phrase in _AI_PHRASE_INDICATORS
    )
    for vendor in _VENDOR_PLATFORMS_REQUIRING_EXPLICIT_AI_CAPABILITY:
        if (
            raw_name == vendor
            or raw_name.startswith(f"{vendor} ")
            or raw_name.endswith(f" {vendor}")
            or f" {vendor} " in raw_name
            or f"/{vendor}" in raw_name
            or f"({vendor})" in raw_name
        ):
            if not has_ai_indicator:
                return True

    return False


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
    if _is_conventional_non_ai_tool(tool):
        logger.info("Dropping non-AI conventional utility: %s", name)
        return False
    why = str(tool.get("why_this_tool") or tool.get("fit_description") or "").strip()
    how = str(tool.get("how_to_use") or tool.get("fit_description") or "").strip()
    # Require substantive explanations — short ones are generic placeholders
    return len(why) >= 30 and len(how) >= 40


def prepare_tool_recommendations(raw_tasks: list[Any]) -> list[dict[str, Any]]:
    """Validate model output into task-scoped, de-duplicated tool recommendations.

    Candidate filtering is evaluated per component so that work matches on one
    component never discard valid actionable tools on other components.
    Deduplication across the task is enforced by canonical product identity.
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
        component_order: list[str] = []
        candidates_by_comp: dict[str, list[tuple[dict[str, Any], bool]]] = {}

        for component in task.get("components") or []:
            if not isinstance(component, dict):
                continue
            name = str(component.get("name") or "").strip()
            if not name:
                continue
            component_order.append(name)
            description = str(component.get("description") or "")
            candidates_by_comp[name] = []

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
                matches_work = _mentions_work(tool, title, name, description)
                candidates_by_comp[name].append((tool, matches_work))

        by_component: dict[str, list[dict[str, Any]]] = {name: [] for name in component_order}
        seen_canonical_task: set[str] = set()
        task_count = 0

        for component_name in component_order:
            comp_candidates = candidates_by_comp.get(component_name, [])
            matching = [t for t, matched in comp_candidates if matched]
            chosen = matching if matching else [t for t, _ in comp_candidates]

            bucket = by_component.setdefault(component_name, [])
            for tool in chosen:
                if task_count >= MAX_TOOLS_PER_TASK:
                    break
                if len(bucket) >= MAX_TOOLS_PER_COMPONENT:
                    break
                cid = canonical_product_id(str(tool.get("name") or ""))
                if not cid or cid in seen_canonical_task:
                    continue
                seen_canonical_task.add(cid)
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
    seen_cids: set[str] = set()
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
            if not name:
                continue
            cid = canonical_product_id(name)
            if cid and cid not in seen_cids:
                seen_cids.add(cid)
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


def _tasks_lacking_tools(tasks: list[dict[str, Any]], prepared: list[dict[str, Any]]) -> list[str]:
    prep_by_id = {str(item["task_id"]): item for item in prepared}
    missing: list[str] = []
    for t in tasks:
        tid = str(t.get("task_id") or "")
        title = str(t.get("title") or "")
        p_task = prep_by_id.get(tid)
        tool_count = 0
        if p_task:
            tools = [tool for comp in p_task.get("components", []) for tool in comp.get("tools", [])]
            distinct_cids = {canonical_product_id(str(tool.get("name") or "")) for tool in tools}
            distinct_cids.discard("")
            tool_count = len(distinct_cids)
        if tool_count < 2:
            missing.append(title or tid)
    return missing


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

    client = create_async_client(
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
                detail="AI service authentication failed. Check OPENAI_API_KEY or ANTHROPIC_API_KEY in Backend/.env.",
            ) from exc
        except APIStatusError as exc:
            message = exc.message or str(exc)
            if "credit balance" in message.lower():
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="AI credit balance is too low. Please add credits or update OPENAI_API_KEY / ANTHROPIC_API_KEY in Backend/.env.",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {message}",
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
            sanitized = _sanitize_task_tools(parsed.get("tasks") or [])
            prepared = prepare_tool_recommendations(sanitized)
            missing = _tasks_lacking_tools(tasks, prepared)
            if missing and attempt < max_attempts:
                logger.warning(
                    "Attempt %d/%d: tasks lacking minimum 2 distinct AI tools: %s. Retrying with targeted prompt.",
                    attempt,
                    max_attempts,
                    missing,
                )
                correction_text = (
                    f"The previous response provided fewer than 2 valid, task-specific AI tools for: {', '.join(missing)}. "
                    "Every task MUST have at least 2 distinct, popular, task-specific AI products (Enterprise AI or External AI). "
                    "Do NOT recommend conventional non-AI utilities (no Jest, Husky, Git, phpMyAdmin, vanilla Chrome DevTools). "
                    "Please return complete recommendations with at least 2 distinct AI tools for every task."
                )
                request_kwargs["messages"] = [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": output_text},
                    {"role": "user", "content": correction_text},
                ]
                continue
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        f"AI could not find at least two validated AI tool recommendations for task(s): {', '.join(missing)}. "
                        "Task analysis incomplete. Please try again."
                    ),
                )
            return sanitized
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
