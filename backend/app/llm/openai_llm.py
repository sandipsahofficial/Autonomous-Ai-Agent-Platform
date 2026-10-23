import json
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMUsage,
    calculate_cost_usd,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMProviderError,
)


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI API Provider (GPT-4o, GPT-4o-mini).
    Uses direct HTTP calls via httpx with token and cost tracking.
    """
    def __init__(self, api_key: str, model_name: str = "gpt-4o", timeout: float = 30.0):
        if not api_key or not api_key.strip():
            raise LLMAuthenticationError("OpenAI API key cannot be empty.")
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
        }

        # If a structured schema is requested, enforce JSON mode
        if response_schema:
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.api_url, headers=headers, json=payload)
                if resp.status_code in (401, 403):
                    raise LLMAuthenticationError(f"OpenAI authentication failed: {resp.status_code} - {resp.text}")
                elif resp.status_code == 429:
                    raise LLMRateLimitError(f"OpenAI rate limit or quota exceeded: {resp.text}")
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"OpenAI request timed out after {self.timeout}s: {str(exc)}") from exc
        except (LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"OpenAI provider communication failure: {str(exc)}") from exc

        choice = data["choices"][0]
        content = choice["message"]["content"]

        usage_raw = data.get("usage", {})
        prompt_tokens = usage_raw.get("prompt_tokens", 0)
        completion_tokens = usage_raw.get("completion_tokens", 0)
        total_tokens = usage_raw.get("total_tokens", prompt_tokens + completion_tokens)
        cost_usd = calculate_cost_usd(self.model_name, prompt_tokens, completion_tokens)

        structured_data = None
        if response_schema:
            try:
                parsed_json = json.loads(content)
                validated = response_schema(**parsed_json)
                structured_data = validated.model_dump()
            except Exception:
                pass

        return LLMResponse(
            content=content,
            structured=structured_data,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
            ),
            provider="openai",
            is_mock=False,
            metadata={"model": self.model_name},
        )
