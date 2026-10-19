"""
SQLAlchemy Engine and Session Factory for Research Intelligence Assistant V2.
Supports PostgreSQL production pooling with explicit, safe SQLite fallback
only for local development and testing environments.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.logging import logger
from app.core.exceptions import DatabaseError, ConfigurationError
from app.db.models import Base

settings = get_settings()
settings.ensure_directories()


def create_db_engine():
    """
    Creates SQLAlchemy engine with connection pooling.
    In production: strictly enforces PostgreSQL connectivity and forbids silent SQLite downgrades.
    In development: gracefully falls back to local SQLite only when explicitly enabled.
    """
    curr_settings = get_settings()
    db_url = curr_settings.DATABASE_URL
    is_prod = curr_settings.is_production()

    # 1. PostgreSQL Database Dialect
    if "postgresql" in db_url.lower():
        try:
            engine = create_engine(
                db_url,
                pool_size=curr_settings.DATABASE_POOL_SIZE,
                max_overflow=curr_settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True
            )
            # Verify connectivity immediately
            with engine.connect() as conn:
                logger.info("Successfully connected to primary PostgreSQL database cluster.")
            return engine
        except Exception as err:
            if is_prod:
                logger.critical(f"FATAL: Production PostgreSQL connection to '{db_url}' failed: {err}")
                raise DatabaseError(
                    f"Production PostgreSQL connection to '{db_url}' failed. "
                    f"Silent fallback to SQLite is strictly forbidden in production: {err}"
                )
            if curr_settings.DATABASE_FALLBACK_SQLITE:
                sqlite_fallback_path = curr_settings.DATA_DIR / "research_prod.db"
                fallback_url = f"sqlite:///{sqlite_fallback_path}"
                logger.warning(
                    f"[DEV FALLBACK ONLY] PostgreSQL connection to '{db_url}' failed ({err}). "
                    f"Falling back to local SQLite storage at: {fallback_url}"
                )
                return create_engine(
                    fallback_url,
                    connect_args={"check_same_thread": False}
                )
            logger.error(f"PostgreSQL connection failed and fallback is disabled: {err}")
            raise DatabaseError(f"PostgreSQL connection failed: {err}")

    # 2. SQLite Database Dialect
    if "sqlite" in db_url.lower():
        if is_prod:
            raise ConfigurationError(
                "SQLite is strictly forbidden as production database. "
                "Configure a valid PostgreSQL DATABASE_URL."
            )
        logger.warning(f"[DEV ONLY] Initializing SQLAlchemy engine with SQLite at: {db_url}")
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )

    # 3. Unsupported Dialect
    raise ConfigurationError(f"Unsupported database scheme in DATABASE_URL: '{db_url}'")


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
get_engine = create_db_engine


def init_db():
    """Initializes tables idempotently."""
    Base.metadata.create_all(bind=engine)
