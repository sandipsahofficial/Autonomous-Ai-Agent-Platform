from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class StreamEventPayload(BaseModel):
    event_id: str = Field(..., description="Unique event identifier")
    task_id: str = Field(..., description="Target mission ID")
    event_type: str = Field(..., description="Standardized event archetype")
    step_index: int = Field(default=0)
    agent_name: Optional[str] = None
    status: str = Field(default="INFO")
    duration_ms: Optional[float] = None
    message: str = Field(...)
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(...)
