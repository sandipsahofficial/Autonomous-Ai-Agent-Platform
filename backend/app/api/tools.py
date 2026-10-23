from typing import List
from fastapi import APIRouter, HTTPException, status
from app.tools.registry import default_tool_registry
from app.schemas.tool import ToolSchemaResponse, ToolExecutionRequest, ToolExecutionResponse

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("", response_model=List[ToolSchemaResponse])
def list_available_tools():
    """
    List all registered tools with their schemas.
    """
    return default_tool_registry.list_schemas()


@router.post("/execute", response_model=ToolExecutionResponse)
def execute_tool(payload: ToolExecutionRequest):
    """
    Execute a tool through the mandatory safety gate.
    """
    result, risk = default_tool_registry.execute_with_safety_gate(
        tool_name=payload.tool_name,
        arguments=payload.arguments,
        human_approved=payload.human_approved,
        idempotency_key=payload.idempotency_key,
    )

    return ToolExecutionResponse(
        tool_name=payload.tool_name,
        success=result.success,
        risk_level=risk.risk_level,
        requires_human_approval=risk.requires_human_approval,
        risk_reason=risk.reason,
        output=result.output,
        error=result.error,
        duration_ms=result.duration_ms,
    )
