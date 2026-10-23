from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FleetMetricsResponse(BaseModel):
    total_tasks: int = Field(..., description="Total tasks ever registered")
    active_tasks: int = Field(..., description="Tasks currently pending, planning, running, or waiting approval")
    completed_tasks: int = Field(..., description="Successfully completed tasks")
    failed_tasks: int = Field(..., description="Tasks with status FAILED")
    pending_approvals: int = Field(..., description="Tasks waiting for human approval")
    completion_rate: float = Field(..., description="Percentage of finalized tasks that completed successfully (0.0 to 100.0)")
    average_cost_usd: float = Field(..., description="Average cost in USD across tasks with recorded non-zero cost")
    total_cost_usd: float = Field(..., description="Total accumulated USD cost across all tasks")
    total_tokens: int = Field(..., description="Total tokens consumed across all tasks")


class AgentMetricItem(BaseModel):
    id: str
    name: str
    role: str
    assigned_agent: str
    status: str
    status_type: str
    runs: int
    success_rate: float
    usage_percent: int
    cost_usd: float
    last_active: Optional[str] = None


class AgentMetricsListResponse(BaseModel):
    total_agents: int
    agents: List[AgentMetricItem]


class FailureReasonItem(BaseModel):
    reason: str
    count: int


class EvaluationQualityMetrics(BaseModel):
    task_completion_rate: float = Field(..., description="Task success completion percentage (0.0-100.0)")
    reviewer_acceptance_rate: float = Field(..., description="Reviewer acceptance rate across subtasks (0.0-100.0)")
    tool_success_rate: float = Field(..., description="Tool invocation success percentage (0.0-100.0)")
    retry_rate: float = Field(..., description="Proportion of missions experiencing bounded retries")
    average_duration_ms: float = Field(..., description="Average operation duration in milliseconds")
    p95_duration_ms: float = Field(..., description="95th percentile operation duration in milliseconds")
    llm_failures_count: int = Field(..., description="Count of recovered or logged LLM provider failures")
    approval_wait_time_avg_s: float = Field(..., description="Average wait time for human operator approvals in seconds")
    top_failure_reasons: List[FailureReasonItem] = Field(default_factory=list, description="Categorized failure explanations")
