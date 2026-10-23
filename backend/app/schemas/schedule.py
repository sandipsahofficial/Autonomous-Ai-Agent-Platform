from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class ScheduleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Schedule name")
    goal: str = Field(..., min_length=3, description="Mission goal or objective")
    workflow_id: Optional[str] = Field(None, description="Optional visual workflow ID to dispatch")
    schedule_type: Literal["one_time", "recurring"] = Field(
        default="recurring", description="One-time or recurring schedule"
    )
    cron_expression: Optional[str] = Field(
        None, description="Cron format: 'min hour day month day-of-week' (e.g. '0 9 * * 1-5' for weekdays at 9am)"
    )
    timezone_str: str = Field(default="UTC", description="Target timezone name (e.g. 'UTC', 'America/New_York')")
    run_at: Optional[datetime] = Field(None, description="Target datetime for one-time run (UTC)")
    is_enabled: bool = Field(default=True, description="Whether schedule is active")
    allow_overlap: bool = Field(default=False, description="Disallow overlapping execution of previous run is active")
    max_retries: int = Field(default=2, ge=0, le=5, description="Retry attempts on scheduled failure")


class ScheduleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    goal: Optional[str] = Field(None, min_length=3)
    workflow_id: Optional[str] = None
    schedule_type: Optional[Literal["one_time", "recurring"]] = None
    cron_expression: Optional[str] = None
    timezone_str: Optional[str] = None
    run_at: Optional[datetime] = None
    is_enabled: Optional[bool] = None
    allow_overlap: Optional[bool] = None


class ScheduleExecutionResponse(BaseModel):
    id: str
    schedule_id: str
    task_id: Optional[str] = None
    idempotency_key: str
    status: str
    scheduled_time: datetime
    executed_time: datetime
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScheduleResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    workflow_id: Optional[str] = None
    name: str
    goal: str
    schedule_type: str
    cron_expression: Optional[str] = None
    timezone_str: str
    run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    is_enabled: bool
    allow_overlap: bool
    failure_count: int
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    executions: List[ScheduleExecutionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ScheduleListResponse(BaseModel):
    total: int
    schedules: List[ScheduleResponse]
