from datetime import datetime, timedelta, timezone
from typing import Optional, List, Callable, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .config import settings
from .db import get_session
from ..models.models import User, Role, AuditLog
import pyotp
import hashlib
from starlette.requests import Request

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def _jwt_payload(user_id: int, email: str, scopes: list[str]) -> dict:
    return {"sub": str(user_id), "email": email, "scopes": scopes}

def create_access_token(user_id: int, email: str, scopes: list[str], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = _jwt_payload(user_id, email, scopes).copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> dict:
    payload = decode_token(token)
    user_id = int(payload.get("sub"))
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive or missing user")
    role_name = None
    if user.role_id:
        r = await session.execute(select(Role).where(Role.id == user.role_id))
        role = r.scalar_one_or_none()
        role_name = role.name if role else None
    return {"id": user.id, "email": user.email, "is_superuser": user.is_superuser, "role": role_name, "scopes": payload.get("scopes", [])}

async def get_current_active_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = decode_token(token)
        return {"email": payload.get("email"), "scopes": payload.get("scopes", [])}
    except Exception:
        return None

def rbac_required(required_roles: Optional[List[str]] = None, allow_superuser: bool = True) -> Callable[[dict], Any]:
    async def dependency(current=Depends(get_current_user)):
        if allow_superuser and current.get("is_superuser"):
            return current
        if required_roles:
            role = current.get("role")
            if role not in required_roles:
                raise HTTPException(status_code=403, detail="Insufficient role")
        return current
    return dependency

def mfa_verify_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)

async def audit_log(session: AsyncSession, action: str, entity_type: Optional[str], entity_id: Optional[str], details: Optional[dict], user_id: Optional[int], request: Optional[Request]):
    # Tamper-evident chain by hashing previous record (simple variant)
    # Get previous hash:
    prev_hash = None
    last_id = await session.scalar(select(AuditLog.id).order_by(AuditLog.id.desc()))
    if last_id:
        prev = await session.get(AuditLog, last_id)
        prev_hash = prev.hash
    base_str = f"{action}|{entity_type}|{entity_id}|{user_id}|{datetime.utcnow().isoformat()}|{details}|{settings.audit_hash_chain_salt}|{prev_hash}"
    curr_hash = hashlib.sha256(base_str.encode("utf-8")).digest()
    ip = request.client.host if request and request.client else None
    log = AuditLog(user_id=user_id, action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id else None, details=details, ip=ip, prev_hash=prev_hash, hash=curr_hash)
    session.add(log)
    await session.commit()
