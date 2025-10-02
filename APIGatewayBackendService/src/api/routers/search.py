from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from ..core.db import get_session
from ..core.security import get_current_user
from ..models.models import Content
from ..schemas.schemas import ContentOut

router = APIRouter()

# PUBLIC_INTERFACE
@router.get("/search", response_model=List[ContentOut], summary="Search content")
async def search(q: Optional[str] = None, session: AsyncSession = Depends(get_session), current=Depends(get_current_user)):
    """Simple search across title, tags and text. Future: integrate external search/index."""
    if not q:
        return []
    res = await session.execute(select(Content).where(Content.is_deleted == False))
    items = res.scalars().all()
    ql = q.lower()
    matches = [i for i in items if (i.title and ql in i.title.lower()) or (i.tags and ql in i.tags.lower()) or (i.text and ql in i.text.lower())]
    return matches
