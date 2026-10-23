import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid() -> str:
    """Generate a random UUID4 string as primary key."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SubtaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Task(Base):
    """
    Primary user-submitted goal and overall execution progress.
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)
    goal = Column(Text, nullable=False)
    status = Column(
        SQLEnum(TaskStatus, native_enum=False),
        default=TaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    current_stage = Column(String(32), default="planner", nullable=False)
    current_step = Column(Integer, default=0, nullable=False)
    rework_count = Column(Integer, default=0, nullable=False)
    token_usage = Column(Integer, default=0, nullable=False)
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    final_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    subtasks = relationship(
        "Subtask",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="Subtask.order_index",
    )
    execution_events = relationship(
        "ExecutionEvent",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ExecutionEvent.created_at",
    )


class Subtask(Base):
    """
    Ordered subtasks produced by the Planner agent.
    """
    __tablename__ = "subtasks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    task_id = Column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    assigned_agent = Column(String(64), nullable=False)  # "researcher", "executor", or legacy "coder"
    status = Column(
        SQLEnum(SubtaskStatus, native_enum=False),
        default=SubtaskStatus.PENDING,
        nullable=False,
    )
    stage = Column(String(32), default="pending", nullable=False)
    dependencies = Column(JSON, nullable=True, default=list)
    retry_count = Column(Integer, default=0, nullable=False)
    result = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    task = relationship("Task", back_populates="subtasks")


class ExecutionEvent(Base):
    """
    Structured timeline event recorded during task planning and agent execution.
    Persists granular state changes, agent activations, tool calls, and human approvals.
    """
    __tablename__ = "execution_events"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    task_id = Column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index = Column(Integer, default=0, nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    agent_name = Column(String(64), nullable=True, index=True)
    status = Column(String(32), default="INFO", nullable=False)
    duration_ms = Column(Float, nullable=True)
    idempotency_key = Column(String(64), nullable=True, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    task = relationship("Task", back_populates="execution_events")

