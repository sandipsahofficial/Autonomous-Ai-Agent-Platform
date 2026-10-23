from typing import List, Optional
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
