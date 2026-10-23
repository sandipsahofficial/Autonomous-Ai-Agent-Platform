from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from app.safety.policy import RiskLevel


class ToolSchemaResponse(BaseModel):
    name: str
    description: str
    version: Optional[str] = "1.0.0"
    parameters: Dict[str, Any]
    required_permissions: Optional[List[str]] = Field(default_factory=list)
    timeout_seconds: Optional[int] = 10
    is_enabled: Optional[bool] = True
    requires_approval: Optional[bool] = False
    idempotent: Optional[bool] = True


class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the registered tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Typed arguments for the tool")
    human_approved: bool = Field(default=False, description="Whether human approval has been granted")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key to prevent duplicate execution")


class ToolExecutionResponse(BaseModel):
    tool_name: str
    success: bool
    risk_level: RiskLevel
    requires_human_approval: bool
    risk_reason: str
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None
