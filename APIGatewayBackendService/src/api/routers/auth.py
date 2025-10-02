from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
import secrets
import pyotp

from ..core.db import get_session
from ..core.security import hash_password, verify_password, create_access_token, audit_log
from ..core.config import settings
from ..models.models import User, Role, RefreshToken
from ..schemas.schemas import RegisterRequest, LoginRequest, TokenResponse

router = APIRouter()

# PUBLIC_INTERFACE
@router.post("/register", summary="Register a new user", responses={201: {"description": "User registered"}, 400: {"description": "Validation error"}})
async def register(req: RegisterRequest, session: AsyncSession = Depends(get_session), request: Request = None):
    """Register a new user with strong password policy and unique email."""
    if len(req.password) < settings.password_min_length:
        raise HTTPException(status_code=400, detail=f"Password must be at least {settings.password_min_length} characters")

    existing = await session.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    role = await session.execute(select(Role).where(Role.name == "user"))
    role_obj = role.scalar_one_or_none()
    if not role_obj:
        role_obj = Role(name="user", description="Standard user")
        session.add(role_obj)
        await session.flush()

    user = User(email=req.email, name=req.name, password_hash=hash_password(req.password), role_id=role_obj.id, is_active=True, is_superuser=False)
    session.add(user)
    await session.commit()

    await audit_log(session, action="register", entity_type="user", entity_id=str(user.id), details={"email": user.email}, user_id=user.id, request=request)

    return {"message": "User registered", "user_id": user.id}

# PUBLIC_INTERFACE
@router.post("/login", response_model=TokenResponse, summary="User login (OAuth2/JWT)", responses={200: {"description": "Login successful, returns JWT token"}, 401: {"description": "Invalid credentials"}})
async def login(req: LoginRequest, session: AsyncSession = Depends(get_session), request: Request = None):
    """User login. Supports optional MFA with TOTP. Returns JWT access and refresh tokens."""
    res = await session.execute(select(User).where(User.email == req.email))
    user = res.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")

    if settings.enable_mfa and user.mfa_secret:
        if not req.mfa_code or not pyotp.TOTP(user.mfa_secret).verify(req.mfa_code, valid_window=1):
            raise HTTPException(status_code=401, detail="MFA code required or invalid")

    scopes = [user.role.name] if user.role_id else []
    access = create_access_token(user.id, user.email, scopes)
    refresh = secrets.token_urlsafe(64)
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)
    session.add(RefreshToken(user_id=user.id, token=refresh, expires_at=expires, is_revoked=False))
    await session.commit()

    await audit_log(session, action="login", entity_type="user", entity_id=str(user.id), details=None, user_id=user.id, request=request)

    return TokenResponse(access_token=access, expires_in=settings.access_token_expire_minutes * 60, refresh_token=refresh, token_type="bearer")

# PUBLIC_INTERFACE
@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(refresh_token: str, session: AsyncSession = Depends(get_session), request: Request = None):
    """Exchange a refresh token for a new access token."""
    q = await session.execute(
        select(RefreshToken, User)
        .join(User, RefreshToken.user_id == User.id)
        .where(RefreshToken.token == refresh_token, RefreshToken.is_revoked == False, RefreshToken.expires_at > datetime.now(timezone.utc))
    )
    row = q.first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = row[1]
    scopes = [user.role.name] if user.role_id else []
    access = create_access_token(user.id, user.email, scopes)
    await audit_log(session, action="refresh_token", entity_type="user", entity_id=str(user.id), details=None, user_id=user.id, request=request)
    return TokenResponse(access_token=access, expires_in=settings.access_token_expire_minutes * 60, refresh_token=refresh_token, token_type="bearer")

# PUBLIC_INTERFACE
@router.post("/mfa/setup", summary="Setup MFA (TOTP)")
async def mfa_setup(session: AsyncSession = Depends(get_session), request: Request = None, refresh_token: str | None = None):
    """Generate a TOTP secret for MFA. Requires a valid refresh token as proof of recent login."""
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token required")
    q = await session.execute(
        select(RefreshToken, User)
        .join(User, RefreshToken.user_id == User.id)
        .where(RefreshToken.token == refresh_token, RefreshToken.is_revoked == False)
    )
    row = q.first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = row[1]
    if user.mfa_secret:
        secret = user.mfa_secret
    else:
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        await session.commit()
    await audit_log(session, "mfa_setup", "user", str(user.id), None, user.id, request)
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=settings.app_name)
    return {"secret": secret, "otpauth_uri": uri}
