from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.task import Task, Subtask, TaskStatus, SubtaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskListResponse, SubtaskCreate, SubtaskResponse
from app.agents.graph import build_multi_agent_graph

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def run_agent_task_background(task_id: str, goal: str):
    """
    Executes the multi-agent graph in the background and updates DB state.
    """
    graph = build_multi_agent_graph(use_checkpointer=True)
    config = {"configurable": {"thread_id": task_id}}
    initial_state = {
        "task_id": task_id,
        "goal": goal,
        "current_step": 0,
        "max_steps": 12,
        "max_rework_attempts": 2,
        "token_usage": 0,
        "estimated_cost_usd": 0.0,
        "messages": [],
        "subtasks": [],
        "current_subtask_index": 0,
        "is_completed": False,
    }

    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == task_id).first()
        if t:
            t.status = TaskStatus.RUNNING
            db.commit()

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
                        assigned_agent=st_dict.get("assigned_agent", "worker"),
                        status=st_status,
                        result=st_dict.get("result", ""),
                    )
                    db.add(subtask)

            t.current_step = final_state.get("current_step", 1)
            t.token_usage = final_state.get("token_usage", 0)
            t.estimated_cost_usd = final_state.get("estimated_cost_usd", 0.0)

            if has_interrupt:
                t.status = TaskStatus.WAITING_APPROVAL
            elif final_state.get("error_message"):
                t.status = TaskStatus.FAILED
                t.error_message = final_state.get("error_message")
            elif final_state.get("is_completed"):
                t.status = TaskStatus.COMPLETED
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
        except Exception:
            pass
    finally:
        db.close()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Create a new agent task with a user goal and trigger background execution.
    """
    task = Task(goal=payload.goal, status=TaskStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(run_agent_task_background, task.id, task.goal)
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
