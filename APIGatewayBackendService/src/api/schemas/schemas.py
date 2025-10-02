from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, List
from datetime import datetime

# PUBLIC_INTERFACE
class RegisterRequest(BaseModel):
    """Request body for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="Plaintext password meeting policy requirements")
    name: str = Field(..., description="Full name of the user")

# PUBLIC_INTERFACE
class LoginRequest(BaseModel):
    """Request body for login."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")
    mfa_code: Optional[str] = Field(None, description="Optional TOTP code if MFA enabled")

# PUBLIC_INTERFACE
class TokenResponse(BaseModel):
    """JWT and refresh tokens response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Seconds until access token expiration")
    refresh_token: Optional[str] = Field(None, description="Refresh token")

# PUBLIC_INTERFACE
class UserOut(BaseModel):
    """Public user profile output."""
    id: int
    email: EmailStr
    name: str
    is_active: bool
    is_superuser: bool
    role: Optional[str] = None

    class Config:
        from_attributes = True

# PUBLIC_INTERFACE
class ContentOut(BaseModel):
    """Content output model."""
    id: int
    title: str
    type: str
    path: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Any] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# PUBLIC_INTERFACE
class ContentUpdateRequest(BaseModel):
    """Request to update content metadata/tags/text."""
    metadata: Optional[Any] = None
    tags: Optional[List[str]] = None
    title: Optional[str] = None
    category: Optional[str] = None
    text: Optional[str] = None

# PUBLIC_INTERFACE
class QuestionRequest(BaseModel):
    """Ask a question for Q&A."""
    question: str = Field(..., description="Natural language question")

# PUBLIC_INTERFACE
class AuditLogOut(BaseModel):
    """Audit log output."""
    id: int
    user_id: Optional[int]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    details: Optional[Any]
    ip: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
