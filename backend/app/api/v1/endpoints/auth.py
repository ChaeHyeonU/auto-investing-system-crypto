from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_token, decode_token, get_password_hash, hash_token, verify_password
from app.db.session import get_db
from app.models.auth import RefreshToken
from app.models.billing import Subscription
from app.models.user import User

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    mfa_enabled: bool
    status: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, role=user.role, mfa_enabled=user.mfa_enabled, status=user.status)


def _issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    access_token = create_token(user.id, settings.access_token_expire_minutes, token_type="access")
    refresh_token = create_token(user.id, settings.refresh_token_expire_minutes, token_type="refresh")
    expires_at = datetime.now(tz=timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)

    db.add(RefreshToken(user_id=user.id, token_hash=hash_token(refresh_token), expires_at=expires_at))
    return access_token, refresh_token


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already exists")

    user = User(email=payload.email, password_hash=get_password_hash(payload.password))
    db.add(user)
    db.flush()

    now = datetime.now(tz=timezone.utc)
    sub = Subscription(
        user_id=user.id,
        plan="basic",
        status="trialing",
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(sub)

    access_token, refresh_token = _issue_token_pair(db, user)
    db.commit()
    db.refresh(user)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_to_user_response(user),
    )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    access_token, refresh_token = _issue_token_pair(db, user)
    db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_to_user_response(user),
    )


@router.post("/refresh")
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token") from exc

    token_type = decoded.get("type")
    user_id = decoded.get("sub")
    token_exp = decoded.get("exp")
    if token_type != "refresh" or not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid refresh token")

    stored_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.token_hash == hash_token(payload.refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
        .first()
    )
    if stored_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token revoked or unknown")

    expires_at = datetime.fromtimestamp(token_exp, tz=timezone.utc) if isinstance(token_exp, int) else stored_token.expires_at
    if expires_at < datetime.now(tz=timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token expired")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    stored_token.revoked_at = datetime.now(tz=timezone.utc)
    access_token, new_refresh_token = _issue_token_pair(db, user)
    db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=_to_user_response(user),
    )
