"""Shared Anthropic client configuration for app and services/."""

import re
from pathlib import Path
from typing import Any

from anthropic import Anthropic, AsyncAnthropic
from dotenv import load_dotenv

# Ensure Backend/.env is loaded before reading settings (services/client.py lives outside app/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=False)

from app.core.config import settings  # noqa: E402


def get_anthropic_api_key() -> str:
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured in Backend/.env")
    return settings.ANTHROPIC_API_KEY


def get_anthropic_model() -> str:
    return settings.ANTHROPIC_MODEL


def get_anthropic_temperature() -> float:
    return settings.ANTHROPIC_TEMPERATURE


def get_anthropic_effort() -> str:
    return settings.ANTHROPIC_EFFORT


# Models that reject temperature/top_p/top_k (Claude 5 and Opus 4.7+).
_SAMPLING_PARAM_UNSUPPORTED = re.compile(
    r"^claude-(?:sonnet-5|opus-5|fable-5|opus-4-[78](?:-\d{8})?)$"
)


def model_supports_sampling_params(model: str) -> bool:
    """Return False when the API rejects temperature/top_p/top_k for this model."""
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


def create_sync_client() -> Anthropic:
    return Anthropic(api_key=get_anthropic_api_key())


def create_async_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_anthropic_api_key())
