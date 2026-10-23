from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user, require_owner_or_admin
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse, MemoryListResponse
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memories", tags=["Agent Memory"])


def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    """
    Extract authenticated user ID from Bearer token, API key, or development session.
    """
    return current_user.id


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_memory(
    payload: MemoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Explicitly persist an agent memory (mission, workspace, or task history).
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot create memories.",
        )
    memory = MemoryService.create_memory(
        db=db,
        user_id=current_user.id,
        key=payload.key,
        content=payload.content,
        memory_type=payload.memory_type,
        workspace_id=payload.workspace_id,
        mission_id=payload.mission_id,
        metadata=payload.metadata,
        ttl_seconds=payload.ttl_seconds,
    )
    return memory


@router.get("", response_model=MemoryListResponse)
def list_memories(
    query: Optional[str] = Query(None, description="Search query keyword matching key or content"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    mission_id: Optional[str] = Query(None, description="Filter by mission ID"),
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve and search persistent memories scoped to the authenticated user.
    """
    memories = MemoryService.search_memories(
        db=db,
        user_id=user_id,
        query=query,
        workspace_id=workspace_id,
        mission_id=mission_id,
        memory_type=memory_type,
        limit=limit,
        offset=offset,
    )
    total = MemoryService.count_memories(
        db=db,
        user_id=user_id,
        query=query,
        workspace_id=workspace_id,
        mission_id=mission_id,
        memory_type=memory_type,
    )
    return MemoryListResponse(total=total, memories=memories)


@router.get("/{memory_id}", response_model=MemoryResponse)
def get_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific memory item by ID with tenant isolation verification.
    """
    memory = MemoryService.get_memory(db, memory_id=memory_id, user_id=user_id)
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item {memory_id} not found or access denied.",
        )
    return memory


@router.put("/{memory_id}", response_model=MemoryResponse)
def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update memory content or metadata.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot update memories.",
        )
    memory = MemoryService.update_memory(
        db,
        memory_id=memory_id,
        user_id=current_user.id,
        content=payload.content,
        metadata=payload.metadata,
    )
    if not memory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item {memory_id} not found or access denied.",
        )
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a memory item enforcing ownership.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot delete memories.",
        )
    deleted = MemoryService.delete_memory(db, memory_id=memory_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory item {memory_id} not found or access denied.",
        )
    return None


@router.post("/cleanup", status_code=status.HTTP_200_OK)
def cleanup_memories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Purge expired TTL memory records.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot clean up memories.",
        )
    deleted_count = MemoryService.cleanup_expired(db)
    return {"cleaned": deleted_count}
