import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    JSON,
    Index,
)
from app.database import Base


def generate_uuid() -> str:
    """Generate a random UUID4 string as primary key."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


class AgentMemory(Base):
    """
    Database-backed persistent agent memory store.
    Supports mission-scoped context, reusable user/workspace strategies, and historical outcomes.
    Enforces strict tenant isolation and memory lifecycle management.
    """
    __tablename__ = "agent_memories"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)
    mission_id = Column(String(36), nullable=True, index=True)
    memory_type = Column(String(32), nullable=False, index=True)  # "mission" | "workspace" | "task_history"
    key = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("ix_agent_memories_user_type", "user_id", "memory_type"),
        Index("ix_agent_memories_user_workspace", "user_id", "workspace_id"),
    )
