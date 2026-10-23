import json
import pytest
from unittest.mock import patch, MagicMock
import httpx
from pydantic import BaseModel

from app.llm.base import (
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMProviderError,
)
from app.llm.openai_llm import OpenAILLMProvider
from app.llm.claude_llm import ClaudeLLMProvider
from app.llm.ollama_llm import OllamaLLMProvider
from app.llm.mock_llm import MockLLMProvider
from app.llm.factory import get_llm_provider


class DummySchema(BaseModel):
    summary: str


def test_openai_validation_and_success():
    with pytest.raises(LLMAuthenticationError):
        OpenAILLMProvider(api_key="")

    provider = OpenAILLMProvider(api_key="sk-test-key", model_name="gpt-4o")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps({"summary": "Task complete"})}}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = provider.generate("Test prompt", response_schema=DummySchema)
        assert res.provider == "openai"
        assert res.is_mock is False
        assert res.usage.prompt_tokens == 50
        assert res.usage.completion_tokens == 20
        assert res.structured == {"summary": "Task complete"}


def test_openai_error_handling():
    provider = OpenAILLMProvider(api_key="sk-test-key")

    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.text = "Invalid API Key"

    with patch("httpx.Client.post", return_value=mock_401):
        with pytest.raises(LLMAuthenticationError):
            provider.generate("Test")

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Rate limit exceeded"

    with patch("httpx.Client.post", return_value=mock_429):
        with pytest.raises(LLMRateLimitError):
            provider.generate("Test")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timeout")):
        with pytest.raises(LLMTimeoutError):
            provider.generate("Test")


def test_claude_validation_and_success():
    with pytest.raises(LLMAuthenticationError):
        ClaudeLLMProvider(api_key="")

    provider = ClaudeLLMProvider(api_key="sk-ant-test", model_name="claude-3-5-sonnet")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "content": [{"text": json.dumps({"summary": "Claude completed"})}],
        "usage": {"input_tokens": 40, "output_tokens": 25},
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = provider.generate("Test prompt", response_schema=DummySchema)
        assert res.provider == "claude"
        assert res.is_mock is False
        assert res.usage.prompt_tokens == 40
        assert res.usage.completion_tokens == 25
        assert res.structured == {"summary": "Claude completed"}


def test_claude_error_handling():
    provider = ClaudeLLMProvider(api_key="sk-ant-test")

    mock_401 = MagicMock()
    mock_401.status_code = 401
    mock_401.text = "Unauthorized"

    with patch("httpx.Client.post", return_value=mock_401):
        with pytest.raises(LLMAuthenticationError):
            provider.generate("Test")

    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.text = "Rate limit reached"

    with patch("httpx.Client.post", return_value=mock_429):
        with pytest.raises(LLMRateLimitError):
            provider.generate("Test")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(LLMTimeoutError):
            provider.generate("Test")


def test_ollama_provider():
    provider = OllamaLLMProvider(base_url="http://localhost:11434", model_name="llama3")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "message": {"content": json.dumps({"summary": "Ollama done"})},
        "prompt_eval_count": 30,
        "eval_count": 15,
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = provider.generate("Test prompt", response_schema=DummySchema)
        assert res.provider == "ollama"
        assert res.is_mock is False
        assert res.usage.cost_usd == 0.0
        assert res.usage.prompt_tokens == 30
        assert res.usage.completion_tokens == 15
        assert res.structured == {"summary": "Ollama done"}

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timeout")):
        with pytest.raises(LLMTimeoutError):
            provider.generate("Test")

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
        with pytest.raises(LLMProviderError):
            provider.generate("Test")


def test_factory_selection():
    mock_p = get_llm_provider("mock")
    assert isinstance(mock_p, MockLLMProvider)

    ollama_p = get_llm_provider("ollama")
    assert isinstance(ollama_p, OllamaLLMProvider)

    with patch("app.config.get_settings") as mock_settings:
        mock_settings.return_value.LLM_PROVIDER = "openai"
        mock_settings.return_value.OPENAI_API_KEY = None
        with pytest.raises(LLMAuthenticationError):
            get_llm_provider("openai")
