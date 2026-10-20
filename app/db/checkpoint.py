"""
Persistence Checkpoint Layer for Research Intelligence Assistant V2.
Manages LangGraph checkpointer with strict PostgreSQL persistence in production
and explicit, safe SQLite fallback only in local development/testing.
"""

import sqlite3
from typing import Optional
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.config import get_settings
from app.core.logging import logger
from app.core.exceptions import DatabaseError, ConfigurationError

settings = get_settings()
settings.ensure_directories()

_pool: Optional[ConnectionPool] = None


def get_checkpointer() -> BaseCheckpointSaver:
    """
    Initializes and returns the authoritative LangGraph checkpoint saver.
    In production: strictly requires PostgreSQL (via PostgresSaver) and executes migrations.
    In development: gracefully falls back to SqliteSaver only when explicitly enabled.
    """
    global _pool
    curr_settings = get_settings()
    db_url = curr_settings.DATABASE_URL
    is_prod = curr_settings.is_production()

    # 1. PostgreSQL Checkpoint Backend
    if "postgresql" in db_url.lower():
        try:
            # Normalize SQLAlchemy connection string to standard psycopg3 URI
            psycopg_uri = (
                db_url
                .replace("postgresql+psycopg2://", "postgresql://")
                .replace("postgresql+asyncpg://", "postgresql://")
            )

            if _pool is None or _pool.closed:
                _pool = ConnectionPool(
                conninfo=psycopg_uri,
                min_size=1,
                max_size=settings.DATABASE_POOL_SIZE,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                },
                open=True
            )

            saver = PostgresSaver(_pool)
            # Execute versioned internal migrations for checkpoints tables
            saver.setup()
            logger.info("LangGraph checkpointer successfully initialized with PostgreSQL (PostgresSaver).")
            return saver
        except Exception as err:
            if is_prod:
                logger.critical(f"FATAL: Production LangGraph PostgreSQL checkpointer failed to connect: {err}")
                raise DatabaseError(
                    f"Production LangGraph PostgreSQL checkpointer failed to connect to '{db_url}'. "
                    f"Silent fallback to SQLite is strictly forbidden in production: {err}"
                )
            if settings.DATABASE_FALLBACK_SQLITE:
                logger.warning(
                    f"[DEV FALLBACK ONLY] PostgreSQL checkpointer connection failed ({err}). "
                    f"Falling back to local SQLite checkpointer at: {settings.SQLITE_DB_PATH}"
                )
                conn = sqlite3.connect(str(settings.SQLITE_DB_PATH), check_same_thread=False)
                return SqliteSaver(conn)
            raise DatabaseError(f"PostgreSQL checkpointer connection failed: {err}")

    # 2. Explicit SQLite Checkpoint Backend
    if "sqlite" in db_url.lower():
        if is_prod:
            raise ConfigurationError(
                "SQLite is strictly forbidden as production checkpointer backend. "
                "Configure a valid PostgreSQL DATABASE_URL."
            )
        logger.warning(f"[DEV ONLY] Initializing LangGraph checkpointer with SQLite at: {settings.SQLITE_DB_PATH}")
        conn = sqlite3.connect(str(settings.SQLITE_DB_PATH), check_same_thread=False)
        return SqliteSaver(conn)

    # 3. Unsupported Dialect
    raise ConfigurationError(f"Unsupported database scheme for checkpointer in: '{db_url}'")


# Canonical checkpointer instance for graph compilation
checkpointer: BaseCheckpointSaver = get_checkpointer()