"""
Centralized Configuration Layer for Research Intelligence Assistant V2.
Uses Pydantic BaseSettings for strict environment variable parsing and validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the repository (where main.py resides)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Research Intelligence Assistant V2"
    APP_VERSION: str = "2.0.0-dev"
    ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # LLM Settings (Google Gemini)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_FAST_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 4096

    # Storage Paths (resolved absolutely from BASE_DIR)
    DATA_DIR: Path = Field(default_factory=lambda: BASE_DIR / "app" / "db")
    SQLITE_DB_PATH: Path = Field(default_factory=lambda: BASE_DIR / "app" / "db" / "research.db")
    CHROMA_PERSIST_DIRECTORY: Path = Field(default_factory=lambda: BASE_DIR / "app" / "db" / "chroma")
    CHROMA_COLLECTION_NAME: str = "research_papers_v2"

    # Database & Persistence (Stage 7 Production Persistence)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/research_assistant"
    DATABASE_FALLBACK_SQLITE: bool = True
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Security & Authentication (Stage 7)
    AUTH_ENABLED: bool = True
    JWT_SECRET_KEY: str = "production-engineering-secret-key-must-be-rotated-via-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    API_KEY_ENABLED: bool = False
    ALLOWED_API_KEYS: List[str] = Field(default_factory=list)

    # Rate Limiting & Resource Protection (Stage 7)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_RESEARCH: str = "5/minute"
    RATE_LIMIT_STATUS: str = "60/minute"
    MAX_CONCURRENT_RESEARCH_JOBS_PER_USER: int = 2
    MAX_CONCURRENT_RESEARCH_JOBS_GLOBAL: int = 10
    MAX_RESEARCH_TIMEOUT_SECONDS: int = 300
    MAX_REQUEST_BODY_BYTES: int = 1024 * 1024  # 1MB limit

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    CORS_ORIGIN_REGEX: Optional[str] = r"https://multi-agent-research-assistant-.*\.vercel\.app"

    # Search & Retrieval Configuration (Stage 2)
    MAX_SEARCH_VARIANTS: int = 3
    MAX_RESULTS_PER_PROVIDER: int = 15
    MAX_TOTAL_CANDIDATES: int = 30
    MAX_FINAL_RETRIEVAL_PAPERS: int = 5
    SEARCH_TIMEOUT_SECONDS: int = 25
    RETRIEVAL_TOP_K: int = 5
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    DEFAULT_SEARCH_MAX_RESULTS: int = 15
    DEFAULT_TOP_PAPERS_COUNT: int = 5

    # Evidence Grounding Configuration (Stage 3)
    MAX_EVIDENCE_CHUNKS: int = 10
    MIN_EVIDENCE_SIMILARITY: float = 0.20
    MAX_CONTEXT_TOKENS: int = 3500
    ENFORCE_CITATION_VERIFICATION: bool = True

    # Agentic Research Loop Configuration (Stage 5)
    ENABLE_AGENTIC_LOOP: bool = True
    MAX_RESEARCH_LOOP_ITERATIONS: int = 3
    MAX_SEARCHES_PER_ITERATION: int = 2
    MAX_CUMULATIVE_PAPERS: int = 20
    MAX_CUMULATIVE_EVIDENCE_CHUNKS: int = 25
    MAX_RESEARCH_BUDGET_CALLS: int = 10

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        """Enforces that production configurations cannot run with insecure development defaults."""
        if self.is_production():
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production environment.")
            if "sqlite" in self.DATABASE_URL.lower():
                raise ValueError("Production environment requires PostgreSQL; SQLite DATABASE_URL is strictly forbidden in production.")
            if self.DATABASE_FALLBACK_SQLITE:
                raise ValueError("DATABASE_FALLBACK_SQLITE must be False in production environment to prevent silent degradation.")
            if self.JWT_SECRET_KEY == "production-engineering-secret-key-must-be-rotated-via-env" or len(self.JWT_SECRET_KEY) < 32:
                raise ValueError("Insecure or default JWT_SECRET_KEY in production. Must be explicitly supplied via environment and at least 32 characters.")
            if not self.AUTH_ENABLED:
                raise ValueError("AUTH_ENABLED cannot be False in production.")
        return self

    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    def ensure_directories(self) -> None:
        """Ensure runtime storage directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_PERSIST_DIRECTORY.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
