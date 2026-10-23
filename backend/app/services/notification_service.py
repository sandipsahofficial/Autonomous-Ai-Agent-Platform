import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        workspace_id: str = "default_workspace",
        dedup_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Notification]:
        """
        Creates a notification with deduplication checks to prevent replay spam.
        """
        if dedup_key:
            existing = db.query(Notification).filter(
                Notification.dedup_key == dedup_key,
                Notification.user_id == user_id,
            ).first()
            if existing:
                return existing

        notification = Notification(
            user_id=user_id,
            workspace_id=workspace_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            dedup_key=dedup_key,
            metadata_=metadata or {},
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def list_notifications(
        db: Session,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> Tuple[List[Notification], int, int]:
        query = db.query(Notification).filter(Notification.user_id == user_id)
        total = query.count()
        unread_count = query.filter(Notification.is_read == False).count()

        if unread_only:
            query = query.filter(Notification.is_read == False)

        items = query.order_by(Notification.created_at.desc()).limit(limit).all()
        return items, total, unread_count

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user_id: str) -> bool:
        item = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        ).first()
        if not item:
            return False
        item.is_read = True
        db.commit()
        return True

    @staticmethod
    def mark_all_as_read(db: Session, user_id: str) -> int:
        updated = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .update({"is_read": True})
        )
        db.commit()
        return updated
