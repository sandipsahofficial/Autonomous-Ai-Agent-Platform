from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    """
    Standard token usage and cost accounting for an LLM invocation.
    """
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0.0)


class LLMResponse(BaseModel):
    """
    Standardized response returned by any LLM provider.
    """
    content: str
    structured: Optional[Dict[str, Any]] = None
    usage: LLMUsage


# Standard token pricing table per million tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {
        "prompt": 2.50 / 1_000_000,
        "completion": 10.00 / 1_000_000,
    },
    "claude-3-5-sonnet": {
        "prompt": 3.00 / 1_000_000,
        "completion": 15.00 / 1_000_000,
    },
    "mock": {
        "prompt": 0.00,
        "completion": 0.00,
    },
}


def calculate_cost_usd(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Compute USD cost based on token counts and model pricing tier.
    """
    normalized_name = model_name.lower()
    rates = MODEL_PRICING.get(normalized_name, MODEL_PRICING["gpt-4o"])
    cost = (prompt_tokens * rates["prompt"]) + (completion_tokens * rates["completion"])
    return round(cost, 6)


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM providers.
    Guarantees token/cost tracking and structured schema validation.
    """
    model_name: str

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> LLMResponse:
        """
        Generate text or structured output from the LLM.
        """
        pass
