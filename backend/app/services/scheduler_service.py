import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from app.models.schedule import WorkflowSchedule, ScheduleExecution
from app.models.workflow import Workflow
from app.models.task import Task, TaskStatus
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate
from app.services.trace_service import record_execution_event
from app.workflows.compiler import WorkflowCompiler

logger = logging.getLogger(__name__)


def parse_cron_field(field_str: str, min_val: int, max_val: int) -> set[int]:
    """
    Parses a single cron field (*, */n, a-b, a,b,c).
    """
    field_str = field_str.strip()
    result = set()

    if field_str == "*":
        return set(range(min_val, max_val + 1))

    parts = field_str.split(",")
    for part in parts:
        part = part.strip()
        if "/" in part:
            subparts = part.split("/")
            base_range = set(range(min_val, max_val + 1)) if subparts[0] == "*" else parse_cron_field(subparts[0], min_val, max_val)
            step = int(subparts[1])
            result.update({v for v in base_range if (v - min_val) % step == 0})
        elif "-" in part:
            start_s, end_s = part.split("-")
            result.update(range(int(start_s), int(end_s) + 1))
        else:
            result.add(int(part))
    return result


def compute_next_cron_run(cron_expr: str, tz_name: str, from_dt: Optional[datetime] = None) -> datetime:
    """
    Computes the next datetime matching a standard 5-part cron string.
    Returns UTC datetime.
    """
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    now_utc = from_dt or datetime.now(timezone.utc)
    current_local = now_utc.astimezone(tz)

    fields = cron_expr.strip().split()
    if len(fields) != 5:
        # Fallback default: 1 hour from now
        return now_utc + timedelta(hours=1)

    min_set = parse_cron_field(fields[0], 0, 59)
    hour_set = parse_cron_field(fields[1], 0, 23)
    dom_set = parse_cron_field(fields[2], 1, 31)
    month_set = parse_cron_field(fields[3], 1, 12)
    dow_set = parse_cron_field(fields[4], 0, 6)

    # Step forward minute by minute up to 365 days
    check_time = current_local.replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit_time = check_time + timedelta(days=366)

    while check_time < limit_time:
        if (
            check_time.minute in min_set
            and check_time.hour in hour_set
            and check_time.day in dom_set
            and check_time.month in month_set
            and (check_time.weekday() in dow_set or ((check_time.weekday() + 1) % 7) in dow_set)
        ):
            return check_time.astimezone(timezone.utc)
        check_time += timedelta(minutes=1)

    return now_utc + timedelta(hours=24)


class SchedulerService:
    @staticmethod
    def create_schedule(
        db: Session,
        user_id: str,
        workspace_id: str,
        payload: ScheduleCreate,
    ) -> WorkflowSchedule:
        now_utc = datetime.now(timezone.utc)
        next_run = None

        if payload.schedule_type == "one_time":
            next_run = payload.run_at or (now_utc + timedelta(minutes=5))
        else:
            expr = payload.cron_expression or "0 9 * * *"
            next_run = compute_next_cron_run(expr, payload.timezone_str, now_utc)

        schedule = WorkflowSchedule(
            user_id=user_id,
            workspace_id=workspace_id,
            workflow_id=payload.workflow_id,
            name=payload.name,
            goal=payload.goal,
            schedule_type=payload.schedule_type,
            cron_expression=payload.cron_expression,
            timezone_str=payload.timezone_str,
            run_at=payload.run_at,
            next_run_at=next_run,
            is_enabled=payload.is_enabled,
            allow_overlap=payload.allow_overlap,
            max_retries=payload.max_retries,
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def update_schedule(
        db: Session,
        schedule_id: str,
        user_id: str,
        payload: ScheduleUpdate,
    ) -> Optional[WorkflowSchedule]:
        schedule = db.query(WorkflowSchedule).filter(
            WorkflowSchedule.id == schedule_id,
            WorkflowSchedule.user_id == user_id,
        ).first()
        if not schedule:
            return None

        if payload.name is not None:
            schedule.name = payload.name
        if payload.goal is not None:
            schedule.goal = payload.goal
        if payload.workflow_id is not None:
            schedule.workflow_id = payload.workflow_id
        if payload.schedule_type is not None:
            schedule.schedule_type = payload.schedule_type
        if payload.cron_expression is not None:
            schedule.cron_expression = payload.cron_expression
        if payload.timezone_str is not None:
            schedule.timezone_str = payload.timezone_str
        if payload.run_at is not None:
            schedule.run_at = payload.run_at
        if payload.is_enabled is not None:
            schedule.is_enabled = payload.is_enabled
        if payload.allow_overlap is not None:
            schedule.allow_overlap = payload.allow_overlap

        # Recalculate next run
        now_utc = datetime.now(timezone.utc)
        if schedule.schedule_type == "one_time":
            schedule.next_run_at = schedule.run_at
        elif schedule.cron_expression:
            schedule.next_run_at = compute_next_cron_run(
                schedule.cron_expression, schedule.timezone_str, now_utc
            )

        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def list_schedules(db: Session, user_id: str) -> List[WorkflowSchedule]:
        return (
            db.query(WorkflowSchedule)
            .filter(WorkflowSchedule.user_id == user_id)
            .order_by(WorkflowSchedule.created_at.desc())
            .all()
        )

    @staticmethod
    def get_schedule(db: Session, schedule_id: str, user_id: str) -> Optional[WorkflowSchedule]:
        return (
            db.query(WorkflowSchedule)
            .filter(WorkflowSchedule.id == schedule_id, WorkflowSchedule.user_id == user_id)
            .first()
        )

    @staticmethod
    def delete_schedule(db: Session, schedule_id: str, user_id: str) -> bool:
        schedule = SchedulerService.get_schedule(db, schedule_id, user_id)
        if not schedule:
            return False
        db.delete(schedule)
        db.commit()
        return True

    @staticmethod
    def execute_scheduled_run(
        db: Session,
        schedule_id: str,
        is_manual: bool = False,
        target_time: Optional[datetime] = None,
    ) -> Tuple[Optional[ScheduleExecution], Optional[str]]:
        """
        Executes a scheduled run with idempotency locking and concurrency bounds.
        """
        schedule = db.query(WorkflowSchedule).filter(WorkflowSchedule.id == schedule_id).first()
        if not schedule:
            return None, "Schedule not found"

        if not schedule.is_enabled and not is_manual:
            return None, "Schedule is disabled"

        now_utc = datetime.now(timezone.utc)
        scheduled_target = target_time or schedule.next_run_at or now_utc

        # Generate deterministic idempotency key
        if is_manual:
            time_slot = f"manual_{int(now_utc.timestamp())}"
        else:
            # If recently run within this 60s minute window, match last_run_at to enforce idempotency
            last_run = schedule.last_run_at
            if last_run and last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)

            if last_run and abs((now_utc - last_run).total_seconds()) < 60:
                time_slot = last_run.strftime("%Y%m%d%H%M")
            else:
                time_slot = scheduled_target.strftime("%Y%m%d%H%M")

        idempotency_key = f"sched_{schedule.id}_{time_slot}"

        # Check for existing execution with this key to prevent duplicate worker restarts
        existing_exec = db.query(ScheduleExecution).filter(
            ScheduleExecution.idempotency_key == idempotency_key
        ).first()
        if existing_exec:
            return existing_exec, "Idempotent replay: already dispatched for this scheduled window."

        # Check concurrency overlap policy
        if not schedule.allow_overlap:
            active_running = (
                db.query(ScheduleExecution)
                .filter(
                    ScheduleExecution.schedule_id == schedule.id,
                    ScheduleExecution.status == "RUNNING",
                )
                .first()
            )
            if active_running:
                return None, "Skipped: Previous scheduled mission execution is still running."

        # Create execution record
        execution = ScheduleExecution(
            schedule_id=schedule.id,
            idempotency_key=idempotency_key,
            status="RUNNING",
            scheduled_time=scheduled_target,
            executed_time=now_utc,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        try:
            task_id = None
            if schedule.workflow_id:
                workflow = db.query(Workflow).filter(Workflow.id == schedule.workflow_id).first()
                if workflow and workflow.is_enabled:
                    wf_run = WorkflowCompiler.create_run(
                        db=db,
                        workflow=workflow,
                        user_id=schedule.user_id,
                        workspace_id=schedule.workspace_id,
                        initial_inputs={"scheduled_by": schedule.name},
                        goal_override=schedule.goal,
                    )
                    task_id = wf_run.task_id
            
            if not task_id:
                # Dispatch standard agent mission
                task = Task(
                    user_id=schedule.user_id,
                    workspace_id=schedule.workspace_id,
                    goal=schedule.goal,
                    status=TaskStatus.RUNNING,
                    current_stage="planner",
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                task_id = task.id

                record_execution_event(
                    task_id=task.id,
                    event_type="MISSION_STARTED",
                    message=f"Scheduled execution started for schedule '{schedule.name}'",
                    agent_name="scheduler",
                    step_index=0,
                    status="SUCCESS",
                    details={"schedule_id": schedule.id, "idempotency_key": idempotency_key},
                )

            execution.task_id = task_id
            execution.status = "SUCCESS"
            schedule.last_run_at = now_utc
            schedule.failure_count = 0
            schedule.last_error = None

            # Calculate next run timestamp
            if schedule.schedule_type == "one_time":
                schedule.is_enabled = False
                schedule.next_run_at = None
            elif schedule.cron_expression:
                schedule.next_run_at = compute_next_cron_run(
                    schedule.cron_expression, schedule.timezone_str, now_utc
                )

        except Exception as exc:
            execution.status = "FAILED"
            execution.error_message = str(exc)
            schedule.failure_count = (schedule.failure_count or 0) + 1
            schedule.last_error = str(exc)
            logger.error(f"Scheduled run failed for {schedule.id}: {exc}")

        db.commit()
        db.refresh(execution)
        return execution, None
