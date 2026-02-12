from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models.billing import Subscription
from app.models.user import User

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
    db.commit()
    db.refresh(user)

    access_token = create_token(user.id, settings.access_token_expire_minutes, token_type="access")
    refresh_token = create_token(user.id, settings.refresh_token_expire_minutes, token_type="refresh")

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id, email=user.email, role=user.role, mfa_enabled=user.mfa_enabled, status=user.status
        ),
    )


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")

    access_token = create_token(user.id, settings.access_token_expire_minutes, token_type="access")
    refresh_token = create_token(user.id, settings.refresh_token_expire_minutes, token_type="refresh")

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse(
            id=user.id, email=user.email, role=user.role, mfa_enabled=user.mfa_enabled, status=user.status
        ),
    )
