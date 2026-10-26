from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ScheduleExecutionResponse,
)
from app.services.scheduler_service import SchedulerService
from app.models.user import User, UserRole
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/schedules", tags=["Workflow Scheduler"])


@router.get("", response_model=ScheduleListResponse)
def list_schedules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = SchedulerService.list_schedules(db, user_id=current_user.id)
    return ScheduleListResponse(total=len(items), schedules=items)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    workspace_id: str = Query("default_workspace"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot create schedules.",
        )
    if payload.workflow_id:
        from app.models.workflow import Workflow
        wf = db.query(Workflow).filter(Workflow.id == payload.workflow_id).first()
        if not wf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced workflow '{payload.workflow_id}' not found.",
            )
        if wf.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot schedule another tenant's workflow.",
            )
    schedule = SchedulerService.create_schedule(
        db=db,
        user_id=current_user.id,
        workspace_id=workspace_id,
        payload=payload,
    )
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    schedule = SchedulerService.get_schedule(db, schedule_id=schedule_id, user_id=current_user.id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found.",
        )
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(
    schedule_id: str,
    payload: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot update schedules.",
        )
    if payload.workflow_id:
        from app.models.workflow import Workflow
        wf = db.query(Workflow).filter(Workflow.id == payload.workflow_id).first()
        if not wf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced workflow '{payload.workflow_id}' not found.",
            )
        if wf.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot schedule another tenant's workflow.",
            )
    schedule = SchedulerService.update_schedule(
        db=db,
        schedule_id=schedule_id,
        user_id=current_user.id,
        payload=payload,
    )
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found.",
        )
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot delete schedules.",
        )
    if not SchedulerService.delete_schedule(db, schedule_id=schedule_id, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found.",
        )


@router.post("/{schedule_id}/run-now", response_model=ScheduleExecutionResponse)
def run_schedule_now(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Manually triggers an immediate run of a configured schedule.
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.OPERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' cannot execute schedules.",
        )
    schedule = SchedulerService.get_schedule(db, schedule_id=schedule_id, user_id=current_user.id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found.",
        )

    execution, err = SchedulerService.execute_scheduled_run(db, schedule_id=schedule_id, is_manual=True)
    if err and not execution:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err,
        )
    return execution
