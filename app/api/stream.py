"""
Real-time Server-Sent Events (SSE) API Endpoints for Research Intelligence Assistant V2.
Streams authenticated, genuine LangGraph execution progress directly to researchers.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.logging import logger
from app.core.rate_limiter import limiter
from app.db.base import SessionLocal
from app.db.models import ResearchJob, User
from app.db.session import get_db
from app.jobs.events import job_event_bus
from app.utils.stream_logger import get_stream_events

settings = get_settings()
router = APIRouter(tags=["Streaming"])


def authenticate_sse_user(
    request: Request,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticates SSE stream connection from Authorization header or URL token parameter.
    Standard EventSource in web browsers cannot customize headers, necessitating URL token support.
    """
    auth_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        auth_token = auth_header.split(" ", 1)[1]
    elif token:
        auth_token = token

    if auth_token:
        try:
            payload = decode_access_token(auth_token)
            user_id = payload.get("sub")
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active:
                return user
        except AuthenticationError:
            pass

    if not settings.AUTH_ENABLED:
        dev_user = db.query(User).filter(User.username == "dev_user").first()
        if not dev_user:
            dev_user = User(
                id="usr_local_dev_tenant",
                username="dev_user",
                email="dev@example.local",
                hashed_password="[DEV_MOCK]",
                is_active=True
            )
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)
        return dev_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Valid authentication token required to connect to SSE stream"
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_events(
    job_id: str,
    request: Request,
    user: User = Depends(authenticate_sse_user),
    db: Session = Depends(get_db)
):
    """
    Authoritative Server-Sent Events stream for a specific research job.
    Strictly verifies multi-tenant ownership before initiating stream.
    """
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research job '{job_id}' not found"
        )

    if job.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to subscribe to this research stream"
        )

    last_event_id = request.headers.get("Last-Event-ID")
    logger.info(f"SSE client connected to job='{job_id}' (user='{user.id}', last_event_id='{last_event_id}')")

    event_generator = job_event_bus.subscribe(job_id, last_event_id=last_event_id)
    return EventSourceResponse(event_generator)


@router.get("/stream")
def legacy_stream_events():
    """
    Maintained for backward compatibility with Stage 1-6 smoke test assertions.
    Returns recent global events.
    """
    events = get_stream_events()
    return {
        "events": events
    }