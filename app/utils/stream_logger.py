"""
Stream logger for Research Intelligence Assistant V2.
Bridges legacy console/array logging with real-time SSE structured lifecycle event publishing.
"""

from typing import Any, Dict, List, Optional
from app.core.correlation import get_correlation_context

stream_events = []


def stream_log(message: str) -> None:
    """Logs message and broadcasts to active SSE subscribers."""
    stream_events.append(message)
    if len(stream_events) > 500:
        stream_events.pop(0)

    # If inside an active background job, publish event to SSE bus
    try:
        ctx = get_correlation_context()
        job_id = ctx.get("job_id")
        if job_id:
            from app.jobs.events import job_event_bus
            job_event_bus.publish_sync(job_id, "agent_log", {"message": message})
    except Exception:
        pass


def emit_lifecycle_event(
    arg1: str,
    arg2: Any = None,
    arg3: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None
) -> None:
    """
    Publishes a structured lifecycle transition event to the active job's SSE bus.
    Supports both signatures:
      - emit_lifecycle_event(event_type, data)
      - emit_lifecycle_event(job_id, event_type, data)
    """
    resolved_job_id = job_id
    if arg3 is not None:
        # Called as emit_lifecycle_event(job_id, event_type, data)
        resolved_job_id = arg1
        event_type = str(arg2)
        payload = arg3 or {}
    elif isinstance(arg2, dict) or arg2 is None:
        # Called as emit_lifecycle_event(event_type, data)
        event_type = arg1
        payload = arg2 or {}
    else:
        event_type = arg1
        payload = {"data": arg2}

    if not resolved_job_id:
        try:
            ctx = get_correlation_context()
            resolved_job_id = ctx.get("job_id")
        except Exception:
            pass

    if resolved_job_id:
        try:
            from app.jobs.events import job_event_bus
            job_event_bus.publish_sync(resolved_job_id, event_type, payload)
        except Exception:
            pass


def get_stream_events() -> List[str]:
    """Returns recent stream events."""
    return list(stream_events)


def clear_stream_events() -> None:
    """Clears stream events list."""
    stream_events.clear()