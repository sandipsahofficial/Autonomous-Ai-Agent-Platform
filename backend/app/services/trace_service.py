import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.task import ExecutionEvent

logger = logging.getLogger(__name__)


def record_execution_event(
    task_id: str,
    event_type: str,
    message: str,
    agent_name: Optional[str] = None,
    step_index: int = 0,
    details: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
) -> Optional[ExecutionEvent]:
    """
    Safely persist an execution timeline event.
    If no db session is provided, creates and closes a short-lived session.
    Never crashes task execution on logging failure.
    """
    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        event = ExecutionEvent(
            task_id=task_id,
            step_index=step_index,
            event_type=event_type,
            agent_name=agent_name,
            message=message,
            details=details,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    except Exception as exc:
        logger.error(f"Failed to record execution event for task {task_id}: {exc}")
        try:
            db.rollback()
        except Exception:
            pass
        return None
    finally:
        if owns_session:
            db.close()
