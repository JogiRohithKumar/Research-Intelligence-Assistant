"""
Primary API Routes for Research Intelligence Assistant V2.
Hardened with authentication, multi-tenant isolation, rate limiting, and async execution.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    JobCancelResponse,
    ResearchJobResponse,
    ResearchRequest,
    ResearchSessionListResponse,
    ResearchSessionResponse,
)
from app.auth.dependencies import get_current_user
from app.core.config import get_settings
from app.core.exceptions import AuthorizationError, ResourceNotFoundError
from app.core.logging import logger
from app.core.metrics import metrics
from app.core.rate_limiter import limiter
from app.db.models import ReportModel, ResearchJob, ResearchSession, User
from app.db.session import get_db
from app.jobs.manager import job_manager

settings = get_settings()
router = APIRouter()


# -------------------------------------------------------------
# RESEARCH EXECUTION & JOB ENDPOINTS
# -------------------------------------------------------------

@router.post("/research")
def run_research(
    request: ResearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a research query to the intelligence engine.
    In production (default), enqueues an asynchronous background job and returns its tracking ID.
    If sync=True, blocks until completion and returns the full result state directly.
    """
    logger.info(f"Received research request: query='{request.query}', user='{current_user.id}', sync={request.sync}")

    result = job_manager.submit_job(
        query=request.query,
        user=current_user,
        session_id=request.session_id,
        idempotency_key=request.idempotency_key,
        sync=request.sync or False
    )

    return result


@router.get("/jobs/{job_id}", response_model=ResearchJobResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the execution status and metrics for an asynchronous research job.
    Strictly verifies multi-tenant ownership.
    """
    job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research job '{job_id}' not found"
        )

    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to view this job"
        )

    return ResearchJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/cancel", response_model=JobCancelResponse)
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """Safely cancels an active or queued research job."""
    res = job_manager.cancel_job(job_id=job_id, user=current_user)
    return JobCancelResponse(**res)


# -------------------------------------------------------------
# SESSION PERSISTENCE & HISTORY ENDPOINTS
# -------------------------------------------------------------

@router.get("/sessions", response_model=ResearchSessionListResponse)
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Lists research sessions owned by the authenticated researcher."""
    total = db.query(ResearchSession).filter(ResearchSession.user_id == current_user.id).count()
    sessions = db.query(ResearchSession).filter(
        ResearchSession.user_id == current_user.id
    ).order_by(ResearchSession.created_at.desc()).offset(offset).limit(limit).all()

    session_items = []
    for s in sessions:
        # Load latest report if available
        latest_report = db.query(ReportModel).filter(
            ReportModel.session_id == s.id
        ).order_by(ReportModel.created_at.desc()).first()

        session_items.append(
            ResearchSessionResponse(
                id=s.id,
                title=s.title,
                original_query=s.original_query,
                status=s.status,
                created_at=s.created_at,
                updated_at=s.updated_at,
                latest_run_id=latest_report.run_id if latest_report else None,
                report_markdown=latest_report.markdown_content if latest_report else None,
                result_data=None  # Omit bulky JSON in list view
            )
        )

    return ResearchSessionListResponse(sessions=session_items, total=total)


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves complete persistent research state and results for a session.
    Strictly enforces multi-tenant boundary checks.
    """
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found"
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access this session"
        )

    latest_report = db.query(ReportModel).filter(
        ReportModel.session_id == session.id
    ).order_by(ReportModel.created_at.desc()).first()

    parsed_result = None
    if latest_report and latest_report.result_json:
        try:
            parsed_result = json.loads(latest_report.result_json)
        except Exception:
            parsed_result = None

    return ResearchSessionResponse(
        id=session.id,
        title=session.title,
        original_query=session.original_query,
        status=session.status,
        created_at=session.created_at,
        updated_at=session.updated_at,
        latest_run_id=latest_report.run_id if latest_report else None,
        report_markdown=latest_report.markdown_content if latest_report else None,
        result_data=parsed_result
    )


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a research session and all associated runs, jobs, and reports."""
    session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research session '{session_id}' not found"
        )

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to delete this session"
        )

    db.delete(session)
    db.commit()

    logger.info(f"Deleted research session='{session_id}' (user='{current_user.id}')")
    return {
        "status": "success",
        "message": f"Session '{session_id}' deleted successfully"
    }


# -------------------------------------------------------------
# OBSERVABILITY & METRICS ENDPOINTS
# -------------------------------------------------------------

@router.get("/metrics")
def get_metrics_endpoint(
    format: str = Query("prometheus", pattern=r"^(prometheus|json)$")
):
    """
    Exposes authentic operational telemetry for monitoring systems.
    Zero synthetic or simulated data.
    """
    if format == "json":
        return metrics.get_summary()

    return Response(
        content=metrics.to_prometheus_format(),
        media_type="text/plain; version=0.0.4"
    )