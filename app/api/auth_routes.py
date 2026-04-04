"""Authentication routes (JWT access tokens, SQLite-backed users)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.schemas import AuthTokenResponse, LoginRequest, MeResponse, SignupRequest, UserPublic
from app.auth.security import create_access_token, hash_password, normalize_email, verify_password
from app.db.session import get_db
from app.models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])


def _display_name_from_signup(display_name: str | None) -> str | None:
    if display_name is None:
        return None
    stripped = display_name.strip()
    return stripped or None


@router.post("/signup", response_model=AuthTokenResponse)
def signup(body: SignupRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    email = normalize_email(str(body.email))
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Email already registered."},
        )

    user = User(
        email=email,
        hashed_password=hash_password(body.password),
        display_name=_display_name_from_signup(body.display_name),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject_user_id=user.id)
    return AuthTokenResponse(user=UserPublic.model_validate(user), access_token=token)


@router.post("/login", response_model=AuthTokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    email = normalize_email(str(body.email))
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Invalid email or password."},
        )

    token = create_access_token(subject_user_id=user.id)
    return AuthTokenResponse(user=UserPublic.model_validate(user), access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=UserPublic.model_validate(current_user))
