import os
from pydantic import BaseModel, Field

class Settings(BaseModel):
    app_name: str = Field(default=os.getenv("APP_NAME", "Knowledgebase Backend API"))
    debug: bool = Field(default=os.getenv("APP_DEBUG", "true").lower() == "true")
    secret_key: str = Field(default=os.getenv("SECRET_KEY", "change-me"))
    jwt_algorithm: str = Field(default=os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = Field(default=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    refresh_token_expire_minutes: int = Field(default=int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", "43200")))
    password_min_length: int = Field(default=int(os.getenv("PASSWORD_MIN_LENGTH", "12")))
    enable_mfa: bool = Field(default=os.getenv("ENABLE_MFA", "true").lower() == "true")

    database_url: str = Field(default=os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/knowledgebase"))

    storage_root: str = Field(default=os.getenv("STORAGE_ROOT", "./storage"))
    max_upload_size_mb: int = Field(default=int(os.getenv("MAX_UPLOAD_SIZE_MB", "1024")))

    audit_hash_chain_salt: str = Field(default=os.getenv("AUDIT_HASH_CHAIN_SALT", "salt"))
    log_retention_days: int = Field(default=int(os.getenv("LOG_RETENTION_DAYS", "365")))

settings = Settings()
