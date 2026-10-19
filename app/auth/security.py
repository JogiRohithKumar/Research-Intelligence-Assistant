"""
Cryptographic security and JWT token handling for Research Intelligence Assistant V2.
Never exposes plaintext passwords, secrets, or insecure algorithm fallbacks.
Enforces minimum secret strength, explicit algorithm restriction, and server-side token revocation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

import hashlib
import logging

logger = logging.getLogger("research_assistant")
settings = get_settings()

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# L1 Fast in-memory cache for revoked tokens and hashes
_revoked_tokens: Set[str] = set()
_revoked_token_hashes: Set[str] = set()


def _hash_token(token: str) -> str:
    """Computes fixed-length SHA-256 hash for secure indexed database storage."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def revoke_token(token: str, user_id: Optional[str] = None) -> None:
    """
    Registers a JWT token in the durable revocation blocklist.
    Updates both local L1 memory cache and persistent PostgreSQL database table.
    """
    if not token or not token.strip():
        return

    clean_token = token.strip()
    token_hash = _hash_token(clean_token)

    # 1. Update L1 In-Memory Cache
    _revoked_tokens.add(clean_token)
    _revoked_token_hashes.add(token_hash)

    # 2. Persist to Durable Storage (PostgreSQL / SQLite)
    try:
        from app.db.base import SessionLocal
        from app.db.models import RevokedToken

        with SessionLocal() as db:
            existing = db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
            if not existing:
                revoked_record = RevokedToken(
                    token_hash=token_hash,
                    user_id=user_id,
                    revoked_at=datetime.now(timezone.utc)
                )
                db.add(revoked_record)
                db.commit()
    except Exception as exc:
        logger.warning(f"Could not persist revoked token to database: {exc}")


def is_token_revoked(token: str) -> bool:
    """
    Checks whether a token has been explicitly revoked upon logout.
    Queries L1 memory cache first, falling back to durable database verification.
    """
    if not token or not token.strip():
        return False

    clean_token = token.strip()
    token_hash = _hash_token(clean_token)

    # 1. Check L1 In-Memory Cache
    if clean_token in _revoked_tokens or token_hash in _revoked_token_hashes:
        return True

    # 2. Check L2 Persistent Storage
    try:
        from app.db.base import SessionLocal
        from app.db.models import RevokedToken

        with SessionLocal() as db:
            record = db.query(RevokedToken).filter(RevokedToken.token_hash == token_hash).first()
            if record:
                _revoked_tokens.add(clean_token)
                _revoked_token_hashes.add(token_hash)
                return True
    except Exception as exc:
        logger.debug(f"Database check for token revocation unavailable: {exc}")

    return False


def hash_password(password: str) -> str:
    """Hashes a plaintext password using modern cryptographic derivation."""
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against its stored cryptographic hash."""
    if not plain_password or not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a securely signed JWT access token with strict claims and secret strength enforcement."""
    secret = settings.JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        raise ValueError("Insecure JWT_SECRET_KEY: server secret must be at least 32 characters long.")

    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "iss": "research-intelligence-assistant"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        secret,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and rigorously validates a JWT access token.
    Enforces expiration, signature integrity, revocation status, and algorithm restrictions.
    """
    if is_token_revoked(token):
        raise AuthenticationError("Authentication token has been revoked upon logout. Please log in again.")

    secret = settings.JWT_SECRET_KEY
    if not secret or len(secret) < 32:
        raise ValueError("Insecure JWT_SECRET_KEY: server secret must be at least 32 characters long.")

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="research-intelligence-assistant"
        )
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Malformed token: missing subject claim")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Authentication token has expired. Please log in again.")
    except JWTError as err:
        raise AuthenticationError(f"Could not validate credentials: {str(err)}")
