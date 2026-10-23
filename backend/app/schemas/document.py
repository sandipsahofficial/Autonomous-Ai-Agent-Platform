from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class DocumentChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    page_number: int
    content: str
    token_count: int
    metadata_: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: str
    user_id: str
    workspace_id: str
    filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    page_count: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    chunks: List[DocumentChunkResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]


class DocumentCitation(BaseModel):
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    matched_snippet: str
    score: float


class DocumentRetrievalResult(BaseModel):
    query: str
    citations: List[DocumentCitation]
    total_found: int
    untrusted_context_block: str
