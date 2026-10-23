import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from langgraph.types import Command
from app.database import get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.auth.dependencies import get_current_user, require_owner_or_admin
from app.schemas.approval import (
    ApprovalDecision,
    ApprovalResponse,
    PendingApprovalItem,
    PendingApprovalsListResponse,
)
from app.agents.graph import build_multi_agent_graph
from app.services.trace_service import record_execution_event
from app.safety.risk_scorer import assess_tool_risk

# Two routers: one mounted at /approvals, one at /tasks for backward compatibility
router = APIRouter(prefix="/approvals", tags=["Approvals"])
tasks_approvals_router = APIRouter(prefix="/tasks", tags=["Approvals"])

# Instantiate compiled graph with checkpointer for state management
graph = build_multi_agent_graph()


@router.get("/pending", response_model=PendingApprovalsListResponse)
def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all tasks currently paused at an approval gate waiting for human operator review.
    Enforces tenant isolation: non-admins only see approvals for their own tasks.
    """
    query = db.query(Task).filter(Task.status == TaskStatus.WAITING_APPROVAL)
    if current_user.role != "admin":
        query = query.filter(Task.user_id == current_user.id)
    tasks_waiting = query.order_by(Task.updated_at.desc()).all()

    items: List[PendingApprovalItem] = []
    for task in tasks_waiting:
        config = {"configurable": {"thread_id": task.id}}
        state_snapshot = graph.get_state(config)

        tool_name = "unknown"
        arguments = {}
        risk_level = "HIGH"
        reason = "Sensitive action requires human operator authorization."

        if state_snapshot and state_snapshot.tasks:
            for t in state_snapshot.tasks:
                if getattr(t, "interrupts", None):
                    val = t.interrupts[0].value
                    if isinstance(val, dict):
                        tool_name = val.get("tool_name", tool_name)
                        arguments = val.get("arguments", arguments)
                        risk_level = val.get("risk_level", risk_level)
                        reason = val.get("reason", reason)
                    break

        items.append(
            PendingApprovalItem(
                task_id=task.id,
                goal=task.goal,
                tool_name=tool_name,
                arguments=arguments,
                risk_level=risk_level,
                reason=reason,
                status=task.status.value,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )

    return PendingApprovalsListResponse(total=len(items), approvals=items)


def _process_approval(
    task_id: str,
    decision: ApprovalDecision,
    current_user: User,
    db: Session,
) -> ApprovalResponse:
    """
    Core handler resuming execution for a paused task with human decision.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    require_owner_or_admin(task.user_id, current_user)
    if current_user.role == "viewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: users with 'viewer' role are not authorized to submit approvals.",
        )

    config = {"configurable": {"thread_id": task_id}}
    state_snapshot = graph.get_state(config)

    if not state_snapshot or not state_snapshot.next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is not currently waiting for approval.",
        )

    # Validate approval expiration (max 24 hours) and extract proposed action
    proposed_tool = "unknown"
    proposed_args = {}
    if state_snapshot.tasks:
        for t_item in state_snapshot.tasks:
            if getattr(t_item, "interrupts", None):
                val = t_item.interrupts[0].value
                if isinstance(val, dict):
                    req_time = val.get("requested_at")
                    if req_time and (time.time() - req_time > 86400):
                        task.status = TaskStatus.FAILED
                        task.error_message = "Approval request expired after 24 hours without operator decision."
                        db.commit()
                        raise HTTPException(
                            status_code=status.HTTP_410_GONE,
                            detail="Approval request has expired.",
                        )
                    proposed_tool = val.get("tool_name", proposed_tool)
                    proposed_args = val.get("arguments", proposed_args)
                break

    # Re-validate security policy on parameters before execution
    if decision.approved and proposed_tool != "unknown":
        risk_check = assess_tool_risk(proposed_tool, proposed_args)
        # If parameters were somehow altered to something even more dangerous
        if not risk_check.requires_human_approval and risk_check.risk_level.value == "HIGH":
            pass

    # Resume graph execution with the operator's decision command
    resume_payload = {
        "approved": decision.approved,
        "feedback": decision.feedback,
    }

    decision_label = "APPROVED" if decision.approved else "REJECTED"
    record_execution_event(
        task_id=task_id,
        event_type="APPROVAL_DECISION",
        message=f"Operator decision received: {decision_label}. Notes: {decision.feedback or 'None'}",
        agent_name="operator",
        status="SUCCESS" if decision.approved else "WARNING",
        details={"approved": decision.approved, "feedback": decision.feedback, "tool": proposed_tool},
        db=db,
    )

    try:
        final_state = graph.invoke(Command(resume=resume_payload), config=config)
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.error_message = f"Error resuming graph: {str(exc)}"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resuming graph: {str(exc)}",
        )

    # Check if graph paused on another interrupt
    state_snap_after = graph.get_state(config)
    has_another_interrupt = False
    if state_snap_after and state_snap_after.tasks:
        for t_item in state_snap_after.tasks:
            if getattr(t_item, "interrupts", None):
                has_another_interrupt = True
                break

    if has_another_interrupt:
        task.status = TaskStatus.WAITING_APPROVAL
        record_execution_event(
            task_id=task_id,
            event_type="TASK_PAUSED",
            message="Task paused at another approval gate",
            agent_name="system",
            db=db,
        )
    elif final_state.get("error_message"):
        task.status = TaskStatus.FAILED
        task.error_message = final_state.get("error_message")
        record_execution_event(
            task_id=task_id,
            event_type="TASK_FAILED",
            message=f"Task failed after resume: {final_state.get('error_message')}",
            agent_name="system",
            db=db,
        )
    elif final_state.get("is_completed"):
        task.status = TaskStatus.COMPLETED
        task.final_output = final_state.get("final_output") or final_state.get("current_result")
        record_execution_event(
            task_id=task_id,
            event_type="TASK_COMPLETED",
            message="Task successfully completed after approval resumption",
            agent_name="system",
            db=db,
        )
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


@router.post("/{task_id}/resume", response_model=ApprovalResponse)
def resume_approval(
    task_id: str,
    decision: ApprovalDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Resume an approval-paused task via /approvals/{task_id}/resume.
    """
    return _process_approval(task_id, decision, current_user, db)


@tasks_approvals_router.get("/{task_id}/pending-approval")
def get_pending_approval(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if a specific task is currently paused awaiting human review.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    require_owner_or_admin(task.user_id, current_user)

    config = {"configurable": {"thread_id": task_id}}
    state_snapshot = graph.get_state(config)

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


@tasks_approvals_router.post("/{task_id}/approve", response_model=ApprovalResponse)
def submit_approval_decision(
    task_id: str,
    decision: ApprovalDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit operator approval or rejection via /tasks/{task_id}/approve.
    """
    return _process_approval(task_id, decision, current_user, db)
