import logging
import re
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.task import ExecutionEvent

logger = logging.getLogger(__name__)

SECRET_REGEX = re.compile(r"(?i)(api[_-]?key|secret|password|bearer|auth|token)")


def sanitize_trace_details(details: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Sanitize sensitive keys/tokens from metadata before saving into database traces.
    """
    if not details or not isinstance(details, dict):
        return details

    sanitized = {}
    for k, v in details.items():
        if SECRET_REGEX.search(str(k)):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = sanitize_trace_details(v)
        elif isinstance(v, str) and len(v) > 2000:
            # Prevent excessive payload bloat
            sanitized[k] = v[:2000] + "...[TRUNCATED]"
        else:
            sanitized[k] = v
    return sanitized


def record_execution_event(
    task_id: str,
    event_type: str,
    message: str,
    agent_name: Optional[str] = None,
    step_index: int = 0,
    status: str = "INFO",
    duration_ms: Optional[float] = None,
    idempotency_key: Optional[str] = None,
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
        clean_details = sanitize_trace_details(details)
        event = ExecutionEvent(
            task_id=task_id,
            step_index=step_index,
            event_type=event_type,
            agent_name=agent_name,
            status=status,
            duration_ms=duration_ms,
            idempotency_key=idempotency_key,
            message=message,
            details=clean_details,
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
