from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from app.database import get_db
from app.models.audit import AuditLog
from app.models.task import Task
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


class AuditLogResponse(BaseModel):
    id: str
    task_id: Optional[str]
    agent_name: str
    action_type: str
    risk_level: str
    payload: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    total: int
    logs: List[AuditLogResponse]


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    task_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Query immutable safety audit logs filtered by task ID, agent, or risk level.
    Enforces tenant isolation: non-admin users only view audit logs for tasks they own.
    """
    query = db.query(AuditLog)

    if current_user.role != UserRole.ADMIN.value:
        user_task_ids = [t[0] for t in db.query(Task.id).filter(Task.user_id == current_user.id).all()]
        if task_id:
            if task_id not in user_task_ids:
                return AuditLogListResponse(total=0, logs=[])
            query = query.filter(AuditLog.task_id == task_id)
        else:
            query = query.filter(AuditLog.task_id.in_(user_task_ids))
    elif task_id:
        query = query.filter(AuditLog.task_id == task_id)

    if risk_level:
        query = query.filter(AuditLog.risk_level == risk_level.upper())
    if agent_name:
        query = query.filter(AuditLog.agent_name == agent_name)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(total=total, logs=logs)
