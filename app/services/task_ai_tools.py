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
MIN_TOOLS_PER_COMPONENT = 1
MAX_TOOLS_PER_COMPONENT = 4
MAX_TOOLS_PER_TASK = 12
_PLACEHOLDER_NAMES = {"ai tool", "tool", "n/a", "na", "none", "unknown", "tbd", "todo"}
_CONTEXT_STOPWORDS = {
    "with", "that", "this", "from", "your", "into", "and", "the", "for", "task",
    "tasks", "review", "analysis", "update", "data", "work", "team", "plan",
    "planning", "report", "reports", "process", "support", "manage", "management",
    "identify", "create", "using", "help", "helps", "weekly", "monthly", "user",
    "users", "need", "needs",
}

_STRICT_CONVENTIONAL_UTILITIES: set[str] = {
    # Conventional testing runners, linters, packaging, or dev tools without AI identities
    "jest", "husky", "mocha", "chai", "junit", "pytest", "unittest", "eslint",
    "prettier", "stylelint", "npm", "yarn", "pnpm", "git", "git cli",
    "chrome devtools", "devtools", "lighthouse", "phpmyadmin", "mysql workbench",
    "pgadmin", "dbeaver", "mongodb compass", "curl",
    "webpack", "vite", "rollup", "babel", "gulp", "grunt", "jenkins",
    "circleci", "travis ci",
    # Serving runtimes, deprecated engines, or conventional Java-only runners
    "tensorflow serving", "torchserve", "triton", "triton server", "triton inference server",
    "openai codex", "codex",
    "diffblue", "diffblue cover",
}

_VENDOR_PLATFORMS_REQUIRING_EXPLICIT_AI_CAPABILITY: set[str] = {
    # Broad platforms where recommending the platform itself without specifying
    # its AI feature is conventional non-AI.
    "postman", "github", "gitlab", "bitbucket", "datadog", "new relic",
    "sonarqube", "snyk", "jira", "confluence", "excel", "word", "powerpoint",
    "salesforce", "servicenow", "workday", "sap", "oracle", "snowflake",
    "docker", "kubernetes", "miro", "trello", "asana", "monday com",
    "feedly", "datagrip", "mongodb", "mongodb atlas", "slack", "zoom", "teams", "outlook",
}

_AI_NAME_INDICATORS: set[str] = {
    "ai", "copilot", "gpt", "llm", "bot", "postbot", "assistant", "intelligence",
    "generative", "agent", "agents", "duo", "composer", "bits", "seer", "smart",
    "cortex", "illuminate", "deepscan", "einstein", "assist", "genius", "grok",
}

_AI_PHRASE_INDICATORS: tuple[str, ...] = (
    "q developer", "now assist", "talent intelligence", "deepcode", "advanced security",
)


def canonical_product_id(name: str) -> str:
    """Return a deterministic canonical identifier for tool deduplication without static catalogs."""
    raw = (name or "").strip().lower()
    if not raw:
        return ""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", raw)
    normalized = " ".join(cleaned.split())
    if not normalized:
        return ""

    for vendor_suffix in (
        "by vercel", "by openai", "by google", "by anthropic",
        "by microsoft", "by atlassian", "by amazon", "by smartbear",
    ):
        normalized = normalized.replace(vendor_suffix, "").strip()

    normalized = " ".join(normalized.split())
    tokens = normalized.split()
    if not tokens:
        return ""

    # Universal canonical mappings
    if tokens == ["github", "copilot"] or tokens == ["copilot"]:
        return "github-copilot"
    if "postbot" in tokens:
        return "postman-postbot"
    if normalized in ("chatgpt", "chat gpt", "openai chatgpt"):
        return "chatgpt"

    # Strip generic suffixes if base name exists (e.g., "cursor ai" -> "cursor", "cursor composer" -> "cursor")
    if len(tokens) > 1 and tokens[-1] in ("ai", "ide", "bot", "assistant", "agent", "platform", "tool", "app", "dev", "composer"):
        base_tokens = tokens[:-1]
        # Keep distinctive multi-word product names intact
        if base_tokens == ["claude"]:
            return "claude"
        return "-".join(base_tokens)

    return "-".join(tokens)


def _is_conventional_non_ai_tool(tool: dict[str, Any]) -> bool:
    """Identify conventional utilities that lack an active AI product capability."""
    raw_name = str(tool.get("name") or "").strip().lower()
    norm_name = re.sub(r"[^a-z0-9\s]", " ", raw_name)
    name_tokens = set(norm_name.split())

    # 2. Broad vendor platforms require explicit AI capability in their product identity
    has_ai_indicator = bool(name_tokens & _AI_NAME_INDICATORS) or any(
        phrase in raw_name for phrase in _AI_PHRASE_INDICATORS
    )

    # 1. Strict conventional utilities are NEVER AI products (unless an explicit AI capability is named)
    for util in _STRICT_CONVENTIONAL_UTILITIES:
        if raw_name == util:
            return True
        if not has_ai_indicator and (
            raw_name.startswith(f"{util} ")
            or raw_name.endswith(f" {util}")
            or f" {util} " in raw_name
            or f"/{util}" in raw_name
            or f"({util})" in raw_name
        ):
            return True

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
    if len(why) < 15 or len(how) < 20:
        logger.warning("Dropping tool with insufficient explanation: %s (why=%d, how=%d)", name, len(why), len(how))
        return False
    return True


def prepare_tool_recommendations(raw_tasks: list[Any]) -> list[dict[str, Any]]:
    """Validate model output into component-scoped, de-duplicated tool recommendations.

    Candidate filtering is evaluated per component.
    Each component gets between 1 and 3 distinct AI tools.
    Deduplication across superficial variants within a task is enforced.
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
    """Copy recommended tools onto matching work components with robust matching and backfill."""
    rec_comps = [c for c in (recommended_components or []) if isinstance(c, dict)]

    # If the task has no existing components, do NOT create fake components!
    if not components:
        return [], []

    def norm_comp_key(name: str) -> str:
        cleaned = re.sub(r"[^a-z0-9\s]", " ", (name or "").lower().replace("&", " and "))
        return " ".join(cleaned.split())

    tools_by_key: dict[str, list[dict[str, Any]]] = {}
    for comp in rec_comps:
        k = norm_comp_key(comp.get("name") or "")
        if k:
            tools_by_key[k] = list(comp.get("tools") or [])

    updated: list[dict[str, Any]] = []
    seen_cids: set[str] = set()
    recommended: list[str] = []

    for idx, component in enumerate(components):
        if not isinstance(component, dict):
            continue
        comp = dict(component)
        raw_name = str(comp.get("name") or "")
        key = norm_comp_key(raw_name)

        # 1. Exact normalized match
        tools = list(tools_by_key.get(key) or [])

        # 2. Substring or token overlap match
        if not tools and key:
            key_tokens = set(key.split())
            best_match = None
            best_overlap = 0
            for r_key, r_tools in tools_by_key.items():
                overlap = len(key_tokens & set(r_key.split()))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = r_tools
            if best_match and best_overlap > 0:
                tools = list(best_match)

        # 3. Positional fallback if index matches
        if not tools and idx < len(rec_comps):
            tools = list(rec_comps[idx].get("tools") or [])

        comp["tools"] = tools[:MAX_TOOLS_PER_COMPONENT]
        for tool in comp["tools"]:
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


def _sanitize_task_tools(
    raw_tasks: list[Any],
    input_tasks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if input_tasks:
        norm_to_id = {
            re.sub(r"[^a-z0-9]", "", str(t.get("title") or "").lower()): str(t.get("task_id") or "")
            for t in input_tasks
            if t.get("title") and t.get("task_id")
        }
        for idx, task in enumerate(raw_tasks):
            if isinstance(task, dict) and not task.get("task_id"):
                norm_title = re.sub(r"[^a-z0-9]", "", str(task.get("title") or "").lower())
                matched_id = norm_to_id.get(norm_title)
                if not matched_id and idx < len(input_tasks) and len(raw_tasks) == len(input_tasks):
                    matched_id = str(input_tasks[idx].get("task_id") or "")
                if matched_id:
                    task["task_id"] = matched_id
    return prepare_tool_recommendations(raw_tasks)


def _tasks_lacking_tools(tasks: list[dict[str, Any]], prepared: list[dict[str, Any]]) -> list[str]:
    prep_by_id = {str(item["task_id"]): item for item in prepared}
    prep_by_title = {
        re.sub(r"[^a-z0-9]", "", str(item.get("title") or "").lower()): item
        for item in prepared
        if item.get("title")
    }
    missing: list[str] = []
    for t in tasks:
        tid = str(t.get("task_id") or "")
        title = str(t.get("title") or "")
        norm_t = re.sub(r"[^a-z0-9]", "", title.lower())
        p_task = prep_by_id.get(tid) or prep_by_title.get(norm_t)
        if p_task:
            comps = p_task.get("components", [])
            has_empty_comp = any(not c.get("tools") for c in comps)
            tools = [tool for comp in comps for tool in comp.get("tools", [])]
            if comps and (not tools or has_empty_comp):
                missing.append(title or tid)
        elif t.get("components"):
            missing.append(title or tid)
    return missing


def _ensure_minimum_tools_for_prepared(
    tasks: list[dict[str, Any]],
    prepared: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Safely backfill only components that have 0 tools on final attempt.

    If at least 1 tool is already present, do not add complementary tools.
    Never create fake components if none exist.
    """
    prep_by_id = {str(item["task_id"]): item for item in prepared}
    prep_by_title = {
        re.sub(r"[^a-z0-9]", "", str(item.get("title") or "").lower()): item
        for item in prepared
        if item.get("title")
    }
    for t in tasks:
        tid = str(t.get("task_id") or "")
        title = str(t.get("title") or "")
        norm_t = re.sub(r"[^a-z0-9]", "", title.lower())
        p_task = prep_by_id.get(tid) or prep_by_title.get(norm_t)
        if not p_task:
            continue

        comps = p_task.get("components", [])
        if not comps:
            continue

        task_tools = [tool for c in comps for tool in c.get("tools", [])]
        task_cids = {canonical_product_id(str(tool.get("name") or "")) for tool in task_tools}
        task_cids.discard("")

        for c in comps:
            c_tools = c.setdefault("tools", [])
            # Requirement 1: If even 1 tool exists, DO NOT add complementary tools!
            if len(c_tools) >= 1:
                continue

            # Only if component has 0 tools, add 1 complementary tool:
            c_name = str(c.get("name") or "Work Component")
            supp = {
                "name": "Microsoft 365 Copilot",
                "access_class": "enterprise",
                "task_fit_rank": 1,
                "task_fit_reason": f"Enterprise AI assistant supporting {c_name} and executive deliverable synthesis.",
                "why_this_tool": f"Microsoft 365 Copilot accelerates {c_name} inside {title} by synthesizing documents, communications, and data.",
                "how_to_use": f"Open Word, Teams, or Excel, prompt Copilot with source materials for {c_name}, and review draft outputs.",
                "task_connection": f"{c_name} inside {title}",
                "expected_benefit": "Reduces manual drafting, email synthesis, and meeting documentation time.",
                "starting_point": f"Prompt Copilot in Microsoft 365 with the primary deliverable for {c_name}.",
                "limitations": "Requires organizational Microsoft 365 Copilot licensing and human verification of factual outputs.",
                "cost_band": "enterprise",
                "pricing_note": "Add-on license for Microsoft 365 enterprise tenants.",
                "feasibility": "org_must_enable",
                "fit_description": f"Enterprise AI assistant for accelerating {c_name}.",
                "market_note": "Widely standard enterprise tool across organizations.",
                "pros": [f"Deeply integrated with daily enterprise workflows for {c_name}", "Strong enterprise data governance and security"],
                "cons": ["Requires enterprise tenant licensing", "Outputs require human review for company context"],
            }
            c_tools.append(supp)
            task_cids.add("microsoft-365-copilot")
    return prepared


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
            sanitized = _sanitize_task_tools(parsed.get("tasks") or [], input_tasks=tasks)
            prepared = sanitized
            missing = _tasks_lacking_tools(tasks, prepared)
            if missing and attempt < max_attempts:
                logger.warning(
                    "Attempt %d/%d: tasks lacking required 1-3 AI tools per component: %s. Retrying with targeted prompt.",
                    attempt,
                    max_attempts,
                    missing,
                )
                correction_text = (
                    f"The previous response provided insufficient or missing AI tool recommendations for: {', '.join(missing)}. "
                    "MANDATORY REQUIREMENT: For EVERY work component, you MUST provide at least 1 and at most 3 distinct, "
                    "suitable, market-standard AI tools (1 to 3 tools per component). "
                    "Every task MUST have at least 2 distinct AI products total across its components. "
                    "Do NOT recommend conventional non-AI utilities (no Jest, Husky, Git CLI, basic office tools without AI). "
                    "Please return complete recommendations with 1 to 3 distinct AI tools and pros/cons for every single component."
                )
                request_kwargs["messages"] = [
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": output_text},
                    {"role": "user", "content": correction_text},
                ]
                continue
            if missing:
                logger.warning(
                    "Attempt %d/%d: tasks lacking required 2 AI tools: %s. Defensively backfilling complementary tools.",
                    attempt,
                    max_attempts,
                    missing,
                )
                sanitized = _ensure_minimum_tools_for_prepared(tasks, sanitized)
                return sanitized
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
