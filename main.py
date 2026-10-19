"""
FastAPI Application Entrypoint for Research Intelligence Assistant V2.
Engineered for production resilience, multi-tenant isolation, structured logging,
correlation tracing, rate limiting, and secure HTTP headers.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.routes import router as research_router
from app.api.stream import router as stream_router
from app.auth.routes import router as auth_router
from app.core.config import get_settings
from app.core.correlation import get_request_id, set_request_id
from app.core.exceptions import ResearchAssistantError
from app.core.logging import logger
from app.core.metrics import metrics
from app.core.rate_limiter import limiter
from app.db.base import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database initialization and resource setup."""
    logger.info("Initializing Research Intelligence Assistant production engine...")
    try:
        init_db()
        logger.info("Relational database schema verified.")
        from app.jobs.manager import job_manager
        recovered = job_manager.recover_stale_jobs()
        if recovered > 0:
            logger.info(f"Startup recovery: cleaned {recovered} stale research jobs.")
    except Exception as err:
        logger.error(f"Failed to initialize database tables or recover jobs: {err}")
    yield
    logger.info("Shutting down Research Intelligence Assistant...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Attach rate limiter to app state
app.state.limiter = limiter


# -------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------

@app.middleware("http")
async def correlation_and_metrics_middleware(request: Request, call_next):
    """
    Propagates correlation ID, enforces payload size limits,
    records execution latency, and injects telemetry headers.
    """
    # 1. Resolve or generate Request ID
    req_id = request.headers.get("X-Request-ID")
    resolved_id = set_request_id(req_id)

    # 2. Enforce maximum request payload size
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content={
                "error": {
                    "type": "payload_too_large",
                    "message": f"Request body exceeds maximum allowed size of {settings.MAX_REQUEST_BODY_BYTES} bytes",
                    "request_id": resolved_id
                }
            }
        )

    start_time = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record genuine observability metrics
        metrics.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration
        )

        response.headers["X-Request-ID"] = resolved_id
        return response
    except Exception as exc:
        duration = time.time() - start_time
        metrics.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=500,
            duration_seconds=duration
        )
        raise exc


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adds hardened production security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.is_production():
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# CORS Middleware with explicit restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "x-api-key",
        "Authorization",
        "X-Request-ID",
        "Idempotency-Key",
        "Last-Event-ID",
        "Accept"
    ],
)


# -------------------------------------------------------------
# EXCEPTION HANDLERS
# -------------------------------------------------------------

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Structured handler for throttled requests."""
    req_id = get_request_id()
    logger.warning(f"Rate limit exceeded on {request.url.path} (request_id={req_id})")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": {
                "type": "rate_limit_error",
                "message": "Too many requests. Please slow down and try again later.",
                "request_id": req_id
            }
        }
    )


@app.exception_handler(ResearchAssistantError)
async def domain_exception_handler(request: Request, exc: ResearchAssistantError):
    """Uniform handler for domain-specific errors with sanitized output."""
    req_id = get_request_id()
    logger.error(f"Domain error [{exc.error_code}] on {request.url.path}: {exc.message} (request_id={req_id})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "request_id": req_id
            }
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Uniform handler for standard HTTP exceptions."""
    req_id = get_request_id()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "message": exc.detail,
                "request_id": req_id
            }
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catches unhandled errors without exposing Python tracebacks to clients."""
    req_id = get_request_id()
    logger.error(f"Unhandled server error on {request.url.path} (request_id={req_id}): {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "type": "internal_error",
                "message": "An internal server error occurred. Please contact support with the request ID.",
                "request_id": req_id
            }
        }
    )


# -------------------------------------------------------------
# CORE ENDPOINTS & ROUTERS
# -------------------------------------------------------------

@app.get("/health/liveness")
def liveness_probe():
    """Kubernetes / Container liveness probe: verifies web server process is responsive."""
    return {
        "status": "alive",
        "app": settings.APP_NAME,
        "timestamp": time.time()
    }


@app.get("/health/readiness")
def readiness_probe():
    """
    Kubernetes / Container readiness probe:
    Rigorously verifies backend dependency availability (database engine connectivity).
    Returns 503 if primary database connection cannot be verified.
    """
    from sqlalchemy import text
    from app.db.base import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database": "connected",
            "workers": "ready"
        }
    except Exception as exc:
        logger.error(f"Readiness probe failed on database connection: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "app": settings.APP_NAME,
                "error": "Primary database dependency is currently unreachable"
            }
        )


@app.get("/health")
def health_check():
    """Health check endpoint for container and deployment monitors."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENV,
        "database": "configured"
    }


# Mount Routers
app.include_router(auth_router)
app.include_router(research_router)
app.include_router(stream_router)