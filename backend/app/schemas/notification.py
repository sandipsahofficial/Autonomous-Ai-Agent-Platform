from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class NotificationCreate(BaseModel):
    user_id: str = Field(default="sandip_sah")
    workspace_id: str = Field(default="default_workspace")
    notification_type: str = Field(..., description="e.g. 'mission_completed', 'approval_requested'")
    title: str = Field(..., min_length=2, max_length=255)
    message: str = Field(...)
    link: Optional[str] = Field(None, max_length=255)
    dedup_key: Optional[str] = Field(None, max_length=128)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime
    metadata_: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationResponse]
