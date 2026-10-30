"""Shared AI client configuration (Anthropic with OpenAI fallback) for app and services/."""

import logging
import re
from pathlib import Path
from typing import Any

from anthropic import (
    Anthropic,
    AsyncAnthropic,
    Timeout,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
)
import httpx
import openai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Ensure Backend/.env is loaded before reading settings (services/client.py lives outside app/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=False)

from app.core.config import settings  # noqa: E402


def get_active_provider() -> str:
    """
    Determine active AI provider.
    Priority: If ANTHROPIC_API_KEY is set and non-empty, use Anthropic.
    Otherwise, if OPENAI_API_KEY is set and non-empty, use OpenAI.
    Otherwise, return 'none'.
    """
    anthropic_key = (settings.ANTHROPIC_API_KEY or "").strip()
    if anthropic_key:
        return "anthropic"
    openai_key = (settings.OPENAI_API_KEY or "").strip()
    if openai_key:
        return "openai"
    return "none"


def get_active_api_key() -> str:
    provider = get_active_provider()
    if provider == "anthropic":
        return settings.ANTHROPIC_API_KEY.strip()
    if provider == "openai":
        return settings.OPENAI_API_KEY.strip()
    raise ValueError(
        "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is configured in Backend/.env"
    )


def get_anthropic_api_key() -> str:
    """Return active provider API key (backwards compatible alias)."""
    return get_active_api_key()


def get_active_model() -> str:
    provider = get_active_provider()
    if provider == "anthropic":
        return settings.ANTHROPIC_MODEL or "claude-sonnet-5"
    if provider == "openai":
        return settings.OPENAI_MODEL or "gpt-4o-mini"
    return settings.OPENAI_MODEL or "gpt-4o-mini"


def get_anthropic_model() -> str:
    """Return active model name (backwards compatible alias)."""
    return get_active_model()


def get_anthropic_temperature() -> float:
    if get_active_provider() == "openai":
        return getattr(settings, "OPENAI_TEMPERATURE", 0.0)
    return settings.ANTHROPIC_TEMPERATURE


def get_anthropic_effort() -> str:
    return settings.ANTHROPIC_EFFORT


# Models that reject temperature/top_p/top_k (Claude 5 and Opus 4.7+).
_SAMPLING_PARAM_UNSUPPORTED = re.compile(
    r"^claude-(?:sonnet-5|opus-5|fable-5|opus-4-[78](?:-\d{8})?)$"
)


def model_supports_sampling_params(model: str) -> bool:
    """Return False when the API rejects temperature/top_p/top_k for this model."""
    if model.startswith("claude-"):
        return _SAMPLING_PARAM_UNSUPPORTED.match(model) is None
    # OpenAI models (e.g. gpt-4o-mini) support temperature
    return True


def build_messages_create_kwargs(model: str, **kwargs: Any) -> dict[str, Any]:
    """
    Build kwargs for messages.create(), omitting deprecated params per model.

    Claude Sonnet/Opus/Fable 5 and Opus 4.7+ reject temperature; use effort instead.
    For OpenAI models, retain temperature and strip Anthropic-specific effort.
    """
    if model.startswith("claude-"):
        if model_supports_sampling_params(model):
            return {"model": model, **kwargs}

        kwargs.pop("temperature", None)
        kwargs.pop("top_p", None)
        kwargs.pop("top_k", None)

        effort = get_anthropic_effort()
        if effort:
            kwargs.setdefault("output_config", {"effort": effort})

        return {"model": model, **kwargs}

    # OpenAI or generic model
    if "output_config" in kwargs and isinstance(kwargs["output_config"], dict):
        out_cfg = dict(kwargs["output_config"])
        out_cfg.pop("effort", None)
        if out_cfg:
            kwargs["output_config"] = out_cfg
        else:
            kwargs.pop("output_config", None)

    return {"model": model, **kwargs}


def long_request_timeout() -> Timeout:
    """SDK timeout for long LLM requests."""
    return Timeout(300.0, connect=30.0)


class TextBlock:
    """Anthropic-compatible text block representation."""

    def __init__(self, text: str, type: str = "text"):
        self.text = text
        self.type = type

    def __repr__(self) -> str:
        return f"TextBlock(type='{self.type}', text={self.text[:50]!r}...)"


class UsageInfo:
    """Anthropic-compatible usage statistics."""

    def __init__(self, input_tokens: int = 0, output_tokens: int = 0):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def __repr__(self) -> str:
        return f"Usage(input_tokens={self.input_tokens}, output_tokens={self.output_tokens})"


class MessagesResponse:
    """Anthropic-compatible response wrapper around OpenAI chat completions."""

    def __init__(self, completion: Any):
        choice = completion.choices[0] if getattr(completion, "choices", None) else None
        content_text = choice.message.content if choice and choice.message else ""
        self.content = [TextBlock(text=content_text or "", type="text")]
        finish_reason = getattr(choice, "finish_reason", "stop") if choice else "stop"
        self.stop_reason = "max_tokens" if finish_reason == "length" else "end_turn"
        usage = getattr(completion, "usage", None)
        p_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        c_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        self.usage = UsageInfo(input_tokens=p_tokens, output_tokens=c_tokens)
        self.model = getattr(completion, "model", "")
        self.choices = getattr(completion, "choices", [])
        self.raw = completion


def _map_openai_error(exc: Exception) -> Exception:
    """Translate OpenAI API exceptions to Anthropic equivalents so all callers handle them cleanly."""
    if isinstance(exc, (AuthenticationError, APIStatusError, APITimeoutError, APIConnectionError)):
        return exc

    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    if isinstance(exc, openai.AuthenticationError):
        resp = getattr(exc, "response", None) or httpx.Response(status_code=401, request=req)
        return AuthenticationError(str(exc), response=resp, body=getattr(exc, "body", None))
    if isinstance(exc, openai.APIStatusError):
        code = getattr(exc, "status_code", 500)
        resp = getattr(exc, "response", None) or httpx.Response(status_code=code, request=req)
        return APIStatusError(str(exc), response=resp, body=getattr(exc, "body", None))
    if isinstance(exc, openai.APITimeoutError):
        return APITimeoutError(request=req)
    if isinstance(exc, openai.APIConnectionError):
        return APIConnectionError(request=req)
    return exc


def _prepare_openai_chat_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Convert Anthropic messages.create parameters into OpenAI chat completions parameters."""
    params = dict(kwargs)
    model = params.pop("model", None)
    if not model or model.startswith("claude-"):
        model = settings.OPENAI_MODEL or "gpt-4o-mini"
    openai_params: dict[str, Any] = {"model": model}

    system_prompt = params.pop("system", None)
    raw_messages = params.pop("messages", []) or []
    openai_messages: list[dict[str, Any]] = []

    if system_prompt:
        openai_messages.append({"role": "system", "content": system_prompt})

    for msg in raw_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            content = "".join(text_parts)
        openai_messages.append({"role": role, "content": content})

    openai_params["messages"] = openai_messages

    max_tokens = params.pop("max_tokens", None)
    if max_tokens is not None:
        openai_params["max_tokens"] = max_tokens

    temperature = params.pop("temperature", None)
    if temperature is not None:
        openai_params["temperature"] = temperature

    # Structured output or json format
    output_config = params.pop("output_config", None)
    if output_config and isinstance(output_config, dict):
        fmt = output_config.get("format")
        if isinstance(fmt, dict):
            fmt_type = fmt.get("type")
            if fmt_type in ("json_schema", "json_object"):
                openai_params["response_format"] = {"type": "json_object"}

    # Forward any remaining valid parameters
    for k, v in params.items():
        if k not in openai_params and k not in ("top_k", "top_p", "stream"):
            openai_params[k] = v

    return openai_params


class OpenAIMessagesSyncAdapter:
    """Synchronous adapter matching client.messages.create() API."""

    def __init__(self, raw_client: openai.OpenAI):
        self._raw_client = raw_client

    def create(self, **kwargs: Any) -> MessagesResponse:
        openai_params = _prepare_openai_chat_params(kwargs)
        try:
            completion = self._raw_client.chat.completions.create(**openai_params)
            return MessagesResponse(completion)
        except Exception as exc:
            mapped = _map_openai_error(exc)
            raise mapped from exc


class OpenAIMessagesAsyncAdapter:
    """Asynchronous adapter matching await client.messages.create() API."""

    def __init__(self, raw_client: openai.AsyncOpenAI):
        self._raw_client = raw_client

    async def create(self, **kwargs: Any) -> MessagesResponse:
        openai_params = _prepare_openai_chat_params(kwargs)
        try:
            completion = await self._raw_client.chat.completions.create(**openai_params)
            return MessagesResponse(completion)
        except Exception as exc:
            mapped = _map_openai_error(exc)
            raise mapped from exc


class OpenAISyncAdapterClient:
    """OpenAI client exposing the Anthropic client interface (client.messages.create)."""

    def __init__(self, raw_client: openai.OpenAI):
        self._raw_client = raw_client
        self.messages = OpenAIMessagesSyncAdapter(raw_client)


class OpenAIAsyncAdapterClient:
    """OpenAI async client exposing the AsyncAnthropic client interface (client.messages.create)."""

    def __init__(self, raw_client: openai.AsyncOpenAI):
        self._raw_client = raw_client
        self.messages = OpenAIMessagesAsyncAdapter(raw_client)


def create_sync_client() -> Any:
    """Create a synchronous client for the active AI provider (Anthropic or OpenAI)."""
    provider = get_active_provider()
    if provider == "anthropic":
        return Anthropic(api_key=settings.ANTHROPIC_API_KEY.strip())
    if provider == "openai":
        raw_client = openai.OpenAI(
            api_key=settings.OPENAI_API_KEY.strip(),
            timeout=300.0,
            max_retries=2,
        )
        return OpenAISyncAdapterClient(raw_client)
    raise ValueError(
        "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is configured in Backend/.env"
    )


def create_async_client() -> Any:
    """Create an asynchronous client for the active AI provider (Anthropic or OpenAI)."""
    provider = get_active_provider()
    if provider == "anthropic":
        return AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY.strip(),
            timeout=long_request_timeout(),
            max_retries=2,
        )
    if provider == "openai":
        raw_client = openai.AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY.strip(),
            timeout=300.0,
            max_retries=2,
        )
        return OpenAIAsyncAdapterClient(raw_client)
    raise ValueError(
        "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is configured in Backend/.env"
    )


def extract_response_text(response: Any) -> str:
    """Return concatenated text blocks; works for Anthropic, OpenAI adapter, or raw OpenAI response."""
    # 1. Anthropic & MessagesResponse content blocks
    parts: list[str] = []
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text":
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
    if parts:
        return "".join(parts)

    # 2. Raw OpenAI ChatCompletion response fallback
    choices = getattr(response, "choices", None)
    if choices and len(choices) > 0:
        msg = getattr(choices[0], "message", None)
        if msg and getattr(msg, "content", None):
            return msg.content

    return ""
