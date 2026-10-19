"""
Database session dependency and transaction management for FastAPI routes.
"""

from typing import Generator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError
from app.core.logging import logger
from app.db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding an isolated database session per request.
    Ensures safe commit/rollback and automatic session cleanup.
    Only intercepts genuine database SQLAlchemy errors, preserving HTTP exceptions.
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Database session rollback triggered by SQLAlchemyError: {exc}")
        raise DatabaseError(f"Database operation failed: {str(exc)}") from exc
    finally:
        db.close()
