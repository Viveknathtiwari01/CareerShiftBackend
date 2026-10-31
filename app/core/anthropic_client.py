"""Shared AI client configuration for app and services/ (supports OpenAI and Anthropic, prioritizing OpenAI)."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import httpx
import anthropic
from anthropic import Anthropic, AsyncAnthropic, Timeout
import openai
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

# Ensure Backend/.env is loaded before reading settings (services/client.py lives outside app/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=False)

from app.core.config import settings  # noqa: E402

logger = logging.getLogger(__name__)


def get_ai_provider() -> str:
    """
    Return active AI provider: checks for OpenAI first, then Anthropic.

    If both keys are present, OpenAI is prioritized.
    """
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
        return "openai"
    if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip():
        return "anthropic"
    # Fallback to OpenAI if configured with empty string vs None
    return "openai" if settings.OPENAI_API_KEY is not None and settings.OPENAI_API_KEY != "" else "anthropic"


def get_ai_api_key() -> str:
    """Get active AI API key, checking OpenAI first, then Anthropic."""
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
        return settings.OPENAI_API_KEY.strip()
    if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip():
        return settings.ANTHROPIC_API_KEY.strip()
    raise ValueError(
        "Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is configured in Backend/.env"
    )


def get_anthropic_api_key() -> str:
    """Backward-compatible alias for the active AI API key."""
    return get_ai_api_key()


def get_openai_api_key() -> str | None:
    return settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else None


def get_ai_model() -> str:
    """Return model for active provider."""
    provider = get_ai_provider()
    if provider == "openai":
        return settings.OPENAI_MODEL or "gpt-4o-mini"
    return settings.ANTHROPIC_MODEL or "claude-sonnet-5"


def get_anthropic_model() -> str:
    """Backward-compatible alias for get_ai_model()."""
    return get_ai_model()


def get_ai_temperature() -> float:
    """Return temperature for active provider."""
    provider = get_ai_provider()
    if provider == "openai":
        return float(settings.OPENAI_TEMPERATURE)
    return float(settings.ANTHROPIC_TEMPERATURE)


def get_anthropic_temperature() -> float:
    """Backward-compatible alias for get_ai_temperature()."""
    return get_ai_temperature()


def get_anthropic_effort() -> str:
    return settings.ANTHROPIC_EFFORT


# Models that reject temperature/top_p/top_k (Claude 5 and Opus 4.7+).
_SAMPLING_PARAM_UNSUPPORTED = re.compile(
    r"^claude-(?:sonnet-5|opus-5|fable-5|opus-4-[78](?:-\d{8})?)$"
)


def model_supports_sampling_params(model: str) -> bool:
    """Return False when the API rejects temperature/top_p/top_k for this model."""
    if not model.startswith("claude-"):
        return True
    return _SAMPLING_PARAM_UNSUPPORTED.match(model) is None


def build_messages_create_kwargs(model: str, **kwargs: Any) -> dict[str, Any]:
    """
    Build kwargs for messages.create(), omitting deprecated params per model.

    Claude Sonnet/Opus/Fable 5 and Opus 4.7+ reject temperature; use effort instead.
    """
    if model_supports_sampling_params(model):
        return {"model": model, **kwargs}

    kwargs.pop("temperature", None)
    kwargs.pop("top_p", None)
    kwargs.pop("top_k", None)

    effort = get_anthropic_effort()
    if effort:
        kwargs.setdefault("output_config", {"effort": effort})

    return {"model": model, **kwargs}


class _TextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text

    def __repr__(self) -> str:
        snippet = self.text[:50] if self.text else ""
        return f"_TextBlock(type='text', text={snippet!r}...)"


class _Usage:
    def __init__(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _AIResponse:
    def __init__(
        self,
        text: str,
        stop_reason: str = "end_turn",
        input_tokens: int = 0,
        output_tokens: int = 0,
        raw: Any = None,
    ) -> None:
        self.content = [_TextBlock(text)]
        self.stop_reason = stop_reason
        self.usage = _Usage(input_tokens, output_tokens)
        self.raw = raw


def _translate_openai_error(exc: Exception) -> Exception:
    """Translate OpenAI errors to Anthropic-compatible errors so existing callers' except blocks work transparently."""
    dummy_req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    if isinstance(exc, openai.AuthenticationError):
        dummy_resp = httpx.Response(401, request=dummy_req)
        err = anthropic.AuthenticationError(
            f"OpenAI authentication failed: {exc}",
            response=dummy_resp,
            body={"message": str(exc)},
        )
        err.__cause__ = exc
        return err

    if isinstance(exc, openai.RateLimitError):
        dummy_resp = httpx.Response(429, request=dummy_req)
        err = anthropic.APIStatusError(
            f"OpenAI rate limit / credit balance error: {exc}",
            response=dummy_resp,
            body={"message": str(exc)},
        )
        err.__cause__ = exc
        return err

    if isinstance(exc, openai.APIStatusError):
        status_code = getattr(exc, "status_code", 500)
        dummy_resp = httpx.Response(status_code, request=dummy_req)
        err = anthropic.APIStatusError(
            f"OpenAI API error ({status_code}): {exc}",
            response=dummy_resp,
            body={"message": str(exc)},
        )
        err.__cause__ = exc
        return err

    if isinstance(exc, openai.APITimeoutError):
        err = anthropic.APITimeoutError(dummy_req)
        err.__cause__ = exc
        return err

    if isinstance(exc, openai.APIConnectionError):
        err = anthropic.APIConnectionError(request=dummy_req)
        err.__cause__ = exc
        return err

    return exc


def _prepare_openai_call_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    # 1. Model resolution
    model = kwargs.get("model")
    if not model or model.startswith("claude-"):
        model = settings.OPENAI_MODEL or "gpt-4o-mini"

    # 2. Messages formatting
    messages = kwargs.get("messages") or []
    system = kwargs.get("system")

    openai_messages: list[dict[str, str]] = []
    if system:
        openai_messages.append({"role": "system", "content": str(system)})

    for m in messages:
        if isinstance(m, dict):
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                content = "".join(text_parts)
            openai_messages.append({"role": role, "content": str(content)})

    call_kwargs: dict[str, Any] = {
        "model": model,
        "messages": openai_messages,
    }

    # 3. max_tokens
    max_tokens = kwargs.get("max_tokens")
    if max_tokens is not None:
        call_kwargs["max_tokens"] = int(max_tokens)

    # 4. temperature
    temperature = kwargs.get("temperature")
    if temperature is not None:
        call_kwargs["temperature"] = float(temperature)

    # 5. structured outputs (output_config)
    output_config = kwargs.get("output_config")
    if isinstance(output_config, dict):
        fmt = output_config.get("format")
        if isinstance(fmt, dict) and fmt.get("type") == "json_schema" and "schema" in fmt:
            call_kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": fmt["schema"],
                    "strict": False,
                },
            }

    return call_kwargs


def _openai_response_to_ai_response(resp: Any) -> _AIResponse:
    content = ""
    stop_reason = "end_turn"
    if getattr(resp, "choices", None):
        choice = resp.choices[0]
        content = getattr(choice.message, "content", "") or ""
        finish = getattr(choice, "finish_reason", None)
        if finish == "stop":
            stop_reason = "end_turn"
        elif finish == "length":
            stop_reason = "max_tokens"
        elif finish:
            stop_reason = finish

    usage = getattr(resp, "usage", None)
    input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

    return _AIResponse(
        text=content,
        stop_reason=stop_reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        raw=resp,
    )


def _normalize_timeout(timeout: Any) -> float | httpx.Timeout | None:
    if timeout is None:
        return None
    if isinstance(timeout, (int, float)):
        return float(timeout)
    if isinstance(timeout, Timeout):
        read_timeout = getattr(timeout, "read", 300.0) or 300.0
        connect_timeout = getattr(timeout, "connect", 30.0) or 30.0
        return httpx.Timeout(read_timeout, connect=connect_timeout)
    if isinstance(timeout, httpx.Timeout):
        return timeout
    return 300.0


class _OpenAIMessagesSync:
    def __init__(self, client: OpenAI) -> None:
        self._client = client

    def create(self, **kwargs: Any) -> _AIResponse:
        call_kwargs = _prepare_openai_call_kwargs(kwargs)
        try:
            resp = self._client.chat.completions.create(**call_kwargs)
        except Exception as exc:
            raise _translate_openai_error(exc) from exc

        return _openai_response_to_ai_response(resp)


class _OpenAIMessagesAsync:
    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def create(self, **kwargs: Any) -> _AIResponse:
        call_kwargs = _prepare_openai_call_kwargs(kwargs)
        try:
            resp = await self._client.chat.completions.create(**call_kwargs)
        except Exception as exc:
            raise _translate_openai_error(exc) from exc

        return _openai_response_to_ai_response(resp)


class OpenAISyncAdapter:
    """Sync adapter mimicking Anthropic client interface for OpenAI."""

    def __init__(
        self,
        api_key: str,
        timeout: Any = None,
        max_retries: int | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if timeout is not None:
            kwargs["timeout"] = _normalize_timeout(timeout)
        if max_retries is not None:
            kwargs["max_retries"] = max_retries
        self._client = OpenAI(**kwargs)
        self.messages = _OpenAIMessagesSync(self._client)


class OpenAIAsyncAdapter:
    """Async adapter mimicking AsyncAnthropic client interface for OpenAI."""

    def __init__(
        self,
        api_key: str,
        timeout: Any = None,
        max_retries: int | None = None,
    ) -> None:
        kwargs: dict[str, Any] = {"api_key": api_key}
        if timeout is not None:
            kwargs["timeout"] = _normalize_timeout(timeout)
        if max_retries is not None:
            kwargs["max_retries"] = max_retries
        self._client = AsyncOpenAI(**kwargs)
        self.messages = _OpenAIMessagesAsync(self._client)


def create_sync_client() -> Any:
    """Create sync client for active provider (OpenAI first, fallback to Anthropic)."""
    provider = get_ai_provider()
    api_key = get_ai_api_key()
    if provider == "openai":
        return OpenAISyncAdapter(api_key=api_key)
    return Anthropic(api_key=api_key)


def create_async_client(timeout: Any = None, max_retries: int | None = None) -> Any:
    """Create async client for active provider (OpenAI first, fallback to Anthropic)."""
    provider = get_ai_provider()
    api_key = get_ai_api_key()
    if provider == "openai":
        return OpenAIAsyncAdapter(api_key=api_key, timeout=timeout, max_retries=max_retries)
    kwargs: dict[str, Any] = {"api_key": api_key}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if max_retries is not None:
        kwargs["max_retries"] = max_retries
    return AsyncAnthropic(**kwargs)


def long_request_timeout() -> Timeout:
    """SDK timeout."""
    return Timeout(300.0, connect=30.0)


def extract_response_text(response: Any) -> str:
    """Return concatenated text blocks; skip thinking/tool blocks."""
    parts: list[str] = []
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
    return "".join(parts)
