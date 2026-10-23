from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.task import TaskStatus, SubtaskStatus


class SubtaskBase(BaseModel):
    order_index: int = Field(..., ge=0, description="Execution order")
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(...)
    assigned_agent: str = Field(..., pattern="^(researcher|coder)$")


class SubtaskCreate(SubtaskBase):
    pass


class SubtaskResponse(SubtaskBase):
    id: str
    task_id: str
    status: SubtaskStatus
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    goal: str = Field(..., min_length=3, description="Goal prompt provided by user")


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    current_step: Optional[int] = None
    rework_count: Optional[int] = None
    token_usage: Optional[int] = None
    estimated_cost_usd: Optional[float] = None


class TaskResponse(TaskBase):
    id: str
    status: TaskStatus
    current_step: int
    rework_count: int
    token_usage: int
    estimated_cost_usd: float
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    subtasks: List[SubtaskResponse] = []

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    total: int
    tasks: List[TaskResponse]


class ExecutionEventResponse(BaseModel):
    id: str
    task_id: str
    step_index: int
    event_type: str
    agent_name: Optional[str] = None
    message: str
    details: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskTracesResponse(BaseModel):
    task_id: str
    total_events: int
    events: List[ExecutionEventResponse]

