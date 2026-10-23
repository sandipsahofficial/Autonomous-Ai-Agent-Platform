import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.tools.base import BaseTool, ToolResult


class JsonValidatorInput(BaseModel):
    json_string: str = Field(..., min_length=1, max_length=50000, description="Raw JSON string to validate and inspect")
    required_keys: Optional[List[str]] = Field(default=None, description="Optional list of required top-level object keys")
    format_output: bool = Field(default=True, description="Whether to format and pretty-print validated JSON")


class JsonValidatorOutput(BaseModel):
    is_valid: bool
    data_type: str
    key_count: int
    missing_required_keys: List[str]
    formatted_json: Optional[str] = None


class JsonValidatorTool(BaseTool):
    """
    Structured JSON validator and formatter.
    Ensures input strings parse cleanly and satisfy required key constraints.
    """
    name = "json_validator"
    version = "1.0.0"
    description = "Validates structured JSON syntax, inspects data types, and checks required schema keys."
    args_schema = JsonValidatorInput
    output_schema = JsonValidatorOutput
    required_permissions = ["json:validate"]
    timeout_seconds = 2
    max_output_size_bytes = 16384
    is_enabled = True
    requires_approval = False
    idempotent = True

    def run(self, json_string: str, required_keys: Optional[List[str]] = None, format_output: bool = True) -> ToolResult:
        try:
            parsed = json.loads(json_string)
            data_type = type(parsed).__name__
            key_count = len(parsed) if isinstance(parsed, (dict, list)) else 1

            missing_keys = []
            if required_keys and isinstance(parsed, dict):
                for k in required_keys:
                    if k not in parsed:
                        missing_keys.append(k)

            formatted = None
            if format_output:
                formatted = json.dumps(parsed, indent=2)

            is_valid = len(missing_keys) == 0

            return ToolResult(
                success=is_valid,
                output={
                    "is_valid": is_valid,
                    "data_type": data_type,
                    "key_count": key_count,
                    "missing_required_keys": missing_keys,
                    "formatted_json": formatted,
                },
                error=f"Missing required keys: {missing_keys}" if missing_keys else None,
            )
        except json.JSONDecodeError as jde:
            return ToolResult(
                success=False,
                output={"is_valid": False, "data_type": "invalid", "key_count": 0, "missing_required_keys": []},
                error=f"Invalid JSON at line {jde.lineno}, col {jde.colno}: {jde.msg}",
            )
        except Exception as exc:
            return ToolResult(success=False, output=None, error=f"JSON validation error: {str(exc)}")
