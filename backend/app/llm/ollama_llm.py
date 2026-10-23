import json
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMUsage,
    LLMTimeoutError,
    LLMProviderError,
)


class OllamaLLMProvider(BaseLLMProvider):
    """
    Local Ollama API Provider (e.g. llama3, mistral, qwen2.5-coder).
    Executes on a local Ollama daemon (defaults to http://localhost:11434).
    Local inference incurs 0.00 USD direct API cost.
    """
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.api_url = f"{self.base_url}/api/chat"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        response_schema: Optional[Type[BaseModel]] = None,
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = prompt
        if response_schema:
            user_content += (
                f"\n\nReturn strictly valid JSON matching this schema:\n"
                f"{json.dumps(response_schema.model_json_schema())}"
            )
        messages.append({"role": "user", "content": user_content})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }
        if response_schema:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(self.api_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Ollama request timed out after {self.timeout}s: {str(exc)}") from exc
        except Exception as exc:
            raise LLMProviderError(f"Ollama provider communication failure at {self.api_url}: {str(exc)}") from exc

        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        total_tokens = prompt_tokens + completion_tokens

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
                cost_usd=0.0,
            ),
            provider="ollama",
            is_mock=False,
            metadata={"model": self.model_name, "base_url": self.base_url},
        )
