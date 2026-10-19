"""
API Schemas for Research Intelligence Assistant V2.
Includes strict input validation limits against resource exhaustion attacks and type safety.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# -------------------------------------------------------------
# AUTHENTICATION SCHEMAS
# -------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\-]+$")
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=6, max_length=128)


class UserLoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserResponse


# -------------------------------------------------------------
# RESEARCH & SESSION SCHEMAS
# -------------------------------------------------------------

class ResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="Research query or scientific question (max 1000 characters)"
    )
    session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9_\-]+$",
        description="Optional alphanumeric session identifier"
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional client-generated deduplication idempotency key"
    )
    sync: Optional[bool] = Field(
        default=False,
        description="Execute synchronously (blocking until completion) for offline scripts and testing"
    )


class ResearchJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    session_id: str
    run_id: Optional[str] = None
    status: str
    current_step: Optional[str] = None
    progress_percent: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobCancelResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ResearchSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_query: str
    status: str
    created_at: datetime
    updated_at: datetime
    latest_run_id: Optional[str] = None
    report_markdown: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


class ResearchSessionListResponse(BaseModel):
    sessions: List[ResearchSessionResponse]
    total: int