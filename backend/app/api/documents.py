from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.document import Document
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentRetrievalResult,
)
from app.services.document_service import DocumentService
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/documents", tags=["Knowledge Base & Retrieval"])


class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search query terms")
    limit: int = Field(default=5, ge=1, le=20)
    workspace_id: Optional[str] = None


class DocumentTextCreate(BaseModel):
    filename: str = Field(..., min_length=2, max_length=255, description="Document name, e.g. 'notes.md'")
    content: str = Field(..., min_length=1, description="Raw text or markdown content")
    workspace_id: str = Field(default="default_workspace")


@router.get("", response_model=DocumentListResponse)
def list_documents(
    workspace_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = DocumentService.list_documents(db, user_id=current_user.id, workspace_id=workspace_id)
    return DocumentListResponse(total=len(docs), documents=docs)


@router.post("/text", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_text_document(
    payload: DocumentTextCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Directly ingest plain text or markdown documentation via JSON payload.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot upload documents.",
        )
    raw_bytes = payload.content.encode("utf-8")
    doc, err = DocumentService.upload_document(
        db=db,
        user_id=current_user.id,
        workspace_id=payload.workspace_id,
        filename=payload.filename,
        raw_bytes=raw_bytes,
        mime_type="text/plain",
    )
    if err or not doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to ingest document",
        )
    return doc


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form("default_workspace"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and parse TXT, MD, PDF, or DOCX documents into chunks for retrieval.
    Enforces MIME type, magic byte, and size verification.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot upload documents.",
        )
    raw_bytes = await file.read()
    filename = file.filename or "uploaded_document.txt"
    mime_type = file.content_type

    doc, err = DocumentService.upload_document(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        filename=filename,
        raw_bytes=raw_bytes,
        mime_type=mime_type,
    )
    if err or not doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err or "Failed to upload document",
        )
    return doc


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot delete documents.",
        )
    if not DocumentService.delete_document(db, doc_id=document_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )


@router.post("/search", response_model=DocumentRetrievalResult)
def search_documents(
    payload: DocumentSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Queries document chunks and returns verified citations with untrusted context framing.
    """
    return DocumentService.search_knowledge_base(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        limit=payload.limit,
        workspace_id=payload.workspace_id,
    )
