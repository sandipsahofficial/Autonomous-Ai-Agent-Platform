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


class ClaudeLLMProvider(BaseLLMProvider):
    """
    Anthropic Claude API Provider (Claude 3.5 Sonnet).
    Tracks prompt and completion tokens and evaluates cost.
    """
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022", timeout: float = 30.0):
        if not api_key or not api_key.strip():
            raise LLMAuthenticationError("Anthropic Claude API key cannot be empty.")
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> LLMResponse:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        user_content = prompt
        if response_schema:
            user_content += (
                f"\n\nIMPORTANT: Return valid JSON matching this schema:\n"
                f"{json.dumps(response_schema.model_json_schema())}"
            )

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": user_content}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.api_url, headers=headers, json=payload)
                if resp.status_code in (401, 403):
                    raise LLMAuthenticationError(f"Claude authentication failed: {resp.status_code} - {resp.text}")
                elif resp.status_code == 429:
                    raise LLMRateLimitError(f"Claude rate limit or quota exceeded: {resp.text}")
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Claude request timed out after {self.timeout}s: {str(exc)}") from exc
        except (LLMAuthenticationError, LLMRateLimitError, LLMTimeoutError):
            raise
        except Exception as exc:
            raise LLMProviderError(f"Claude provider communication failure: {str(exc)}") from exc

        content = data["content"][0]["text"]
        usage_raw = data.get("usage", {})
        prompt_tokens = usage_raw.get("input_tokens", 0)
        completion_tokens = usage_raw.get("output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_cost_usd("claude-3-5-sonnet", prompt_tokens, completion_tokens)

        structured_data = None
        if response_schema:
            try:
                cleaned = content.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                parsed_json = json.loads(cleaned.strip())
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
            provider="claude",
            is_mock=False,
            metadata={"model": self.model_name},
        )
