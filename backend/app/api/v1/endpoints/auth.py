from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_token, decode_token, get_password_hash, hash_token, verify_password
from app.core.totp import generate_base32_secret, provisioning_uri, verify_totp
from app.db.session import get_db
from app.models.audit import AuthAuditLog
from app.models.auth import RefreshToken
from app.models.billing import Subscription
from app.models.user import User

router = APIRouter()
MAX_MFA_FAILURES = 5
MFA_LOCK_MINUTES = 15


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class MFAVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class MFASetupResponse(BaseModel):
    secret: str
    otpauth_url: str


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


def _create_audit_log(db: Session, user_id: str | None, event_type: str, result: str, detail: str | None = None) -> None:
    db.add(AuthAuditLog(user_id=user_id, event_type=event_type, result=result, detail=detail))


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


@router.post("/mfa/setup")
def mfa_setup(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MFASetupResponse:
    if current_user.mfa_secret is None:
        current_user.mfa_secret = generate_base32_secret()
    otpauth_url = provisioning_uri(current_user.mfa_secret, account_name=current_user.email, issuer_name="Auto Investing")

    _create_audit_log(db, current_user.id, "mfa_setup", "success")
    db.commit()
    return MFASetupResponse(secret=current_user.mfa_secret, otpauth_url=otpauth_url)


@router.post("/mfa/verify")
def mfa_verify(
    payload: MFAVerifyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, bool]:
    now = datetime.now(tz=timezone.utc)
    if not current_user.mfa_secret:
        _create_audit_log(db, current_user.id, "mfa_verify", "failure", "mfa not setup")
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mfa not configured")

    locked_until = current_user.mfa_locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until and locked_until > now:
        _create_audit_log(db, current_user.id, "mfa_verify", "locked", "too many failures")
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="mfa temporarily locked")

    verified = verify_totp(current_user.mfa_secret, payload.code, valid_window=1)

    if not verified:
        current_user.mfa_failed_attempts += 1
        detail = f"failed attempts={current_user.mfa_failed_attempts}"
        if current_user.mfa_failed_attempts >= MAX_MFA_FAILURES:
            current_user.mfa_locked_until = now + timedelta(minutes=MFA_LOCK_MINUTES)
            _create_audit_log(db, current_user.id, "mfa_verify", "locked", detail)
            db.commit()
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="mfa temporarily locked")

        _create_audit_log(db, current_user.id, "mfa_verify", "failure", detail)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid mfa code")

    current_user.mfa_enabled = True
    current_user.mfa_failed_attempts = 0
    current_user.mfa_locked_until = None
    _create_audit_log(db, current_user.id, "mfa_verify", "success")
    db.commit()
    return {"verified": True}


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
        _create_audit_log(db, user_id, "token_refresh", "failure", "revoked or unknown refresh token")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token revoked or unknown")

    expires_at = datetime.fromtimestamp(token_exp, tz=timezone.utc) if isinstance(token_exp, int) else stored_token.expires_at
    if isinstance(expires_at, datetime) and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(tz=timezone.utc):
        _create_audit_log(db, user_id, "token_refresh", "failure", "refresh token expired")
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token expired")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")

    stored_token.revoked_at = datetime.now(tz=timezone.utc)
    access_token, new_refresh_token = _issue_token_pair(db, user)
    _create_audit_log(db, user.id, "token_refresh", "success")
    db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=_to_user_response(user),
    )
