from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..core.db import get_session
from ..core.security import rbac_required, get_current_user, audit_log
from ..models.models import User, Role
from ..schemas.schemas import UserOut

router = APIRouter()

# PUBLIC_INTERFACE
@router.get("/me", response_model=UserOut, summary="Get my profile")
async def me(current=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Return the current user's profile."""
    res = await session.execute(select(User).where(User.id == current["id"]))
    user = res.scalar_one_or_none()
    role = None
    if user.role_id:
        r = await session.execute(select(Role).where(Role.id == user.role_id))
        role_obj = r.scalar_one_or_none()
        role = role_obj.name if role_obj else None
    return UserOut(id=user.id, email=user.email, name=user.name, is_active=user.is_active, is_superuser=user.is_superuser, role=role)

# PUBLIC_INTERFACE
@router.post("/{user_id}/role/{role_name}", summary="Assign role to user")
async def assign_role(user_id: int, role_name: str, session: AsyncSession = Depends(get_session), current=Depends(rbac_required(["admin"])) , request: Request = None):
    """Assign a role to the specified user. Admin-only."""
    res = await session.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role_res = await session.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one_or_none()
    if not role:
        role = Role(name=role_name, description=f"Role {role_name}")
        session.add(role)
        await session.flush()
    user.role_id = role.id
    await session.commit()
    await audit_log(session, "assign_role", "user", str(user.id), {"role": role_name}, current["id"], request)
    return {"message": "Role updated", "user_id": user_id, "role": role_name}
