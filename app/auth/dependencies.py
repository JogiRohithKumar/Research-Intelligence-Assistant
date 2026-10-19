"""
Authentication and Authorization dependencies for FastAPI endpoints.
Enforces multi-tenant boundary checks and user identity resolution.
"""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.core.config import get_settings
from app.core.correlation import set_current_user_id
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.models import User
from app.db.session import get_db

settings = get_settings()
security = HTTPBearer(auto_error=False)


def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Authoritative authentication dependency.
    Extracts and validates JWT Bearer token, binding user identity to correlation context.
    Supports API Key fallback for machine-to-machine integrations.
    """
    token = auth_header.credentials if auth_header else None

    if token:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        set_current_user_id(user.id)
        return user

    # Machine/Legacy API Key authentication fallback
    if settings.API_KEY_ENABLED and x_api_key:
        if x_api_key in settings.ALLOWED_API_KEYS:
            # Resolve or create synthetic API tenant user to enforce relational multi-tenancy
            api_user = db.query(User).filter(User.username == "api_service_user").first()
            if not api_user:
                api_user = User(
                    id="usr_api_service_tenant",
                    username="api_service_user",
                    email="api-service@system.local",
                    hashed_password="[MACHINE_ACCOUNT_NO_LOGIN]",
                    is_active=True
                )
                db.add(api_user)
                db.commit()
                db.refresh(api_user)
            set_current_user_id(api_user.id)
            return api_user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

    # If auth is disabled for local testing or unauthenticated requests
    if not settings.AUTH_ENABLED:
        dev_user = db.query(User).filter(User.username == "dev_user").first()
        if not dev_user:
            dev_user = User(
                id="usr_local_dev_tenant",
                username="dev_user",
                email="dev@example.local",
                hashed_password="[DEV_MOCK_NO_LOGIN]",
                is_active=True
            )
            db.add(dev_user)
            db.commit()
            db.refresh(dev_user)
        set_current_user_id(dev_user.id)
        return dev_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials required. Please provide a valid Bearer token."
    )


def get_optional_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Returns authenticated user if a valid token is supplied, otherwise None."""
    if not auth_header:
        return None
    try:
        return get_current_user(auth_header=auth_header, db=db)
    except HTTPException:
        return None


def verify_resource_ownership(resource_owner_id: str, current_user: User) -> None:
    """
    Strict server-side multi-tenant ownership guard.
    Guarantees User A cannot access or mutate User B's resources.
    """
    if str(resource_owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have permission to access or mutate this resource"
        )
