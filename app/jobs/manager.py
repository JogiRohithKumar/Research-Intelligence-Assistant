"""
Background Job Execution Engine for Research Intelligence Assistant V2.
Manages asynchronous LangGraph execution outside the HTTP request lifecycle,
enforcing concurrency limits, idempotency deduplication, and safe cancellation.
"""

import hashlib
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def utc_now():
    return datetime.now(timezone.utc)

from app.core.config import get_settings
from app.core.correlation import set_job_context
from app.core.exceptions import AuthorizationError, ConflictError, ResourceNotFoundError
from app.core.logging import logger
from app.core.metrics import metrics
from app.db.base import SessionLocal
from app.db.models import (
    ReportModel,
    ResearchIterationModel,
    ResearchJob,
    ResearchRun,
    ResearchSession,
    User,
)
from app.graph.research_graph import research_graph
from app.jobs.events import job_event_bus

settings = get_settings()


class JobManager:
    """Thread-safe background research job orchestrator."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(
            max_workers=settings.MAX_CONCURRENT_RESEARCH_JOBS_GLOBAL,
            thread_name_prefix="research_worker"
        )
        self._cancellation_flags: Dict[str, bool] = {}
        self._active_jobs_lock = threading.Lock()

    def submit_job(
        self,
        query: str,
        user: User,
        session_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        sync: bool = False
    ) -> Dict[str, Any]:
        """
        Validates concurrency, enforces idempotency, enqueues background worker,
        and returns durable job metadata.
        """
        db = SessionLocal()
        try:
            # 1. Idempotency Check: return existing active job if key was previously submitted
            if idempotency_key:
                existing_key_job = db.query(ResearchJob).filter(
                    ResearchJob.user_id == user.id,
                    ResearchJob.idempotency_key == idempotency_key
                ).first()
                if existing_key_job:
                    logger.info(f"Duplicate request detected via idempotency key='{idempotency_key}', returning job='{existing_key_job.id}'")
                    return self._job_to_dict(existing_key_job)

            # 2. Concurrency Checks
            active_global = db.query(ResearchJob).filter(
                ResearchJob.status.in_(["QUEUED", "RUNNING"])
            ).count()
            if active_global >= settings.MAX_CONCURRENT_RESEARCH_JOBS_GLOBAL:
                raise ConflictError("Global concurrent research job limit reached. Please retry in a few moments.")

            active_user = db.query(ResearchJob).filter(
                ResearchJob.user_id == user.id,
                ResearchJob.status.in_(["QUEUED", "RUNNING"])
            ).count()
            if active_user >= settings.MAX_CONCURRENT_RESEARCH_JOBS_PER_USER:
                raise ConflictError("You have reached the maximum allowed concurrent active research jobs.")

            # 3. Duplicate active job check for exact same query
            duplicate_active = db.query(ResearchJob).filter(
                ResearchJob.user_id == user.id,
                ResearchJob.status.in_(["QUEUED", "RUNNING"])
            ).join(ResearchSession).filter(ResearchSession.original_query == query.strip()).first()
            if duplicate_active:
                logger.info(f"Existing active job '{duplicate_active.id}' found for query='{query}', returning it directly.")
                return self._job_to_dict(duplicate_active)

            # 4. Resolve or create ResearchSession
            if session_id:
                session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
                if session:
                    if session.user_id != user.id:
                        raise AuthorizationError("Access denied: You do not own this research session.")
                else:
                    session = ResearchSession(
                        id=session_id,
                        user_id=user.id,
                        title=query[:100],
                        original_query=query,
                        status="QUEUED"
                    )
                    db.add(session)
            else:
                query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()[:8]
                resolved_session_id = f"thread_{query_hash}_{int(time.time())}"
                session = ResearchSession(
                    id=resolved_session_id,
                    user_id=user.id,
                    title=query[:100],
                    original_query=query,
                    status="QUEUED"
                )
                db.add(session)

            # 5. Create ResearchJob record
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            job = ResearchJob(
                id=job_id,
                user_id=user.id,
                session_id=session.id,
                status="QUEUED",
                idempotency_key=idempotency_key,
                created_at=utc_now()
            )
            db.add(job)
            db.commit()
            db.refresh(job)

            metrics.record_job_lifecycle("QUEUED")
            logger.info(f"Created research job='{job_id}' for session='{session.id}', user='{user.id}'")

            # 6. Execute synchronously if requested, or dispatch to background thread pool
            if sync:
                return self._execute_worker(job_id, session.id, user.id, query)
            else:
                self._ensure_executor()
                self._executor.submit(self._execute_worker, job_id, session.id, user.id, query)
                return self._job_to_dict(job)

        finally:
            db.close()

    def _execute_worker(self, job_id: str, session_id: str, user_id: str, query: str) -> Dict[str, Any]:
        """Background thread execution worker for LangGraph research workflow."""
        start_time = time.time()
        set_job_context(job_id=job_id, session_id=session_id, user_id=user_id)
        db = SessionLocal()

        try:
            # Mark Job as RUNNING
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if job:
                job.status = "RUNNING"
                job.started_at = utc_now()
                db.commit()

            session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
            if session:
                session.status = "RUNNING"
                db.commit()

            metrics.record_job_lifecycle("RUNNING")
            job_event_bus.publish_sync(job_id, "research_started", {
                "session_id": session_id,
                "query": query,
                "timestamp": time.time()
            })

            # Check for cancellation before execution
            if self._is_cancelled(job_id):
                return self._handle_cancellation(job_id, session_id, db)

            # Construct initial state with user-partitioned checkpoint thread_id
            checkpoint_thread_id = f"usr_{user_id}:sess_{session_id}"
            config = {"configurable": {"thread_id": checkpoint_thread_id}}
            initial_state = {
                "query": query,
                "thread_id": session_id,
                "retry_count": 0,
                "execution_status": "in_progress",
                "supervisor": None,
                "search_plan": None,
                "papers": [],
                "retrieved_documents": [],
                "evidence_registry": [],
                "claims": [],
                "grounded_summary": "",
                "citation_verification": None,
                "grounding_status": "UNGROUNDED",
                "summaries": [],
                "citations": [],
                "verification": None,
                "gaps": None,
                "intelligence": None,
                "cross_paper_findings": [],
                "study_comparisons": [],
                "contradiction_findings": [],
                "evidence_strength": None,
                "research_gaps": [],
                "consensus_synthesis": None,
                "current_iteration": 1,
                "max_iterations": settings.MAX_RESEARCH_LOOP_ITERATIONS,
                "loop_state": None,
                "active_targeted_query": None,
                "sufficiency_evaluation": None,
                "actionable_gaps": [],
                "research_decision": None,
                "iterations_history": [],
                "report": "",
                "final_report": None,
                "agent_logs": [],
                "errors": []
            }

            # Execute graph
            result = research_graph.invoke(initial_state, config=config)

            # Check if cancelled during execution
            if self._is_cancelled(job_id):
                return self._handle_cancellation(job_id, session_id, db)

            # Execution successful: Persist durable results
            duration = round(time.time() - start_time, 2)
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            research_run = ResearchRun(
                id=run_id,
                session_id=session_id,
                user_id=user_id,
                iteration_count=result.get("current_iteration", 1),
                status="COMPLETED",
                grounding_status=result.get("grounding_status", "UNGROUNDED"),
                created_at=utc_now(),
                completed_at=utc_now()
            )
            db.add(research_run)

            # Persist iterations
            iterations = result.get("iterations_history") or []
            for it in iterations:
                it_record = ResearchIterationModel(
                    id=f"iter_{uuid.uuid4().hex[:12]}",
                    run_id=run_id,
                    iteration_number=it.get("iteration", 1),
                    query_used=it.get("query_used", query),
                    papers_count=it.get("new_papers_count", 0),
                    evidence_count=it.get("new_evidence_count", 0),
                    sufficiency_status=it.get("sufficiency_status"),
                    created_at=utc_now()
                )
                db.add(it_record)

            # Persist Report
            report_md = result.get("report") or result.get("grounded_summary") or ""
            evidence_strength = result.get("evidence_strength", {})
            rating = evidence_strength.get("rating") if isinstance(evidence_strength, dict) else str(evidence_strength)

            # Safely serialize result JSON for instantaneous reloading
            try:
                serializable_result = json.dumps(result, default=str)
            except Exception:
                serializable_result = None

            report = ReportModel(
                id=f"rep_{uuid.uuid4().hex[:12]}",
                session_id=session_id,
                user_id=user_id,
                run_id=run_id,
                markdown_content=report_md,
                evidence_strength=rating,
                claims_count=len(result.get("claims", [])),
                citations_count=len(result.get("citations", [])),
                result_json=serializable_result,
                created_at=utc_now()
            )
            db.add(report)

            # Update Job and Session status
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if job:
                job.run_id = run_id
                job.status = "COMPLETED"
                job.completed_at = utc_now()
                job.duration_seconds = duration
                job.progress_percent = 100

            session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
            if session:
                session.status = "COMPLETED"
                session.updated_at = utc_now()

            db.commit()

            metrics.record_job_lifecycle("COMPLETED", duration)
            job_event_bus.publish_sync(job_id, "research_completed", {
                "job_id": job_id,
                "session_id": session_id,
                "run_id": run_id,
                "duration_seconds": duration,
                "status": "COMPLETED",
                "claims_count": len(result.get("claims", [])),
                "citations_count": len(result.get("citations", []))
            })

            logger.info(f"Research job='{job_id}' completed successfully in {duration}s")
            return result

        except Exception as err:
            duration = round(time.time() - start_time, 2)
            logger.error(f"Research job='{job_id}' failed: {err}", exc_info=True)

            try:
                job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
                if job:
                    job.status = "FAILED"
                    job.completed_at = utc_now()
                    job.error_message = str(err)
                    job.error_code = "execution_error"
                    job.duration_seconds = duration

                session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
                if session:
                    session.status = "FAILED"
                    session.updated_at = utc_now()

                db.commit()
            except Exception as dberr:
                logger.error(f"Failed to persist job failure state to database: {dberr}")
                metrics.record_database_failure()

            metrics.record_job_lifecycle("FAILED", duration)
            job_event_bus.publish_sync(job_id, "research_failed", {
                "job_id": job_id,
                "session_id": session_id,
                "error": "Research execution encountered an unrecoverable failure",
                "error_code": "execution_error"
            })
            raise err

        finally:
            self._cancellation_flags.pop(job_id, None)
            db.close()

    def cancel_job(self, job_id: str, user: User) -> Dict[str, Any]:
        """Safely stops an active research job and persists cancellation state."""
        db = SessionLocal()
        try:
            job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
            if not job:
                raise ResourceNotFoundError(f"Research job '{job_id}' not found")
            if job.user_id != user.id:
                raise AuthorizationError("Access denied: You do not own this research job")

            if job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
                return {
                    "job_id": job_id,
                    "status": job.status,
                    "message": f"Job is already {job.status.lower()}"
                }

            # Set in-memory cancellation flag
            self._cancellation_flags[job_id] = True

            # Mark state
            job.status = "CANCELLED"
            job.completed_at = utc_now()

            session = db.query(ResearchSession).filter(ResearchSession.id == job.session_id).first()
            if session:
                session.status = "CANCELLED"
                session.updated_at = utc_now()

            db.commit()

            metrics.record_job_lifecycle("CANCELLED")
            job_event_bus.publish_sync(job_id, "research_cancelled", {
                "job_id": job_id,
                "message": "Research job was cancelled by user"
            })

            logger.info(f"Research job='{job_id}' successfully cancelled by user='{user.id}'")
            return {
                "job_id": job_id,
                "status": "CANCELLED",
                "message": "Research job successfully cancelled"
            }
        finally:
            db.close()

    def _is_cancelled(self, job_id: str) -> bool:
        return self._cancellation_flags.get(job_id, False)

    def _handle_cancellation(self, job_id: str, session_id: str, db) -> Dict[str, Any]:
        job = db.query(ResearchJob).filter(ResearchJob.id == job_id).first()
        if job:
            job.status = "CANCELLED"
            job.completed_at = utc_now()
        session = db.query(ResearchSession).filter(ResearchSession.id == session_id).first()
        if session:
            session.status = "CANCELLED"
        db.commit()
        return {"status": "CANCELLED", "job_id": job_id}

    def _job_to_dict(self, job: ResearchJob) -> Dict[str, Any]:
        return {
            "job_id": job.id,
            "session_id": job.session_id,
            "run_id": job.run_id,
            "status": job.status,
            "current_step": job.current_step,
            "progress_percent": job.progress_percent,
            "error_message": job.error_message,
            "error_code": job.error_code,
            "duration_seconds": job.duration_seconds,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at
        }

    def recover_stale_jobs(self) -> int:
        """
        Recovers orphaned jobs left in QUEUED or RUNNING state from a previous crash/restart.
        Marks them as FAILED to prevent persistent concurrency blocks.
        """
        db = SessionLocal()
        recovered_count = 0
        try:
            stale_jobs = db.query(ResearchJob).filter(
                ResearchJob.status.in_(["QUEUED", "RUNNING"])
            ).all()
            for job in stale_jobs:
                job.status = "FAILED"
                job.error_code = "PROCESS_INTERRUPTED"
                job.error_message = "Research job was interrupted by a server restart or process termination."
                job.completed_at = utc_now()
                recovered_count += 1
            if recovered_count > 0:
                db.commit()
                logger.warning(f"JobManager startup recovery: marked {recovered_count} orphaned job(s) as FAILED.")
        except Exception as exc:
            db.rollback()
            logger.error(f"Failed to recover stale jobs on startup: {exc}")
        finally:
            db.close()
        return recovered_count

    def shutdown(self, wait: bool = True) -> None:
        """Shuts down background worker thread pool gracefully."""
        self._executor.shutdown(wait=wait)

    def _ensure_executor(self) -> None:
        if getattr(self._executor, "_shutdown", False):
            self._executor = ThreadPoolExecutor(
                max_workers=settings.MAX_CONCURRENT_RESEARCH_JOBS_GLOBAL,
                thread_name_prefix="research_worker"
            )


# Global job manager singleton
job_manager = JobManager()
