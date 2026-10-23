from typing import Optional
from app.config import get_settings
from app.llm.base import BaseLLMProvider, LLMAuthenticationError
from app.llm.mock_llm import MockLLMProvider
from app.llm.openai_llm import OpenAILLMProvider
from app.llm.claude_llm import ClaudeLLMProvider
from app.llm.ollama_llm import OllamaLLMProvider

settings = get_settings()


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """
    Factory function to instantiate the configured LLM provider.
    Defaults to MockLLMProvider for zero-cost local development and testing.
    """
    provider = (provider_type or settings.LLM_PROVIDER).lower()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise LLMAuthenticationError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model_name=settings.LLM_MODEL_NAME,
            timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 30.0),
        )

    elif provider == "claude":
        if not settings.CLAUDE_API_KEY:
            raise LLMAuthenticationError("CLAUDE_API_KEY is required when LLM_PROVIDER=claude")
        return ClaudeLLMProvider(
            api_key=settings.CLAUDE_API_KEY,
            model_name=settings.LLM_MODEL_NAME,
            timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 30.0),
        )

    elif provider == "ollama":
        return OllamaLLMProvider(
            base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name=getattr(settings, "OLLAMA_MODEL_NAME", "llama3"),
            timeout=getattr(settings, "LLM_TIMEOUT_SECONDS", 30.0),
        )

    # Default fallback: Zero-cost Mock LLM
    return MockLLMProvider(model_name=settings.LLM_MODEL_NAME)
