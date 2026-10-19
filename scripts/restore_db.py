"""
Production Database Restore Utility for Research Intelligence Assistant.
Verifies SHA-256 checksum integrity and restores application state transactionally.
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db.base import Base, engine, SessionLocal
from app.db.models import (
    ReportModel,
    ResearchIterationModel,
    ResearchJob,
    ResearchRun,
    ResearchSession,
    RevokedToken,
    User,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("restore_db")


def compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file for integrity verification."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def restore_database(backup_file: Path, verify_checksum: bool = True) -> Dict[str, Any]:
    """
    Restores database state from a verified backup JSON file.
    Executes in a single atomic transaction.
    """
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    # Check for metadata file
    meta_path = backup_file.parent / f"{backup_file.stem}.meta.json"
    if verify_checksum and meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        expected_hash = meta.get("sha256")
        actual_hash = compute_sha256(backup_file)
        if expected_hash and actual_hash != expected_hash:
            raise ValueError(
                f"Checksum mismatch! Expected: {expected_hash}, Actual: {actual_hash}. "
                f"Backup file may be corrupted or tampered with."
            )
        logger.info(f"Backup integrity verified via SHA-256: {actual_hash}")

    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    restored_counts = {}

    try:
        # 1. Restore Users
        user_records = data.get("users", [])
        for u in user_records:
            existing = db.query(User).filter(User.id == u["id"]).first()
            if not existing:
                db.add(User(
                    id=u["id"],
                    email=u["email"],
                    username=u["username"],
                    hashed_password=u["hashed_password"],
                    is_active=u["is_active"],
                    created_at=parse_dt(u["created_at"]),
                    updated_at=parse_dt(u["updated_at"])
                ))
        restored_counts["users"] = len(user_records)

        # 2. Restore Sessions
        session_records = data.get("research_sessions", [])
        for s in session_records:
            existing = db.query(ResearchSession).filter(ResearchSession.id == s["id"]).first()
            if not existing:
                db.add(ResearchSession(
                    id=s["id"],
                    user_id=s["user_id"],
                    title=s["title"],
                    original_query=s["original_query"],
                    status=s["status"],
                    created_at=parse_dt(s["created_at"]),
                    updated_at=parse_dt(s["updated_at"])
                ))
        restored_counts["research_sessions"] = len(session_records)

        # 3. Restore Runs
        run_records = data.get("research_runs", [])
        for r in run_records:
            existing = db.query(ResearchRun).filter(ResearchRun.id == r["id"]).first()
            if not existing:
                db.add(ResearchRun(
                    id=r["id"],
                    session_id=r["session_id"],
                    user_id=r["user_id"],
                    iteration_count=r["iteration_count"],
                    status=r["status"],
                    grounding_status=r["grounding_status"],
                    created_at=parse_dt(r["created_at"]),
                    completed_at=parse_dt(r["completed_at"])
                ))
        restored_counts["research_runs"] = len(run_records)

        # 4. Restore Iterations
        it_records = data.get("research_iterations", [])
        for it in it_records:
            existing = db.query(ResearchIterationModel).filter(ResearchIterationModel.id == it["id"]).first()
            if not existing:
                db.add(ResearchIterationModel(
                    id=it["id"],
                    run_id=it["run_id"],
                    iteration_number=it["iteration_number"],
                    query_used=it["query_used"],
                    papers_count=it["papers_count"],
                    evidence_count=it["evidence_count"],
                    sufficiency_status=it.get("sufficiency_status"),
                    created_at=parse_dt(it["created_at"])
                ))
        restored_counts["research_iterations"] = len(it_records)

        # 5. Restore Jobs
        job_records = data.get("research_jobs", [])
        for j in job_records:
            existing = db.query(ResearchJob).filter(ResearchJob.id == j["id"]).first()
            if not existing:
                db.add(ResearchJob(
                    id=j["id"],
                    user_id=j["user_id"],
                    session_id=j["session_id"],
                    run_id=j.get("run_id"),
                    status=j["status"],
                    idempotency_key=j.get("idempotency_key"),
                    current_step=j.get("current_step"),
                    progress_percent=j.get("progress_percent"),
                    error_message=j.get("error_message"),
                    error_code=j.get("error_code"),
                    duration_seconds=j.get("duration_seconds"),
                    created_at=parse_dt(j["created_at"]),
                    started_at=parse_dt(j.get("started_at")),
                    completed_at=parse_dt(j.get("completed_at"))
                ))
        restored_counts["research_jobs"] = len(job_records)

        # 6. Restore Reports
        rep_records = data.get("reports", [])
        for rep in rep_records:
            existing = db.query(ReportModel).filter(ReportModel.id == rep["id"]).first()
            if not existing:
                db.add(ReportModel(
                    id=rep["id"],
                    session_id=rep["session_id"],
                    user_id=rep["user_id"],
                    run_id=rep.get("run_id"),
                    markdown_content=rep["markdown_content"],
                    evidence_strength=rep.get("evidence_strength"),
                    claims_count=rep.get("claims_count", 0),
                    citations_count=rep.get("citations_count", 0),
                    result_json=rep.get("result_json"),
                    created_at=parse_dt(rep["created_at"])
                ))
        restored_counts["reports"] = len(rep_records)

        # 7. Restore Revoked Tokens
        tok_records = data.get("revoked_tokens", [])
        for tok in tok_records:
            existing = db.query(RevokedToken).filter(RevokedToken.token_hash == tok["token_hash"]).first()
            if not existing:
                db.add(RevokedToken(
                    token_hash=tok["token_hash"],
                    user_id=tok.get("user_id"),
                    revoked_at=parse_dt(tok["revoked_at"]),
                    expires_at=parse_dt(tok.get("expires_at"))
                ))
        restored_counts["revoked_tokens"] = len(tok_records)

        db.commit()
        logger.info(f"Database successfully restored from {backup_file.name}")
        logger.info(f"Restored counts: {restored_counts}")
        return restored_counts

    except Exception as exc:
        db.rollback()
        logger.error(f"Restore failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore Research Intelligence Assistant Database")
    parser.add_argument("backup_file", type=str, help="Path to backup JSON file")
    parser.add_argument("--no-verify", action="store_true", help="Skip SHA-256 checksum verification")
    args = parser.parse_args()

    result = restore_database(Path(args.backup_file), verify_checksum=not args.no_verify)
    print(json.dumps(result, indent=2))
