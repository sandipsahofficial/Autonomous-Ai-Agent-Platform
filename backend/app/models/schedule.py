from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.task import generate_uuid, utc_now


class WorkflowSchedule(Base):
    """
    Persistent schedule for automated workflow / mission execution.
    Supports one-time runs, cron expressions, explicit timezones, idempotency keys,
    and concurrency policies.
    """
    __tablename__ = "workflow_schedules"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    workflow_id = Column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    goal = Column(Text, nullable=False)
    name = Column(String(128), nullable=False)
    
    # Schedule type: "one_time" | "recurring"
    schedule_type = Column(String(32), default="recurring", nullable=False)
    
    # Cron string (e.g. "0 9 * * 1" for Mondays at 9am) or interval
    cron_expression = Column(String(64), nullable=True)
    timezone_str = Column(String(64), default="UTC", nullable=False)
    
    run_at = Column(DateTime(timezone=True), nullable=True)  # For one-time schedules
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    
    is_enabled = Column(Boolean, default=True, nullable=False)
    allow_overlap = Column(Boolean, default=False, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)
    
    # Track consecutive failures for alerting
    failure_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Executions history relationship
    executions = relationship(
        "ScheduleExecution",
        back_populates="schedule",
        cascade="all, delete-orphan",
        order_by="ScheduleExecution.created_at.desc()",
    )


class ScheduleExecution(Base):
    """
    Historical execution record for a scheduled run.
    Ensures idempotency across worker restarts.
    """
    __tablename__ = "schedule_executions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    schedule_id = Column(
        String(36),
        ForeignKey("workflow_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id = Column(String(36), nullable=True, index=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    
    status = Column(String(32), default="RUNNING", nullable=False)  # "SUCCESS", "FAILED", "RUNNING", "SKIPPED"
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    executed_time = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    schedule = relationship("WorkflowSchedule", back_populates="executions")
