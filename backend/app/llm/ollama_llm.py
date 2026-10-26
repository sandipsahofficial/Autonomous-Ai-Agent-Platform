import json
import re
from typing import Any, Dict, Optional, Type
import httpx
from pydantic import BaseModel
from app.config import get_settings
from app.llm.base import (
    BaseLLMProvider,
    LLMResponse,
    LLMUsage,
    LLMTimeoutError,
    LLMProviderError,
)


def _generate_schema_example(schema_cls: Type[BaseModel]) -> Dict[str, Any]:
    schema = schema_cls.model_json_schema()
    defs = schema.get("$defs", {})

    def resolve_prop(prop_dict: Dict[str, Any]) -> Any:
        if "$ref" in prop_dict:
            ref_name = prop_dict["$ref"].split("/")[-1]
            ref_schema = defs.get(ref_name, {})
            return resolve_object(ref_schema)
        prop_type = prop_dict.get("type", "string")
        if "enum" in prop_dict and prop_dict["enum"]:
            return prop_dict["enum"][0]
        if prop_type == "integer":
            return 95
        if prop_type == "number":
            return 1.0
        if prop_type == "boolean":
            return True
        if prop_type == "array":
            items = prop_dict.get("items", {})
            return [resolve_prop(items)]
        if prop_type == "object":
            return resolve_object(prop_dict)
        title = prop_dict.get("title", "text").lower()
        return f"example_{title}"

    def resolve_object(obj_schema: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        props = obj_schema.get("properties", {})
        for name, p_info in props.items():
            result[name] = resolve_prop(p_info)
        return result

    return resolve_object(schema)


class OllamaLLMProvider(BaseLLMProvider):
    """
    Local Ollama API Provider (e.g. llama3, mistral, qwen2.5-coder).
    Executes on a local Ollama daemon (defaults to http://localhost:11434).
    Local inference incurs 0.00 USD direct API cost.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        resolved_base = base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")
        self.base_url = resolved_base.rstrip("/")
        self.model_name = model_name or getattr(settings, "OLLAMA_MODEL_NAME", "llama3")
        self.provider_name = "ollama"
        self.timeout = timeout if timeout is not None else float(getattr(settings, "LLM_TIMEOUT_SECONDS", 60.0))
        self.api_url = f"{self.base_url}/api/chat"

    @staticmethod
    def _parse_structured_output(content: str, response_schema: Type[BaseModel]) -> Optional[Dict[str, Any]]:
        cleaned = content.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Attempt 1: direct parse
        parsed = None
        try:
            parsed = json.loads(cleaned)
        except Exception:
            # Attempt 2: extract JSON object via regex
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except Exception:
                    pass

        if parsed is None or not isinstance(parsed, dict):
            return None

        # Attempt A: direct validation
        try:
            validated = response_schema(**parsed)
            return validated.model_dump()
        except Exception:
            pass

        # Attempt B: check if wrapped inside a nested dictionary
        for val in parsed.values():
            if isinstance(val, dict):
                try:
                    validated = response_schema(**val)
                    return validated.model_dump()
                except Exception:
                    pass

        # Attempt C: coerce string integers if model formatted e.g. "quality_score": "95"
        try:
            coerced = dict(parsed)
            schema_props = response_schema.model_json_schema().get("properties", {})
            for k, prop_info in schema_props.items():
                if k in coerced and prop_info.get("type") == "integer" and isinstance(coerced[k], str):
                    digits = "".join(ch for ch in coerced[k] if ch.isdigit())
                    if digits:
                        coerced[k] = int(digits)
            validated = response_schema(**coerced)
            return validated.model_dump()
        except Exception:
            pass

        return None

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
            try:
                example_json = json.dumps(_generate_schema_example(response_schema), indent=2)
            except Exception:
                example_json = json.dumps(response_schema.model_json_schema())

            user_content += (
                f"\n\nCRITICAL INSTRUCTION: Output strictly valid JSON matching this structure without any markdown fences, preamble, or schema metadata:\n"
                f"{example_json}\n"
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
            structured_data = self._parse_structured_output(content, response_schema)

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
