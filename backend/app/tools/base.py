from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Standardized typed result returned by every tool.
    """
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for all agent tools.
    Enforces typed input arguments via Pydantic schema and standardized outputs.
    """
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        """
        Execute the tool logic with validated arguments.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Export tool definition in OpenAPI / OpenAI function calling format.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.args_schema.model_json_schema(),
        }
