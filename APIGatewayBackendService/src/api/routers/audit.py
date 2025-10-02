from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from ..core.db import get_session
from ..core.security import rbac_required
from ..models.models import AuditLog
from ..schemas.schemas import AuditLogOut

router = APIRouter()

# PUBLIC_INTERFACE
@router.get("/logs", response_model=List[AuditLogOut], summary="Get audit logs")
async def get_logs(type: Optional[str] = None, session: AsyncSession = Depends(get_session), current=Depends(rbac_required(["admin"]))):
    """Retrieve audit logs. Admin-only. Optional filter by action type."""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    res = await session.execute(stmt)
    logs = res.scalars().all()
    if type:
        logs = [l for l in logs if l.action == type]
    return logs
