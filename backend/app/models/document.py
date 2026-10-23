from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.task import generate_uuid, utc_now


class Document(Base):
    """
    Uploaded knowledge base document (TXT, Markdown, PDF, DOCX).
    Stores file metadata, ownership, size verification, and chunking parameters.
    """
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    filename = Column(String(255), nullable=False)
    file_type = Column(String(16), nullable=False)  # "txt", "md", "pdf", "docx"
    mime_type = Column(String(64), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    page_count = Column(Integer, default=1, nullable=False)
    
    # Storage or extraction status
    status = Column(String(32), default="PROCESSED", nullable=False)  # "PENDING", "PROCESSED", "FAILED"
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )


class DocumentChunk(Base):
    """
    Extracted textual chunk from a document for citation-backed retrieval.
    Includes page numbers and offsets for verifiable evidence.
    """
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    document_id = Column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(64), default="sandip_sah", nullable=False, index=True)
    workspace_id = Column(String(64), default="default_workspace", nullable=False, index=True)

    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, default=1, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    
    # Metadata for citations: e.g. section title, paragraph index
    metadata_ = Column("metadata", JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="chunks")
