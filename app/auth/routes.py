"""
Authentication API Endpoints for Research Intelligence Assistant V2.
Provides registration, login, profile inspection, and session logout.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.auth.dependencies import get_current_user
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
    revoke_token,
)
from app.core.config import get_settings
from app.core.logging import logger
from app.core.rate_limiter import limiter
from app.db.models import User
from app.db.session import get_db

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    req: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """Registers a new user account with secure password hashing and returns an access token."""
    existing_email = db.query(User).filter(User.email == req.email.lower()).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists"
        )

    existing_username = db.query(User).filter(User.username == req.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken"
        )

    user_id = f"usr_{uuid.uuid4().hex[:16]}"
    hashed_pw = hash_password(req.password)

    new_user = User(
        id=user_id,
        username=req.username,
        email=req.email.lower(),
        hashed_password=hashed_pw,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Registered new user: username='{new_user.username}', id='{new_user.id}'")

    token = create_access_token({"sub": new_user.id, "username": new_user.username})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
def login(
    req: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticates credentials and returns a secure JWT access token."""
    identifier = req.username_or_email.strip()
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: username/email or password incorrect"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    logger.info(f"User login successful: username='{user.username}', id='{user.id}'")

    token = create_access_token({"sub": user.id, "username": user.username})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """Returns the authenticated profile of the requesting user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user)
):
    """Terminates and revokes the current session token."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        revoke_token(token, user_id=current_user.id)
    logger.info(f"User logged out: username='{current_user.username}', id='{current_user.id}'")
    return {
        "status": "success",
        "message": "Logged out successfully; session token revoked"
    }
