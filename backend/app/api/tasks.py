from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.task import Task, Subtask, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskListResponse, SubtaskCreate, SubtaskResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """
    Create a new agent task with a user goal.
    """
    task = Task(goal=payload.goal, status=TaskStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List tasks with optional status filter and pagination.
    """
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter)

    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()

    return TaskListResponse(total=total, tasks=tasks)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """
    Fetch a task and its ordered subtasks by ID.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """
    Delete a task and its subtasks.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    db.delete(task)
    db.commit()
    return None


@router.post("/{task_id}/subtasks", response_model=SubtaskResponse, status_code=status.HTTP_201_CREATED)
def add_subtask(task_id: str, payload: SubtaskCreate, db: Session = Depends(get_db)):
    """
    Add a subtask to an existing task.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    subtask = Subtask(
        task_id=task_id,
        order_index=payload.order_index,
        title=payload.title,
        description=payload.description,
        assigned_agent=payload.assigned_agent,
    )
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask
