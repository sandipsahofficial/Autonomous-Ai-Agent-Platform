from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EvaluationSummary(BaseModel):
    sample_size: int = Field(..., description="Total completed or evaluated task samples")
    completion_rate: float
    reviewer_acceptance_rate: float
    tool_success_rate: float
    failure_rate: float
    retry_rate: float
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    avg_provider_latency_ms: float
    total_tokens_consumed: int
    total_cost_usd: float
    cost_attribution_mode: str = "Actual database records (where valid) & zero-cost local inference"


class WorkflowPerformanceItem(BaseModel):
    workflow_id: str
    workflow_name: str
    runs_count: int
    success_rate: float
    avg_duration_ms: float


class EvaluationDashboardResponse(BaseModel):
    summary: EvaluationSummary
    workflow_breakdown: List[WorkflowPerformanceItem]
    recent_benchmark_results: List[Dict[str, Any]]
