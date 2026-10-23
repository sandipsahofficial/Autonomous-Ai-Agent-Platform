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
from app.api.memories import get_current_user_id

router = APIRouter(prefix="/schedules", tags=["Workflow Scheduler"])


@router.get("", response_model=ScheduleListResponse)
def list_schedules(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    items = SchedulerService.list_schedules(db, user_id=user_id)
    return ScheduleListResponse(total=len(items), schedules=items)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(
    payload: ScheduleCreate,
    workspace_id: str = Query("default_workspace"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    schedule = SchedulerService.create_schedule(
        db=db,
        user_id=user_id,
        workspace_id=workspace_id,
        payload=payload,
    )
    return schedule


@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    schedule = SchedulerService.get_schedule(db, schedule_id=schedule_id, user_id=user_id)
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
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    schedule = SchedulerService.update_schedule(
        db=db,
        schedule_id=schedule_id,
        user_id=user_id,
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
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not SchedulerService.delete_schedule(db, schedule_id=schedule_id, user_id=user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schedule '{schedule_id}' not found.",
        )


@router.post("/{schedule_id}/run-now", response_model=ScheduleExecutionResponse)
def run_schedule_now(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Manually triggers an immediate run of a configured schedule.
    """
    schedule = SchedulerService.get_schedule(db, schedule_id=schedule_id, user_id=user_id)
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
