from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
)
from app.database import Base
from app.models.task import generate_uuid, utc_now


class Notification(Base):
    """
    In-app notification for mission events, approval requests, scheduled runs,
    and workflow alerts.
    """
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    notification_type = Column(String(64), nullable=False, index=True)  # e.g. "mission_completed", "approval_requested"
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(255), nullable=True)  # e.g. "/tasks/{id}" or "/approvals"
    
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    dedup_key = Column(String(128), nullable=True, index=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
