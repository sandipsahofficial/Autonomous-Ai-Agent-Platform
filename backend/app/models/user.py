import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.task import generate_uuid, utc_now


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """
    User account model for authentication, role-based access control (RBAC),
    and tenant/resource ownership isolation.
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default=UserRole.OPERATOR.value, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    """
    Hashed API Key for programmatic machine-to-machine authentication.
    Raw keys are never stored; only cryptographic SHA-256 digests are persisted.
    """
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), default="Default Key", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="api_keys")
