from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
)
from app.services.notification_service import NotificationService
from app.api.memories import get_current_user_id

router = APIRouter(prefix="/notifications", tags=["Notification Center"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items, total, unread_count = NotificationService.list_notifications(
        db, user_id=user_id, unread_only=unread_only, limit=limit
    )
    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        notifications=items,
    )


@router.post("/{notification_id}/read", response_model=dict)
def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not NotificationService.mark_as_read(db, notification_id, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification '{notification_id}' not found.",
        )
    return {"success": True, "id": notification_id}


@router.post("/read-all", response_model=dict)
def mark_all_notifications_read(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    updated = NotificationService.mark_all_as_read(db, user_id)
    return {"success": True, "updated_count": updated}
