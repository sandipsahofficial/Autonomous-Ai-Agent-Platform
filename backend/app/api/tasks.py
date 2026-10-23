from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.task import Task, Subtask, ExecutionEvent, TaskStatus, SubtaskStatus
from app.models.user import User
from app.auth.dependencies import get_current_user, require_owner_or_admin
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskListResponse,
    SubtaskCreate,
    SubtaskResponse,
    TaskTracesResponse,
    ExecutionEventResponse,
)
from app.agents.graph import build_multi_agent_graph
from app.services.trace_service import record_execution_event
from app.config import get_settings

router = APIRouter(prefix="/tasks", tags=["Tasks"])
settings = get_settings()


def run_agent_task_background(task_id: str, goal: str):
    """
    Executes the multi-agent graph in the background and updates DB state.
    """
    graph = build_multi_agent_graph(use_checkpointer=True)
    config = {"configurable": {"thread_id": task_id}}

    db = SessionLocal()
    user_id = "sandip_sah"
    workspace_id = "default_workspace"
    try:
        t_init = db.query(Task).filter(Task.id == task_id).first()
        if t_init:
            user_id = t_init.user_id or user_id
            workspace_id = t_init.workspace_id or workspace_id
    finally:
        db.close()

    initial_state = {
        "task_id": task_id,
        "user_id": user_id,
        "workspace_id": workspace_id,
        "goal": goal,
        "current_stage": "planner",
        "current_step": 0,
        "max_steps": settings.MAX_STEPS,
        "max_rework_attempts": settings.MAX_REWORK_ATTEMPTS,
        "token_usage": 0,
        "estimated_cost_usd": 0.0,
        "token_budget": settings.TOKEN_BUDGET,
        "cost_budget_usd": settings.COST_BUDGET_USD,
        "messages": [],
        "subtasks": [],
        "current_subtask_index": 0,
        "completed_subtask_indices": [],
        "is_completed": False,
    }

    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            t.status = TaskStatus.RUNNING
            t.current_stage = "planner"
            db.commit()

        record_execution_event(
            task_id=task_id,
            event_type="TASK_STARTED",
            message=f"Starting multi-agent execution DAG for goal: {goal}",
            agent_name="system",
            step_index=0,
            db=db,
        )

        final_state = graph.invoke(initial_state, config=config)

        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            # Check if execution paused at an approval interrupt
            state_snapshot = graph.get_state(config)
            has_interrupt = False
            if state_snapshot and state_snapshot.tasks:
                for task_task in state_snapshot.tasks:
                    if getattr(task_task, "interrupts", None):
                        has_interrupt = True
                        break

            # Sync subtasks to DB
            existing_subtasks = db.query(Subtask).filter(Subtask.task_id == task_id).all()
            if not existing_subtasks:
                for st_dict in final_state.get("subtasks", []):
                    st_status = SubtaskStatus.COMPLETED
                    if has_interrupt and st_dict.get("order_index") == final_state.get("current_subtask_index", 0):
                        st_status = SubtaskStatus.WAITING_APPROVAL
                    subtask = Subtask(
                        task_id=task_id,
                        order_index=st_dict.get("order_index", 0),
                        title=st_dict.get("title", ""),
                        description=st_dict.get("description", ""),
                        assigned_agent=st_dict.get("assigned_agent", "executor"),
                        status=st_status,
                        stage=st_dict.get("stage", "completed"),
                        dependencies=st_dict.get("dependencies", []),
                        result=st_dict.get("result", ""),
                    )
                    db.add(subtask)

            subtask_count = len(final_state.get("subtasks", []))
            t.current_step = final_state.get("current_step", 1)
            t.token_usage = final_state.get("token_usage", 0)
            t.estimated_cost_usd = final_state.get("estimated_cost_usd", 0.0)
            t.current_stage = final_state.get("current_stage", "completed")

            if has_interrupt:
                t.status = TaskStatus.WAITING_APPROVAL
                t.current_stage = "tool_gate"
                record_execution_event(
                    task_id=task_id,
                    event_type="TASK_PAUSED",
                    message="Task execution paused: Sensitive action requires human operator approval",
                    agent_name="system",
                    step_index=t.current_step,
                    status="WARNING",
                    db=db,
                )
            elif final_state.get("error_message"):
                t.status = TaskStatus.FAILED
                t.error_message = final_state.get("error_message")
                record_execution_event(
                    task_id=task_id,
                    event_type="TASK_FAILED",
                    message=f"Task terminated with error: {final_state.get('error_message')}",
                    agent_name="system",
                    step_index=t.current_step,
                    status="ERROR",
                    db=db,
                )
            elif final_state.get("is_completed"):
                t.status = TaskStatus.COMPLETED
                t.current_stage = "finalizer"
                t.final_output = final_state.get("final_output") or final_state.get("current_result")
            else:
                t.status = TaskStatus.RUNNING

            db.commit()

    except Exception as exc:
        print(f"Background execution error: {exc}")
        try:
            t = db.query(Task).filter(Task.id == task_id).first()
            if t:
                t.status = TaskStatus.FAILED
                t.error_message = f"Execution failed: {str(exc)}"
                db.commit()
                record_execution_event(
                    task_id=task_id,
                    event_type="TASK_FAILED",
                    message=f"Execution error: {str(exc)}",
                    agent_name="system",
                    status="ERROR",
                    db=db,
                )
        except Exception:
            pass
    finally:
        db.close()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new agent mission with a user goal and trigger autonomous multi-agent execution.
    """
    owner_id = current_user.id if current_user else (payload.user_id or "sandip_sah")
    task = Task(
        goal=payload.goal,
        user_id=owner_id,
        workspace_id=payload.workspace_id or "default_workspace",
        status=TaskStatus.PENDING,
        current_stage="planner",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    record_execution_event(
        task_id=task.id,
        event_type="TASK_CREATED",
        message=f"Mission initialized with goal: '{task.goal}'",
        agent_name="system",
        step_index=0,
        status="INFO",
        db=db,
    )

    background_tasks.add_task(run_agent_task_background, task.id, task.goal)
    return task


@router.post("/{task_id}/cancel", response_model=dict)
def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely cancel an active or paused mission.
    """
    from app.services.recovery_service import TaskRecoveryService
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

    require_owner_or_admin(task.user_id, current_user)
    ok, msg = TaskRecoveryService.cancel_task(db, task_id, current_user.username)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return {"success": True, "message": msg, "task_id": task_id}


@router.post("/recovery/sweep", response_model=dict)
def sweep_stuck_tasks(
    timeout_seconds: int = Query(1800, ge=60, le=86400),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Administrative hook: detect and sweep stalled tasks past execution timeout.
    """
    from app.services.recovery_service import TaskRecoveryService
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required to trigger recovery sweeper.")
    swept = TaskRecoveryService.sweep_stuck_tasks(db, timeout_seconds=timeout_seconds)
    return {"success": True, "swept_count": swept, "timeout_seconds": timeout_seconds}


@router.post("/{task_id}/retry", response_model=TaskResponse)
def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Safely trigger a manual retry for a failed or interrupted mission.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")

    require_owner_or_admin(task.user_id, current_user)

    if task.status not in (TaskStatus.FAILED, TaskStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is in status '{task.status.value}', only FAILED or CANCELLED tasks can be retried.",
        )

    task.status = TaskStatus.RUNNING
    task.error_message = None
    task.current_stage = "planner"
    db.commit()
    db.refresh(task)

    record_execution_event(
        task_id=task.id,
        event_type="RETRY_ATTEMPTED",
        message=f"Manual retry initiated by operator for mission: '{task.goal}'",
        agent_name="operator",
        step_index=task.current_step,
        status="RETRY",
        db=db,
    )

    background_tasks.add_task(run_agent_task_background, task.id, task.goal)
    return task


@router.get("/{task_id}/traces", response_model=TaskTracesResponse)
def get_task_traces(
    task_id: str,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (INFO, SUCCESS, WARNING, ERROR, RETRY)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve structured timeline of execution events for a task with filtering and pagination.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    require_owner_or_admin(task.user_id, current_user)

    query = db.query(ExecutionEvent).filter(ExecutionEvent.task_id == task_id)
    if event_type:
        query = query.filter(ExecutionEvent.event_type == event_type)
    if status_filter:
        query = query.filter(ExecutionEvent.status == status_filter)

    total = query.count()
    events = query.order_by(ExecutionEvent.created_at.asc()).offset(offset).limit(limit).all()

    return TaskTracesResponse(
        task_id=task_id,
        total_events=total,
        events=events,
    )


@router.get("", response_model=TaskListResponse)
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List tasks with optional status filter and pagination.
    Enforces tenant isolation: non-admins only see their own tasks.
    """
    query = db.query(Task)
    if current_user.role != "admin":
        query = query.filter(Task.user_id == current_user.id)
    if status_filter:
        query = query.filter(Task.status == status_filter)

    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()

    return TaskListResponse(total=total, tasks=tasks)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch a task and its ordered subtasks by ID.
    Enforces ownership verification.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    require_owner_or_admin(task.user_id, current_user)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a task and its subtasks.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    require_owner_or_admin(task.user_id, current_user)
    db.delete(task)
    db.commit()
    return None


@router.post("/{task_id}/subtasks", response_model=SubtaskResponse, status_code=status.HTTP_201_CREATED)
def add_subtask(
    task_id: str,
    payload: SubtaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add a subtask to an existing task.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )
    require_owner_or_admin(task.user_id, current_user)
    subtask = Subtask(
        task_id=task_id,
        order_index=payload.order_index,
        title=payload.title,
        description=payload.description,
        assigned_agent=payload.assigned_agent,
        dependencies=payload.dependencies or [],
        stage=payload.stage or "pending",
        retry_count=payload.retry_count or 0,
    )
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask
