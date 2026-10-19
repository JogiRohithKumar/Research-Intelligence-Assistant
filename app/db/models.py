"""
Relational Database Models for Research Intelligence Assistant V2.
Defines durable application state schemas separated from transient LangGraph execution buffers.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    """Generates timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account entity for authentication and multi-tenant isolation."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Multi-tenant relationships
    sessions = relationship("ResearchSession", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("ResearchJob", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("ReportModel", back_populates="user", cascade="all, delete-orphan")


class ResearchSession(Base):
    """Durable server-side research session authoritative over client state."""
    __tablename__ = "research_sessions"

    id = Column(String(128), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(500), nullable=False)
    original_query = Column(Text, nullable=False)
    status = Column(String(50), default="IDLE", index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="sessions")
    runs = relationship("ResearchRun", back_populates="session", cascade="all, delete-orphan")
    jobs = relationship("ResearchJob", back_populates="session", cascade="all, delete-orphan")
    reports = relationship("ReportModel", back_populates="session", cascade="all, delete-orphan")

    @property
    def session_id(self) -> str:
        return self.id


class ResearchRun(Base):
    """Individual execution execution run associated with a research session."""
    __tablename__ = "research_runs"

    id = Column(String(128), primary_key=True)
    session_id = Column(String(128), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    iteration_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="RUNNING", index=True, nullable=False)
    grounding_status = Column(String(50), default="UNGROUNDED", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    session = relationship("ResearchSession", back_populates="runs")
    iterations = relationship("ResearchIterationModel", back_populates="run", cascade="all, delete-orphan")
    reports = relationship("ReportModel", back_populates="run", cascade="all, delete-orphan")


class ResearchIterationModel(Base):
    """Individual agentic loop iteration trace record."""
    __tablename__ = "research_iterations"

    id = Column(String(128), primary_key=True)
    run_id = Column(String(128), ForeignKey("research_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    iteration_number = Column(Integer, nullable=False)
    query_used = Column(Text, nullable=False)
    papers_count = Column(Integer, default=0, nullable=False)
    evidence_count = Column(Integer, default=0, nullable=False)
    sufficiency_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    run = relationship("ResearchRun", back_populates="iterations")


class ResearchJob(Base):
    """Asynchronous background execution job model with explicit lifecycle states."""
    __tablename__ = "research_jobs"

    id = Column(String(128), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id = Column(String(128), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    run_id = Column(String(128), ForeignKey("research_runs.id", ondelete="SET NULL"), index=True, nullable=True)
    status = Column(String(50), default="QUEUED", index=True, nullable=False)
    idempotency_key = Column(String(128), index=True, nullable=True)
    current_step = Column(String(100), nullable=True)
    progress_percent = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="jobs")
    session = relationship("ResearchSession", back_populates="jobs")

    @property
    def job_id(self) -> str:
        return self.id


class ReportModel(Base):
    """Persisted scholarly brief and serialized research output."""
    __tablename__ = "reports"

    id = Column(String(128), primary_key=True)
    session_id = Column(String(128), ForeignKey("research_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    run_id = Column(String(128), ForeignKey("research_runs.id", ondelete="CASCADE"), index=True, nullable=True)
    markdown_content = Column(Text, nullable=False)
    evidence_strength = Column(String(50), nullable=True)
    claims_count = Column(Integer, default=0, nullable=False)
    citations_count = Column(Integer, default=0, nullable=False)
    result_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    session = relationship("ResearchSession", back_populates="reports")
    run = relationship("ResearchRun", back_populates="reports")
    user = relationship("User", back_populates="reports")


class RevokedToken(Base):
    """
    Durable server-side token revocation record for multi-instance production safety.
    Stores cryptographic SHA-256 hashes of invalidated tokens so revocation survives restarts and across nodes.
    """
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(String(36), index=True, nullable=True)
    revoked_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=True)
