"""
Domain exceptions for Research Intelligence Assistant V2.
Provides structured, predictable error hierarchy with status codes and machine-readable error codes.
"""

from typing import Any, Dict, Optional


class ResearchAssistantError(Exception):
    """Base exception for all domain errors."""
    error_code: str = "internal_error"
    status_code: int = 400

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code


class ConfigurationError(ResearchAssistantError):
    """Raised when environment or runtime settings are invalid."""
    error_code = "configuration_error"
    status_code = 500


class AuthenticationError(ResearchAssistantError):
    """Raised when authentication credentials are missing, invalid, or expired."""
    error_code = "authentication_error"
    status_code = 401


class AuthorizationError(ResearchAssistantError):
    """Raised when an authenticated user attempts to access or mutate another tenant's resource."""
    error_code = "authorization_error"
    status_code = 403


class ResourceNotFoundError(ResearchAssistantError):
    """Raised when a requested resource does not exist or user is unauthorized to view it."""
    error_code = "not_found"
    status_code = 404


class ConflictError(ResearchAssistantError):
    """Raised when an entity or active job already exists or concurrency is exceeded."""
    error_code = "conflict"
    status_code = 409


class RateLimitError(ResearchAssistantError):
    """Raised when request frequency exceeds server limits."""
    error_code = "rate_limit_error"
    status_code = 429


class DatabaseError(ResearchAssistantError):
    """Raised when database operations encounter persistence or connectivity failures."""
    error_code = "database_error"
    status_code = 500


class ProviderError(ResearchAssistantError):
    """Raised when an external scholarly provider or service fails."""
    error_code = "provider_error"
    status_code = 502


class ResearchTimeoutError(ResearchAssistantError):
    """Raised when research execution exceeds the configured duration threshold."""
    error_code = "research_timeout"
    status_code = 504


class JobError(ResearchAssistantError):
    """Raised when a research background job encounters an invalid state transition or execution failure."""
    error_code = "job_error"
    status_code = 400


class LLMGenerationError(ResearchAssistantError):
    """Raised when an LLM API call fails or encounters an upstream error."""
    error_code = "llm_generation_error"
    status_code = 502


class LLMValidationError(ResearchAssistantError):
    """Raised when an LLM output fails schema validation after retries."""
    error_code = "validation_error"
    status_code = 422


class SearchRetrievalError(ResearchAssistantError):
    """Raised when an external academic search provider fails."""
    error_code = "provider_error"
    status_code = 502


class GraphExecutionError(ResearchAssistantError):
    """Raised when LangGraph execution encounters a terminal state failure."""
    error_code = "graph_execution_error"
    status_code = 500
