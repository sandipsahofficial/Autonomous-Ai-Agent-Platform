from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Central state dictionary maintained across all LangGraph nodes.
    Tracks tenant identity, stage transitions, dependencies, memory context,
    tool gates, human approvals, and budget safety bounds.
    """
    # Core Task & Tenant Metadata
    task_id: str
    user_id: str
    workspace_id: str
    goal: str
    current_stage: str  # "planner" | "researcher" | "executor" | "reviewer" | "finalizer" | "completed"

    # Bounds & Safety Limits
    current_step: int
    max_steps: int
    rework_count: int
    max_rework_attempts: int
    retry_count: int

    # Financial & Resource Accounting
    token_usage: int
    estimated_cost_usd: float
    token_budget: int
    cost_budget_usd: float

    # Persistent Memory Context
    retrieved_memories: List[Dict[str, Any]]

    # Workflow Artifacts & Progress
    messages: List[Dict[str, Any]]
    subtasks: List[Dict[str, Any]]
    current_subtask_index: int
    completed_subtask_indices: List[int]
    last_agent: Optional[str]
    current_result: Optional[str]
    review_feedback: Optional[str]
    is_approved: bool

    # Completion & Error State
    final_output: Optional[str]
    error_message: Optional[str]
    is_completed: bool

    # Tool Execution Gate
    pending_tool_call: Optional[Dict[str, Any]]

    # Human-in-the-Loop Gateway
    pending_approval: Optional[Dict[str, Any]]
