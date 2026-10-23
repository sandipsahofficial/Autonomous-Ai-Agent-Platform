from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    Float,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.task import generate_uuid, utc_now


class Workflow(Base):
    """
    Visual graph workflow automation definition.
    Persists node and edge structures, version state, and execution policies.
    """
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # Graph structure: { nodes: [...], edges: [...], triggers: [...], variables: {...} }
    definition = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    versions = relationship(
        "WorkflowVersion",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowVersion.version.desc()",
    )
    runs = relationship(
        "WorkflowRun",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowRun.created_at.desc()",
    )


class WorkflowVersion(Base):
    """
    Immutable versioned snapshot of a workflow definition for reproducibility.
    """
    __tablename__ = "workflow_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workflow_id = Column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    definition = Column(JSON, default=dict, nullable=False)
    changelog = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    workflow = relationship("Workflow", back_populates="versions")


class WorkflowRun(Base):
    """
    Execution instance of a workflow definition.
    Tracks node-level states (completed, active, waiting, failed), outputs, and timing.
    """
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    workflow_id = Column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    task_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    status = Column(String(32), default="PENDING", nullable=False, index=True)
    # Node state map: { [node_id]: { status: "completed"|"active"|"waiting"|"failed", output: ..., error: ..., started_at: ..., duration_ms: ... } }
    node_states = Column(JSON, default=dict, nullable=False)
    
    execution_context = Column(JSON, default=dict, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    workflow = relationship("Workflow", back_populates="runs")
