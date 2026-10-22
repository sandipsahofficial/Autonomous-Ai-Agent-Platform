from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from app.safety.policy import RiskLevel


class ToolSchemaResponse(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the registered tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Typed arguments for the tool")
    human_approved: bool = Field(default=False, description="Whether human approval has been granted")


class ToolExecutionResponse(BaseModel):
    tool_name: str
    success: bool
    risk_level: RiskLevel
    requires_human_approval: bool
    risk_reason: str
    output: Optional[Any] = None
    error: Optional[str] = None
