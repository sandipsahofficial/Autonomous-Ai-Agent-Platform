import json
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.llm.base import BaseLLMProvider, LLMResponse, LLMUsage, calculate_cost_usd


class ClaudeLLMProvider(BaseLLMProvider):
    """
    Anthropic Claude API Provider (Claude 3.5 Sonnet).
    Tracks prompt and completion tokens and evaluates cost.
    """
    def __init__(self, api_key: str, model_name: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = "https://api.anthropic.com/v1/messages"

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

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(self.api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        content = data["content"][0]["text"]
        usage_raw = data.get("usage", {})
        prompt_tokens = usage_raw.get("input_tokens", 0)
        completion_tokens = usage_raw.get("output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        cost_usd = calculate_cost_usd("claude-3-5-sonnet", prompt_tokens, completion_tokens)

        structured_data = None
        if response_schema:
            try:
                # Handle potential markdown code fences ```json ... ```
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
        )
