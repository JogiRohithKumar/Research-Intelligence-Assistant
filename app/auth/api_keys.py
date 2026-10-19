"""
API Key configuration layer for Research Intelligence Assistant V2.
Loads valid keys dynamically from centralized environment settings.
"""

from app.core.config import get_settings


def get_valid_api_keys() -> list[str]:
    """Returns the list of authorized API keys from environment settings."""
    settings = get_settings()
    return settings.ALLOWED_API_KEYS


# Backwards compatibility alias
VALID_API_KEYS = get_valid_api_keys()