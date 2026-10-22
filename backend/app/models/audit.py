import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.database import Base


def generate_uuid() -> str:
    """Generate a random UUID4 string as primary key."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """
    Immutable audit trail recording every agent action, risk assessment, and tool invocation.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    task_id = Column(String(36), nullable=True, index=True)
    agent_name = Column(String(64), nullable=False, index=True)
    action_type = Column(String(64), nullable=False)  # e.g., "tool_execution", "approval_decision"
    risk_level = Column(String(16), nullable=False)   # "LOW", "MEDIUM", "HIGH"
    payload = Column(JSON, nullable=True)             # Input arguments, response, or risk explanation

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
