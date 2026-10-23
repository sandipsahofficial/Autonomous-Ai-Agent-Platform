import asyncio
import json
import logging
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.task import Task, ExecutionEvent, TaskStatus
from app.api.memories import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Streaming Execution"])


def format_sse_message(event_id: str, event_type: str, data: dict) -> str:
    """
    Format standard SSE payload with id, event, and data fields.
    """
    # Exclude internal chain of thought, credentials, or private state
    sanitized_data = {k: v for k, v in data.items() if k not in ("chain_of_thought", "raw_prompt", "credentials")}
    data_json = json.dumps(sanitized_data)
    return f"id: {event_id}\nevent: {event_type.lower()}\ndata: {data_json}\n\n"


async def event_generator(
    task_id: str,
    user_id: str,
    last_event_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Server-Sent Events generator streaming mission progress from persisted ExecutionEvents.
    Supports reconnection and replaying from Last-Event-ID.
    """
    sent_event_ids = set()
    found_last = last_event_id is None

    # First pass: stream historical events
    with SessionLocal() as db:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            yield format_sse_message("error", "error", {"message": "Mission not found"})
            return

        # Authorization: verify ownership if user_id is set
        if task.user_id and task.user_id != user_id and user_id != "admin":
            yield format_sse_message("error", "error", {"message": "Unauthorized access to mission"})
            return

        events = (
            db.query(ExecutionEvent)
            .filter(ExecutionEvent.task_id == task_id)
            .order_by(ExecutionEvent.step_index.asc(), ExecutionEvent.created_at.asc())
            .all()
        )

        for ev in events:
            if not found_last:
                if ev.id == last_event_id:
                    found_last = True
                continue

            sent_event_ids.add(ev.id)
            payload = {
                "event_id": ev.id,
                "task_id": ev.task_id,
                "event_type": ev.event_type,
                "step_index": ev.step_index,
                "agent_name": ev.agent_name,
                "status": ev.status,
                "duration_ms": ev.duration_ms,
                "message": ev.message,
                "details": ev.details or {},
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            yield format_sse_message(ev.id, ev.event_type, payload)

    # Second pass: live stream loop
    max_idle_seconds = 120
    idle_counter = 0

    while idle_counter < max_idle_seconds:
        await asyncio.sleep(0.8)
        new_events = []
        is_task_final = False

        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                break

            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                is_task_final = True

            unprocessed = (
                db.query(ExecutionEvent)
                .filter(ExecutionEvent.task_id == task_id)
                .order_by(ExecutionEvent.step_index.asc(), ExecutionEvent.created_at.asc())
                .all()
            )
            for ev in unprocessed:
                if ev.id not in sent_event_ids:
                    sent_event_ids.add(ev.id)
                    new_events.append(ev)

        for ev in new_events:
            payload = {
                "event_id": ev.id,
                "task_id": ev.task_id,
                "event_type": ev.event_type,
                "step_index": ev.step_index,
                "agent_name": ev.agent_name,
                "status": ev.status,
                "duration_ms": ev.duration_ms,
                "message": ev.message,
                "details": ev.details or {},
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            yield format_sse_message(ev.id, ev.event_type, payload)

        if new_events:
            idle_counter = 0
        else:
            idle_counter += 1
            # Send keep-alive comment
            yield ": ping\n\n"

        if is_task_final and not new_events:
            # Yield final completion notice
            yield format_sse_message(
                f"final_{task_id}",
                "stream_closed",
                {"task_id": task_id, "status": task.status.value, "final": True},
            )
            break


@router.get("/{task_id}/events/stream")
async def stream_task_events(
    task_id: str,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    since_id: Optional[str] = Query(None, description="Optional replay point from specific event ID"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events (SSE) streaming real-time mission execution progress.
    Supports reconnection and replaying from Last-Event-ID.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mission '{task_id}' not found.",
        )

    # Mission-level authorization
    if task.user_id and task.user_id != user_id and user_id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this mission.",
        )

    resume_id = last_event_id or since_id

    return StreamingResponse(
        event_generator(task_id, user_id, resume_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
