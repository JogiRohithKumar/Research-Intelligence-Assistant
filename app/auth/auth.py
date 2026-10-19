"""
Authentication middleware for Research Intelligence Assistant V2.
Enforces API key validation when enabled, supporting seamless local development.
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from app.core.config import get_settings


def verify_api_key(
    x_api_key: Optional[str] = Header(None)
) -> bool:
    """
    Validates the incoming x-api-key header against allowed keys.
    If API_KEY_ENABLED is false, requests are permitted in development mode.
    """
    settings = get_settings()

    if not settings.API_KEY_ENABLED:
        return True

    if not x_api_key or x_api_key not in settings.ALLOWED_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )

    return True