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
from app.services.task_3b_verification import (
    sanitize_llm_analyses,
    validate_analyses_with_pydantic,
)
from promppts.Task3BClassificationService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


from fastapi import HTTPException, status

def _strip_markdown_json(text: str) -> str:
    clean = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
    if match:
        clean = match.group(1).strip()
    else:
        start = clean.find('{')
        end = clean.rfind('}')
        if start != -1 and end != -1 and end > start:
            clean = clean[start:end+1]
    return clean.strip()


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
    grounding_payload: dict[str, Any],
) -> dict[str, Any]:
    """Call Anthropic to classify tasks into BUILD/BOT/BLEND with optional components."""
    tasks = grounding_payload.get("reviewed_tasks") or []
    user_prompt = USER_PROMPT_TEMPLATE.format(
        grounding_json=json.dumps(grounding_payload, indent=2),
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
    max_attempts = 2
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.messages.create(**request_kwargs)
        except AuthenticationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI service authentication failed. Check ANTHROPIC_API_KEY in Backend/.env."
            ) from exc
        except APIStatusError as exc:
            message = exc.message or str(exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {message}"
            ) from exc

        output_text = extract_response_text(response)
        if not output_text:
            if attempt < max_attempts:
                logger.warning("AI returned no text content, retrying...")
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned no text content. Please try again."
            )
        
        logger.info("3B classification raw output (first 200 chars): %s", output_text[:200])

        try:
            parsed = _parse_3b_json(output_text)
            break
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to parse 3B JSON (attempt %d): %s...", attempt, output_text[:500])
            if attempt < max_attempts:
                logger.warning("Retrying 3B classification due to parsing error...")
                continue
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI returned an invalid 3B analysis response. Please try again."
            ) from exc

    summary_confidence = parsed.get("summary_confidence")
    if summary_confidence is not None:
        try:
            parsed["summary_confidence"] = max(0, min(100, int(summary_confidence)))
        except (TypeError, ValueError):
            parsed["summary_confidence"] = None

    raw_analyses = [item for item in parsed.get("analyses", []) if isinstance(item, dict)]
    sanitized = sanitize_llm_analyses(raw_analyses)
    try:
        validated = validate_analyses_with_pydantic(sanitized)
    except Exception as exc:
        logger.warning("Pydantic validation fallback to sanitized output: %s", exc)
        validated = sanitized

    parsed["analyses"] = validated
    return parsed
