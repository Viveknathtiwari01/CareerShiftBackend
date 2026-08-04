"""Shared Anthropic client configuration for app and services/."""

from pathlib import Path

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


def create_sync_client() -> Anthropic:
    return Anthropic(api_key=get_anthropic_api_key())


def create_async_client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_anthropic_api_key())
