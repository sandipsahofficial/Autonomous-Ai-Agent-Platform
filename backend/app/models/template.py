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
)
from app.database import Base
from app.models.task import generate_uuid, utc_now


class Template(Base):
    """
    Reusable agent or workflow template.
    Can be browsed, searched, cloned into user workspaces, exported to JSON,
    and imported with untrusted input validation.
    """
    __tablename__ = "templates"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    template_type = Column(String(32), default="workflow", nullable=False)  # "agent" | "workflow"
    name = Column(String(128), nullable=False)
    slug = Column(String(128), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(64), default="general", nullable=False, index=True)
    version = Column(String(32), default="1.0.0", nullable=False)
    
    # Template schema payload: stores agent config or workflow nodes/edges
    content = Column(JSON, default=dict, nullable=False)
    
    is_builtin = Column(Boolean, default=False, nullable=False)
    author = Column(String(64), default="MESH System", nullable=False)
    tags = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
