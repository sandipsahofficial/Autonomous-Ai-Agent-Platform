from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    Central state dictionary maintained across all LangGraph nodes.
    Includes budget safety bounds and execution tracking.
    """
    # Core Task Metadata
    task_id: str
    goal: str

    # Bounds & Safety Limits
    current_step: int
    max_steps: int
    rework_count: int
    max_rework_attempts: int

    # Financial & Resource Accounting
    token_usage: int
    estimated_cost_usd: float
    token_budget: int
    cost_budget_usd: float

    # Workflow Artifacts & Progress
    messages: List[Dict[str, Any]]
    subtasks: List[Dict[str, Any]]
    current_subtask_index: int
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
