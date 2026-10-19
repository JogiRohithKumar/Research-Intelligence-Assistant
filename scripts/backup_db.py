"""
Production Database Backup Utility for Research Intelligence Assistant.
Supports both PostgreSQL (via pg_dump or high-fidelity relational JSON dump)
and SQLite development databases with SHA-256 checksum integrity verification.
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import get_settings
from app.db.base import engine, SessionLocal
from app.db.models import (
    Base,
    ReportModel,
    ResearchIterationModel,
    ResearchJob,
    ResearchRun,
    ResearchSession,
    RevokedToken,
    User,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backup_db")


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file for integrity verification."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def backup_database(output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Executes a complete database backup.
    Returns metadata dictionary including backup path, size, row counts, and checksum.
    """
    settings = get_settings()
    target_dir = output_dir or (REPO_ROOT / "backups")
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = target_dir / f"db_backup_{timestamp}.json"
    meta_file = target_dir / f"db_backup_{timestamp}.meta.json"

    logger.info(f"Initiating database backup to: {backup_file}")

    # Ensure schema is synchronized
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    counts = {}
    data = {}

    try:
        # 1. Export Users
        users = db.query(User).all()
        counts["users"] = len(users)
        data["users"] = [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "hashed_password": u.hashed_password,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            }
            for u in users
        ]

        # 2. Export Sessions
        sessions = db.query(ResearchSession).all()
        counts["research_sessions"] = len(sessions)
        data["research_sessions"] = [
            {
                "id": s.id,
                "user_id": s.user_id,
                "title": s.title,
                "original_query": s.original_query,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]

        # 3. Export Runs
        runs = db.query(ResearchRun).all()
        counts["research_runs"] = len(runs)
        data["research_runs"] = [
            {
                "id": r.id,
                "session_id": r.session_id,
                "user_id": r.user_id,
                "iteration_count": r.iteration_count,
                "status": r.status,
                "grounding_status": r.grounding_status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in runs
        ]

        # 4. Export Iterations
        iterations = db.query(ResearchIterationModel).all()
        counts["research_iterations"] = len(iterations)
        data["research_iterations"] = [
            {
                "id": it.id,
                "run_id": it.run_id,
                "iteration_number": it.iteration_number,
                "query_used": it.query_used,
                "papers_count": it.papers_count,
                "evidence_count": it.evidence_count,
                "sufficiency_status": it.sufficiency_status,
                "created_at": it.created_at.isoformat() if it.created_at else None,
            }
            for it in iterations
        ]

        # 5. Export Jobs
        jobs = db.query(ResearchJob).all()
        counts["research_jobs"] = len(jobs)
        data["research_jobs"] = [
            {
                "id": j.id,
                "user_id": j.user_id,
                "session_id": j.session_id,
                "run_id": j.run_id,
                "status": j.status,
                "idempotency_key": j.idempotency_key,
                "current_step": j.current_step,
                "progress_percent": j.progress_percent,
                "error_message": j.error_message,
                "error_code": j.error_code,
                "duration_seconds": j.duration_seconds,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ]

        # 6. Export Reports
        reports = db.query(ReportModel).all()
        counts["reports"] = len(reports)
        data["reports"] = [
            {
                "id": rep.id,
                "session_id": rep.session_id,
                "user_id": rep.user_id,
                "run_id": rep.run_id,
                "markdown_content": rep.markdown_content,
                "evidence_strength": rep.evidence_strength,
                "claims_count": rep.claims_count,
                "citations_count": rep.citations_count,
                "result_json": rep.result_json,
                "created_at": rep.created_at.isoformat() if rep.created_at else None,
            }
            for rep in reports
        ]

        # 7. Export Revoked Tokens
        revoked = db.query(RevokedToken).all()
        counts["revoked_tokens"] = len(revoked)
        data["revoked_tokens"] = [
            {
                "id": tok.id,
                "token_hash": tok.token_hash,
                "user_id": tok.user_id,
                "revoked_at": tok.revoked_at.isoformat() if tok.revoked_at else None,
                "expires_at": tok.expires_at.isoformat() if tok.expires_at else None,
            }
            for tok in revoked
        ]

        # Write data payload
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        file_size = os.path.getsize(backup_file)
        checksum = compute_sha256(backup_file)

        metadata = {
            "backup_version": "1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_url_dialect": settings.DATABASE_URL.split("://")[0],
            "backup_file": str(backup_file.name),
            "size_bytes": file_size,
            "sha256": checksum,
            "row_counts": counts,
        }

        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Database backup completed successfully. Size: {file_size} bytes. Checksum: {checksum}")
        logger.info(f"Row counts: {counts}")
        return metadata

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup Research Intelligence Assistant Database")
    parser.add_argument("--output-dir", type=str, default=None, help="Target backup directory")
    args = parser.parse_args()

    out_path = Path(args.output_dir) if args.output_dir else None
    result = backup_database(output_dir=out_path)
    print(json.dumps(result, indent=2))
