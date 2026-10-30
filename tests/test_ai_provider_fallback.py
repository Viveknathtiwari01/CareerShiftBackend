"""Tests for AI provider selection, OpenAI adapter, and fallback behavior."""

from unittest.mock import AsyncMock, MagicMock
import pytest
import httpx
import openai
from anthropic import AuthenticationError, APIStatusError, APITimeoutError, APIConnectionError

from app.core import anthropic_client as ai_mod
from app.core.anthropic_client import (
    MessagesResponse,
    _map_openai_error,
    _prepare_openai_chat_params,
    extract_response_text,
    get_active_api_key,
    get_active_model,
    get_active_provider,
    get_anthropic_model,
    get_anthropic_temperature,
    model_supports_sampling_params,
)


def test_provider_selection_anthropic_priority(monkeypatch):
    monkeypatch.setattr(ai_mod.settings, "ANTHROPIC_API_KEY", "sk-ant-key-123")
    monkeypatch.setattr(ai_mod.settings, "OPENAI_API_KEY", "sk-proj-key-456")
    monkeypatch.setattr(ai_mod.settings, "ANTHROPIC_MODEL", "claude-sonnet-5")
    monkeypatch.setattr(ai_mod.settings, "OPENAI_MODEL", "gpt-4o-mini")

    assert get_active_provider() == "anthropic"
    assert get_active_api_key() == "sk-ant-key-123"
    assert get_active_model() == "claude-sonnet-5"
    assert get_anthropic_model() == "claude-sonnet-5"


def test_provider_selection_openai_fallback_when_anthropic_empty(monkeypatch):
    monkeypatch.setattr(ai_mod.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(ai_mod.settings, "OPENAI_API_KEY", "sk-proj-key-456")
    monkeypatch.setattr(ai_mod.settings, "ANTHROPIC_MODEL", "claude-sonnet-5")
    monkeypatch.setattr(ai_mod.settings, "OPENAI_MODEL", "gpt-4o-mini")

    assert get_active_provider() == "openai"
    assert get_active_api_key() == "sk-proj-key-456"
    assert get_active_model() == "gpt-4o-mini"
    assert get_anthropic_model() == "gpt-4o-mini"


def test_provider_selection_openai_fallback_when_anthropic_none(monkeypatch):
    monkeypatch.setattr(ai_mod.settings, "ANTHROPIC_API_KEY", None)
    monkeypatch.setattr(ai_mod.settings, "OPENAI_API_KEY", "sk-proj-key-456")

    assert get_active_provider() == "openai"
    assert get_active_api_key() == "sk-proj-key-456"


def test_provider_selection_none_configured_raises(monkeypatch):
    monkeypatch.setattr(ai_mod.settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(ai_mod.settings, "OPENAI_API_KEY", "")

    assert get_active_provider() == "none"
    with pytest.raises(ValueError, match="Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY"):
        get_active_api_key()

    with pytest.raises(ValueError, match="Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY"):
        ai_mod.create_sync_client()

    with pytest.raises(ValueError, match="Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY"):
        ai_mod.create_async_client()


def test_sampling_params_support():
    assert model_supports_sampling_params("claude-sonnet-5") is False
    assert model_supports_sampling_params("claude-3-5-sonnet-latest") is True
    assert model_supports_sampling_params("gpt-4o-mini") is True
    assert model_supports_sampling_params("gpt-4o") is True


def test_prepare_openai_chat_params():
    kwargs = {
        "model": "claude-sonnet-5",  # Should map to OpenAI model
        "system": "You are an assistant.",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 2048,
        "temperature": 0.2,
        "output_config": {"format": {"type": "json_schema"}},
    }
    openai_params = _prepare_openai_chat_params(kwargs)

    assert openai_params["model"] == "gpt-4o-mini"
    assert len(openai_params["messages"]) == 2
    assert openai_params["messages"][0] == {"role": "system", "content": "You are an assistant."}
    assert openai_params["messages"][1] == {"role": "user", "content": "Hello"}
    assert openai_params["max_tokens"] == 2048
    assert openai_params["temperature"] == 0.2
    assert openai_params["response_format"] == {"type": "json_object"}


def test_extract_response_text():
    # 1. Block structure
    block_resp = type("AnthropicResp", (), {
        "content": [
            type("Block", (), {"type": "text", "text": "Part 1 "})(),
            type("Block", (), {"type": "thinking", "text": "hidden"})(),
            type("Block", (), {"type": "text", "text": "Part 2"})(),
        ]
    })()
    assert extract_response_text(block_resp) == "Part 1 Part 2"

    # 2. OpenAI structure
    choice = type("Choice", (), {"message": type("Msg", (), {"content": "OpenAI answer"})()})()
    openai_resp = type("OpenAIResp", (), {"choices": [choice], "content": None})()
    assert extract_response_text(openai_resp) == "OpenAI answer"


def test_map_openai_errors():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp_401 = httpx.Response(status_code=401, request=req)
    resp_500 = httpx.Response(status_code=500, request=req)

    # Auth error
    err_auth = openai.AuthenticationError("Invalid API key", response=resp_401, body=None)
    mapped_auth = _map_openai_error(err_auth)
    assert isinstance(mapped_auth, AuthenticationError)
    assert mapped_auth.status_code == 401

    # Status error
    err_status = openai.APIStatusError("Server error", response=resp_500, body=None)
    mapped_status = _map_openai_error(err_status)
    assert isinstance(mapped_status, APIStatusError)
    assert mapped_status.status_code == 500

    # Timeout error
    err_timeout = openai.APITimeoutError(request=req)
    mapped_timeout = _map_openai_error(err_timeout)
    assert isinstance(mapped_timeout, APITimeoutError)

    # Connection error
    err_conn = openai.APIConnectionError(request=req)
    mapped_conn = _map_openai_error(err_conn)
    assert isinstance(mapped_conn, APIConnectionError)


@pytest.mark.asyncio
async def test_openai_async_adapter_client():
    mock_choice = MagicMock()
    mock_choice.message.content = '{"status": "success"}'
    mock_choice.finish_reason = "stop"

    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 42
    mock_usage.completion_tokens = 15

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage
    mock_completion.model = "gpt-4o-mini"

    mock_openai = MagicMock()
    mock_openai.chat.completions.create = AsyncMock(return_value=mock_completion)

    adapter_client = ai_mod.OpenAIAsyncAdapterClient(mock_openai)
    response = await adapter_client.messages.create(
        model="gpt-4o-mini",
        system="System prompt",
        messages=[{"role": "user", "content": "User prompt"}],
        max_tokens=100,
        temperature=0.0,
    )

    assert isinstance(response, MessagesResponse)
    assert response.content[0].text == '{"status": "success"}'
    assert response.stop_reason == "end_turn"
    assert response.usage.input_tokens == 42
    assert response.usage.output_tokens == 15
    assert extract_response_text(response) == '{"status": "success"}'
