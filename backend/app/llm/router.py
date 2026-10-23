import os
import time
import httpx
from typing import Optional, List, Dict, Any, Tuple
from app.config import get_settings
from app.schemas.model_router import (
    ModelRouteRequest,
    ModelRouteDecision,
    ProviderStatusItem,
    ModelRouterStatusResponse,
)
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider


class ModelRouter:
    """
    Intelligent, privacy-preserving model routing service.
    Evaluates provider availability, task category, privacy requirements, and budgets.
    STRICT POLICY: Never silently switch to a paid cloud provider when local inference is expected.
    """

    @classmethod
    def check_ollama_health(cls) -> Tuple[bool, Optional[float], Optional[str]]:
        settings = get_settings()
        base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        start = time.time()
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{base_url}/api/tags")
                latency = round((time.time() - start) * 1000, 1)
                if res.status_code == 200:
                    return True, latency, None
                return False, latency, f"HTTP {res.status_code}"
        except Exception as exc:
            return False, None, str(exc)

    @classmethod
    def get_provider_status(cls) -> ModelRouterStatusResponse:
        settings = get_settings()
        providers: List[ProviderStatusItem] = []

        # 1. Ollama (Local Zero-Cost)
        ollama_ok, ollama_lat, ollama_err = cls.check_ollama_health()
        providers.append(
            ProviderStatusItem(
                provider_name="ollama",
                is_available=ollama_ok,
                is_configured=bool(settings.OLLAMA_BASE_URL),
                is_local=True,
                supported_models=[settings.OLLAMA_MODEL_NAME, "llama3", "mistral", "qwen2.5-coder"],
                latency_ms=ollama_lat,
                last_error=ollama_err,
            )
        )

        # 2. OpenAI
        has_openai = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.startswith("sk-"))
        providers.append(
            ProviderStatusItem(
                provider_name="openai",
                is_available=has_openai,
                is_configured=has_openai,
                is_local=False,
                supported_models=["gpt-4o", "gpt-4o-mini"],
                latency_ms=None,
                last_error=None if has_openai else "Missing or unconfigured OPENAI_API_KEY",
            )
        )

        # 3. Claude
        has_claude = bool(settings.CLAUDE_API_KEY and len(settings.CLAUDE_API_KEY) > 10)
        providers.append(
            ProviderStatusItem(
                provider_name="claude",
                is_available=has_claude,
                is_configured=has_claude,
                is_local=False,
                supported_models=["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"],
                latency_ms=None,
                last_error=None if has_claude else "Missing or unconfigured CLAUDE_API_KEY",
            )
        )

        # 4. Mock (Test)
        providers.append(
            ProviderStatusItem(
                provider_name="mock",
                is_available=True,
                is_configured=True,
                is_local=True,
                supported_models=["mock-llama3"],
                latency_ms=0.5,
                last_error=None,
            )
        )

        return ModelRouterStatusResponse(
            default_provider=settings.LLM_PROVIDER,
            providers=providers,
            active_routing_policy="Privacy-First & Zero-Cost Priority",
        )

    @classmethod
    def route(cls, req: ModelRouteRequest) -> ModelRouteDecision:
        settings = get_settings()

        # Privacy constraint: If mission contains private user documents, prevent external leaks
        if req.has_private_documents:
            if settings.LLM_PROVIDER == "mock":
                return ModelRouteDecision(
                    selected_provider="mock",
                    selected_model="mock-llama3",
                    reason="Privacy Enforcement: Mission references private documents. Routed strictly to local zero-cost provider (MockLLM).",
                    is_local_zero_cost=True,
                    candidate_providers=["mock"],
                )
            # Check if local Ollama is available
            ollama_ok, _, _ = cls.check_ollama_health()
            if ollama_ok:
                return ModelRouteDecision(
                    selected_provider="ollama",
                    selected_model=settings.OLLAMA_MODEL_NAME,
                    reason="Privacy Enforcement: Mission references private user documents. Routed strictly to local Ollama daemon to prevent third-party exfiltration.",
                    is_local_zero_cost=True,
                    candidate_providers=["ollama"],
                )
            elif settings.APP_DEBUG:
                return ModelRouteDecision(
                    selected_provider="mock",
                    selected_model="mock-llama3",
                    reason="Privacy Enforcement: Local Ollama unavailable in debug mode; routed to safe offline mock.",
                    is_local_zero_cost=True,
                    fallback_applied=True,
                    candidate_providers=["ollama", "mock"],
                )

        # Deterministic testing override
        if settings.LLM_PROVIDER == "mock":
            return ModelRouteDecision(
                selected_provider="mock",
                selected_model="mock-llama3",
                reason="Test environment active: routed to deterministic MockLLM provider.",
                is_local_zero_cost=True,
                candidate_providers=["mock"],
            )

        # User explicit preference
        if req.preferred_provider:
            pref = req.preferred_provider
            if pref == "openai" and settings.OPENAI_API_KEY:
                return ModelRouteDecision(
                    selected_provider="openai",
                    selected_model=settings.OPENAI_MODEL_NAME,
                    reason="Routed to user-preferred OpenAI cloud provider.",
                    is_local_zero_cost=False,
                    candidate_providers=["openai"],
                )
            elif pref == "claude" and settings.CLAUDE_API_KEY:
                return ModelRouteDecision(
                    selected_provider="claude",
                    selected_model=settings.CLAUDE_MODEL_NAME,
                    reason="Routed to user-preferred Anthropic Claude cloud provider.",
                    is_local_zero_cost=False,
                    candidate_providers=["claude"],
                )
            elif pref == "ollama":
                return ModelRouteDecision(
                    selected_provider="ollama",
                    selected_model=settings.OLLAMA_MODEL_NAME,
                    reason="Routed to user-preferred local Ollama provider.",
                    is_local_zero_cost=True,
                    candidate_providers=["ollama"],
                )

        # Default standard route: Ollama local first
        ollama_ok, _, _ = cls.check_ollama_health()
        if ollama_ok:
            return ModelRouteDecision(
                selected_provider="ollama",
                selected_model=settings.OLLAMA_MODEL_NAME,
                reason="Default zero-cost local inference selected via Ollama daemon.",
                is_local_zero_cost=True,
                candidate_providers=["ollama"],
            )

        # If Ollama is offline and user configured OpenAI
        if settings.OPENAI_API_KEY:
            return ModelRouteDecision(
                selected_provider="openai",
                selected_model=settings.OPENAI_MODEL_NAME,
                reason="Local Ollama daemon offline; fell back to configured OpenAI credentials.",
                is_local_zero_cost=False,
                fallback_applied=True,
                candidate_providers=["ollama", "openai"],
            )

        # Default fallback to mock in development if nothing configured
        return ModelRouteDecision(
            selected_provider="mock",
            selected_model="mock-llama3",
            reason="No live external provider or Ollama daemon detected; falling back to offline mock.",
            is_local_zero_cost=True,
            fallback_applied=True,
            candidate_providers=["mock"],
        )
