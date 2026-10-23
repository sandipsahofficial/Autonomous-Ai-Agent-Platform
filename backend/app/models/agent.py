import enum
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
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.task import generate_uuid, utc_now


class AgentRole(str, enum.Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    EXECUTOR = "executor"
    CODER = "coder"
    REVIEWER = "reviewer"
    FINALIZER = "finalizer"
    CUSTOM = "custom"


class ReviewPolicy(str, enum.Enum):
    STRICT = "strict"
    STANDARD = "standard"
    LENIENT = "lenient"
    NONE = "none"


class CustomAgent(Base):
    """
    Configurable custom AI agent definition.
    Stores assigned role, permitted tools, execution limits, model preference,
    system instructions, and validation policies.
    """
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False, index=True)
    description = Column(Text, nullable=True)
    role = Column(String(64), default="custom", nullable=False)
    
    # Security permissions: explicit whitelist of tool names this agent may invoke
    permitted_tools = Column(JSON, default=list, nullable=False)
    
    # Inference parameters
    model_provider = Column(String(32), default="ollama", nullable=False)  # "ollama", "openai", "claude", "mock"
    model_name = Column(String(64), default="llama3", nullable=False)
    temperature = Column(Float, default=0.7, nullable=False)
    max_steps = Column(Integer, default=10, nullable=False)
    
    # System behavior & guardrails
    system_prompt = Column(Text, nullable=False)
    review_policy = Column(String(32), default="standard", nullable=False)
    
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
