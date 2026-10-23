import logging
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.models.workflow import WorkflowRun
from app.services.trace_service import record_execution_event

logger = logging.getLogger("mesh.recovery")


class TaskRecoveryService:
    """
    Automated worker crash recovery, stuck-job sweeper, and cancellation manager.
    Prevents orphaned tasks from blocking execution queues across worker restarts.
    """

    @classmethod
    def sweep_stuck_tasks(cls, db: Session, timeout_seconds: int = 1800) -> int:
        """
        Detects tasks marked RUNNING that have stalled past the execution timeout without heartbeat.
        Safely transitions them to FAILED with explicit recovery diagnosis.
        """
        now_utc = datetime.now(timezone.utc)
        stuck_threshold = now_utc - timedelta(seconds=timeout_seconds)

        stuck_tasks = (
            db.query(Task)
            .filter(
                Task.status.in_([TaskStatus.RUNNING, TaskStatus.PLANNING]),
                Task.updated_at < stuck_threshold,
            )
            .all()
        )

        recovered_count = 0
        for task in stuck_tasks:
            task.status = TaskStatus.FAILED
            task.error_message = (
                f"Task execution timed out: no worker heartbeat recorded for > {timeout_seconds // 60} minutes. "
                "Safe manual retry is available via /api/v1/tasks/{id}/retry."
            )
            record_execution_event(
                task_id=task.id,
                event_type="TASK_STUCK_TIMEOUT",
                message="Automated recovery: marked stalled task as FAILED to unblock queue.",
                agent_name="recovery_sweeper",
                step_index=task.current_step,
                status="ERROR",
                details={"timeout_seconds": timeout_seconds, "last_updated": str(task.updated_at)},
                db=db,
            )
            recovered_count += 1

        # Also sweep stalled workflow runs
        stuck_runs = (
            db.query(WorkflowRun)
            .filter(
                WorkflowRun.status == "RUNNING",
                WorkflowRun.updated_at < stuck_threshold,
            )
            .all()
        )
        for run in stuck_runs:
            run.status = "FAILED"
            run.error_message = f"Workflow run stalled: no activity past {timeout_seconds // 60} min threshold."

        if recovered_count > 0 or stuck_runs:
            db.commit()
            logger.warning(
                f"[Recovery] Swept {recovered_count} stalled tasks and {len(stuck_runs)} workflow runs."
            )

        return recovered_count

    @classmethod
    def cancel_task(cls, db: Session, task_id: str, operator_id: str) -> Tuple[bool, str]:
        """
        Explicitly cancels an active or paused mission.
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False, f"Task {task_id} not found"

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False, f"Task is already in terminal state '{task.status.value}'"

        task.status = TaskStatus.CANCELLED
        task.error_message = f"Mission cancelled by operator '{operator_id}'."
        record_execution_event(
            task_id=task.id,
            event_type="TASK_CANCELLED",
            message=f"Mission terminated prematurely by operator {operator_id}.",
            agent_name="operator",
            step_index=task.current_step,
            status="WARNING",
            details={"operator_id": operator_id},
            db=db,
        )
        db.commit()
        db.refresh(task)
        return True, "Task cancelled successfully."
