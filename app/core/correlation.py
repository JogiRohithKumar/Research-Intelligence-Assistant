"""
Correlation ID context management for Research Intelligence Assistant V2.
Provides request and job tracing across async tasks and background execution.
"""

import uuid
from contextvars import ContextVar
from typing import Optional

_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_user_id_ctx: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
_session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id", default=None)
_job_id_ctx: ContextVar[Optional[str]] = ContextVar("job_id", default=None)


def get_request_id() -> str:
    """Returns the current request ID or generates a fallback if outside request scope."""
    val = _request_id_ctx.get()
    return val if val else "req_system"


def set_request_id(request_id: Optional[str] = None) -> str:
    """Sets the current request ID in context, generating one if not provided."""
    rid = request_id or f"req_{uuid.uuid4().hex[:12]}"
    _request_id_ctx.set(rid)
    return rid


def get_current_user_id() -> Optional[str]:
    """Returns the authenticated user ID for the current context."""
    return _user_id_ctx.get()


def set_current_user_id(user_id: Optional[str]) -> None:
    """Sets the authenticated user ID in context."""
    _user_id_ctx.set(user_id)


def get_correlation_context() -> dict:
    """Returns the complete correlation dictionary for structured logging and metrics."""
    return {
        "request_id": _request_id_ctx.get(),
        "user_id": _user_id_ctx.get(),
        "session_id": _session_id_ctx.get(),
        "job_id": _job_id_ctx.get(),
    }


def set_job_context(job_id: Optional[str], session_id: Optional[str] = None, user_id: Optional[str] = None) -> None:
    """Sets job and session correlation identifiers."""
    if job_id:
        _job_id_ctx.set(job_id)
    if session_id:
        _session_id_ctx.set(session_id)
    if user_id:
        _user_id_ctx.set(user_id)
