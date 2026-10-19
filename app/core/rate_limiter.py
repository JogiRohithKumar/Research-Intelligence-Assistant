"""
Server-side rate limiting configuration for Research Intelligence Assistant V2.
Uses slowapi with user-aware and IP-aware key resolution.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings


def rate_limit_key_func(request: Request) -> str:
    """
    User-aware rate limit key resolver.
    Prefers authenticated user ID if available, falling back to client IP address.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Also check Authorization header token preview or client IP
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        # Hash or truncate token for rate limit bucket key without logging token
        return f"token:{hash(token)}"

    return get_remote_address(request) or "127.0.0.1"


settings = get_settings()

limiter = Limiter(
    key_func=rate_limit_key_func,
    default_limits=[settings.RATE_LIMIT_DEFAULT] if settings.RATE_LIMIT_ENABLED else [],
    enabled=settings.RATE_LIMIT_ENABLED
)
