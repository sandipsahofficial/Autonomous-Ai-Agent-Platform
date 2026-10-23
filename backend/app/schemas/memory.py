from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class MemoryCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255, description="Unique memory lookup key")
    content: str = Field(..., min_length=1, description="Textual memory payload or strategy description")
    memory_type: Literal["mission", "workspace", "task_history"] = Field(
        default="workspace", description="Memory persistence scope"
    )
    workspace_id: str = Field(default="default_workspace", description="Tenant workspace ID")
    mission_id: Optional[str] = Field(None, description="Optional parent mission task ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured tags or attributes")
    ttl_seconds: Optional[int] = Field(None, ge=1, description="Optional time-to-live in seconds")


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1, description="Updated content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata attributes")


class MemoryResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    mission_id: Optional[str] = None
    memory_type: str
    key: str
    content: str
    metadata_: Optional[Dict[str, Any]] = Field(default=None)
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MemoryListResponse(BaseModel):
    total: int
    memories: List[MemoryResponse]
