from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Standardized typed result returned by every tool.
    """
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.
    Enforces typed input arguments, explicit versioning, permissions, timeouts, and size caps.
    """
    name: str
    description: str
    version: str = "1.0.0"
    args_schema: Type[BaseModel]
    output_schema: Optional[Type[BaseModel]] = None
    required_permissions: List[str] = []
    timeout_seconds: int = 10
    max_output_size_bytes: int = 32768  # 32 KB maximum output
    is_enabled: bool = True
    requires_approval: bool = False
    idempotent: bool = True

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        """
        Execute the tool logic with validated arguments.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Export tool definition in OpenAPI / function calling format.
        """
        schema: Dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema(),
            "required_permissions": self.required_permissions,
            "timeout_seconds": self.timeout_seconds,
            "is_enabled": self.is_enabled,
            "requires_approval": self.requires_approval,
            "idempotent": self.idempotent,
        }
        if self.output_schema:
            schema["output_schema"] = self.output_schema.model_json_schema()
        return schema
