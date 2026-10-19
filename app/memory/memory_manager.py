"""
Session memory persistence manager for Research Intelligence Assistant V2.
Bridges in-memory execution state with durable database persistence.
"""

import json
from typing import Dict, Optional
from app.core.logging import logger
from app.db.base import SessionLocal
from app.db.models import ReportModel, ResearchSession

# Thread-safe in-memory cache for fast session retrieval
research_sessions: Dict[str, dict] = {}


def save_session(thread_id: str, state: dict) -> None:
    """Saves session state into in-memory store and updates durable database record."""
    research_sessions[thread_id] = state

    # Persist durable state to DB if thread_id is registered
    try:
        db = SessionLocal()
        try:
            session = db.query(ResearchSession).filter(ResearchSession.id == thread_id).first()
            if session:
                session.status = state.get("execution_status", session.status)
                db.commit()
        finally:
            db.close()
    except Exception as err:
        logger.debug(f"DB session sync skipped or failed for thread_id='{thread_id}': {err}")


def get_session(thread_id: str) -> Optional[dict]:
    """Retrieves session directly from in-memory cache."""
    return research_sessions.get(thread_id)


def delete_session(thread_id: str) -> None:
    """Removes session from in-memory cache."""
    research_sessions.pop(thread_id, None)


def load_session(thread_id: str) -> Optional[dict]:
    """Loads session state from memory cache, falling back to database serialization."""
    mem_data = get_session(thread_id)
    if mem_data:
        return mem_data

    # Fallback to database serialized result
    try:
        db = SessionLocal()
        try:
            latest_report = db.query(ReportModel).filter(
                ReportModel.session_id == thread_id
            ).order_by(ReportModel.created_at.desc()).first()
            if latest_report and latest_report.result_json:
                data = json.loads(latest_report.result_json)
                research_sessions[thread_id] = data
                return data
        finally:
            db.close()
    except Exception as err:
        logger.debug(f"DB session load skipped for thread_id='{thread_id}': {err}")

    return None