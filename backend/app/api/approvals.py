from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from langgraph.types import Command
from app.database import get_db
from app.models.task import Task, TaskStatus
from app.schemas.approval import ApprovalDecision, ApprovalResponse
from app.agents.graph import build_multi_agent_graph

router = APIRouter(prefix="/tasks", tags=["Approvals"])

# Instantiate compiled graph with checkpointer for state management
graph = build_multi_agent_graph()


@router.get("/{task_id}/pending-approval")
def get_pending_approval(task_id: str, db: Session = Depends(get_db)):
    """
    Check if a task is currently paused awaiting human review.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    config = {"configurable": {"thread_id": task_id}}
    state_snapshot = graph.get_state(config)

    # In LangGraph, when interrupted, pending payload is in snapshot.tasks[0].interrupts[0].value
    pending_payload = None
    if state_snapshot and state_snapshot.tasks:
        for t in state_snapshot.tasks:
            if getattr(t, "interrupts", None):
                pending_payload = t.interrupts[0].value
                break

    return {
        "task_id": task_id,
        "status": task.status.value,
        "has_pending_approval": pending_payload is not None,
        "pending_approval": pending_payload,
    }


@router.post("/{task_id}/approve", response_model=ApprovalResponse)
def submit_approval_decision(
    task_id: str,
    decision: ApprovalDecision,
    db: Session = Depends(get_db),
):
    """
    Submit operator approval or rejection for a paused high-risk action,
    resuming graph execution.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    config = {"configurable": {"thread_id": task_id}}
    state_snapshot = graph.get_state(config)

    if not state_snapshot or not state_snapshot.next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is not currently waiting for approval.",
        )

    # Resume graph execution with the operator's decision command
    resume_payload = {
        "approved": decision.approved,
        "feedback": decision.feedback,
    }

    try:
        final_state = graph.invoke(Command(resume=resume_payload), config=config)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming graph: {str(exc)}",
        )

    # Update database task status based on resumed execution
    if final_state.get("is_completed"):
        task.status = TaskStatus.COMPLETED
        task.final_output = final_state.get("final_output")
    elif final_state.get("error_message"):
        task.status = TaskStatus.FAILED
        task.error_message = final_state.get("error_message")
    else:
        task.status = TaskStatus.RUNNING

    task.current_step = final_state.get("current_step", task.current_step)
    task.token_usage = final_state.get("token_usage", task.token_usage)
    task.estimated_cost_usd = final_state.get("estimated_cost_usd", task.estimated_cost_usd)

    db.commit()
    db.refresh(task)

    decision_label = "APPROVED" if decision.approved else "REJECTED"
    return ApprovalResponse(
        task_id=task_id,
        decision=decision_label,
        task_status=task.status.value,
        message=f"Action was {decision_label.lower()} and execution resumed.",
    )
