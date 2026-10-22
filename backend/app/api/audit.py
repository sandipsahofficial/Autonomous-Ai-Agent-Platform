from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from app.database import get_db
from app.models.audit import AuditLog

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
    db: Session = Depends(get_db),
):
    """
    Query immutable safety audit logs filtered by task ID, agent, or risk level.
    """
    query = db.query(AuditLog)

    if task_id:
        query = query.filter(AuditLog.task_id == task_id)
    if risk_level:
        query = query.filter(AuditLog.risk_level == risk_level.upper())
    if agent_name:
        query = query.filter(AuditLog.agent_name == agent_name)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()

    return AuditLogListResponse(total=total, logs=logs)
