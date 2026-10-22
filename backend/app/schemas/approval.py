from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    """
    Details of a high-risk tool action awaiting human decision.
    """
    task_id: str
    tool_name: str
    arguments: Dict[str, Any]
    risk_level: str = "HIGH"
    reason: str


class ApprovalDecision(BaseModel):
    """
    Human operator decision to approve or reject a paused action.
    """
    approved: bool = Field(..., description="True to allow execution, False to abort")
    feedback: Optional[str] = Field(None, description="Optional explanation or correction notes")


class ApprovalResponse(BaseModel):
    """
    Result returned after processing human decision and resuming graph.
    """
    task_id: str
    decision: str
    task_status: str
    message: str
