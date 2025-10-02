from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv
import os
from .routers import auth, users, content, search, qa, audit
from .core.db import init_db, close_db
from .core.security import get_current_active_user_optional

# Load .env
load_dotenv()

openapi_tags = [
    {"name": "Health", "description": "Service health and info"},
    {"name": "Auth", "description": "User authentication, JWT, MFA"},
    {"name": "Users", "description": "User and RBAC management"},
    {"name": "Content", "description": "Content CRUD, metadata, media upload"},
    {"name": "Search", "description": "Search over content and transcripts"},
    {"name": "Q&A", "description": "Ask questions and get answers"},
    {"name": "Audit", "description": "Audit logs and compliance"},
]

app = FastAPI(
    title=os.getenv("APP_NAME", "Knowledgebase Backend API"),
    description="REST API for all business operations: content, user, security, search, Q&A, integration.",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS
allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allow_origins.split(",")] if allow_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple request audit middleware (high-level)
class RequestAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Attach a simple header to show audit trace id placeholder
        response.headers["X-Audit-Trace"] = "trace-"  # could be set with real trace id
        return response

app.add_middleware(RequestAuditMiddleware)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(content.router, prefix="/content", tags=["Content"])
app.include_router(search.router, tags=["Search"])
app.include_router(qa.router, prefix="/qa", tags=["Q&A"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])


@app.on_event("startup")
async def on_startup():
    await init_db()
    storage_root = os.getenv("STORAGE_ROOT", "./storage")
    os.makedirs(storage_root, exist_ok=True)


@app.on_event("shutdown")
async def on_shutdown():
    await close_db()


# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["Health"])
def health_check(current_user=Depends(get_current_active_user_optional)):
    """Health check endpoint. Returns service status.
    Parameters:
      - current_user: optional authenticated user (for RBAC-aware readiness)
    Returns:
      - JSON status message with optional user info.
    """
    return JSONResponse(
        {"status": "ok", "user": current_user["email"] if current_user else None}
    )


# PUBLIC_INTERFACE
@app.get("/ws/help", summary="WebSocket Usage Help", tags=["Health"])
def websocket_usage_note():
    """Describes how to connect to real-time WebSocket endpoints (future extension).
    Parameters: none
    Returns:
      - JSON with instructions and example URLs.
    """
    return {
        "websocket_endpoints": [],
        "note": "No WebSockets implemented yet. Future endpoints will be documented here with operation_id and usage examples.",
    }
