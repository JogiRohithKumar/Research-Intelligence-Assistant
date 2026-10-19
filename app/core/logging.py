"""
Standardized logging layer for Research Intelligence Assistant V2.
Provides structured logging, secret sanitization, and level control.
"""

import logging
import re
import sys
from typing import Any, Dict

# Patterns for potential secrets that must NEVER be emitted in logs
SECRET_PATTERNS = [
    re.compile(r"AIzaSy[A-Za-z0-9_-]{30,40}", re.IGNORECASE),
    re.compile(r"(['\"]?GEMINI_API_KEY['\"]?\s*[:=]\s*['\"]?)([^'\";\s]+)(['\"]?)", re.IGNORECASE),
    re.compile(r"(['\"]?x[-_]api[-_]key['\"]?\s*[:=]\s*['\"]?)([^'\";\s]+)(['\"]?)", re.IGNORECASE),
]


class SecretSanitizingFormatter(logging.Formatter):
    """Logging formatter that scrubs API keys and tokens and injects correlation metadata."""

    def format(self, record: logging.LogRecord) -> str:
        # Import lazily to avoid circular dependencies
        try:
            from app.core.correlation import get_correlation_context
            ctx = get_correlation_context()
            req_id = ctx.get("request_id") or "-"
            job_id = ctx.get("job_id") or "-"
            user_id = ctx.get("user_id") or "-"
            record.correlation = f"[req:{req_id} job:{job_id} user:{user_id}]"
        except Exception:
            record.correlation = "[-]"

        original = super().format(record)
        sanitized = original

        # Scrub AIzaSy keys
        sanitized = re.sub(r"AIzaSy[A-Za-z0-9_-]{30,40}", "***REDACTED***", sanitized, flags=re.IGNORECASE)
        # Scrub GEMINI_API_KEY values
        sanitized = re.sub(r"(['\"]?GEMINI_API_KEY['\"]?\s*[:=]\s*['\"]?)([^'\";\s]+)(['\"]?)", r"\1***REDACTED***\3", sanitized, flags=re.IGNORECASE)
        # Scrub x-api-key values
        sanitized = re.sub(r"(['\"]?x[-_]api[-_]key['\"]?\s*[:=]\s*['\"]?)([^'\";\s]+)(['\"]?)", r"\1***REDACTED***\3", sanitized, flags=re.IGNORECASE)

        return sanitized


def setup_logger(name: str = "research_assistant", level: str = "INFO") -> logging.Logger:
    """Configures and returns a sanitized application logger."""
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    formatter = SecretSanitizingFormatter(
        fmt="%(asctime)s [%(levelname)s] %(correlation)s [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger


# Default application logger instance
logger = setup_logger()
