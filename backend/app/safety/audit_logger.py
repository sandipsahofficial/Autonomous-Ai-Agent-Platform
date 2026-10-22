import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.audit import AuditLog


def record_audit_log(
    agent_name: str,
    action_type: str,
    risk_level: str,
    payload: Dict[str, Any],
    task_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> AuditLog:
    """
    Persists an immutable audit log entry recording agent decisions,
    risk assessments, and tool executions.
    """
    entry = AuditLog(
        task_id=task_id,
        agent_name=agent_name,
        action_type=action_type,
        risk_level=risk_level,
        payload=payload,
    )

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as exc:
        db.rollback()
        # Non-fatal log fallback to console if database is temporarily unavailable
        print(f"Audit log write warning: {exc}")
        return entry
    finally:
        if should_close:
            db.close()
