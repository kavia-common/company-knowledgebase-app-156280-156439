from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from ..core.db import get_session
from ..core.security import get_current_user, audit_log
from ..models.models import Content
from ..schemas.schemas import QuestionRequest

router = APIRouter()

# PUBLIC_INTERFACE
@router.post("/ask", summary="Ask a question (Q&A)")
async def ask(body: QuestionRequest, session: AsyncSession = Depends(get_session), current=Depends(get_current_user), request: Request = None):
    """Accept a natural language question and return a simple heuristic answer with references.
    Future: call external AI/ML service and provide transparency and confidence."""
    q = body.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Invalid question")

    # Heuristic: find content containing any keyword
    res = await session.execute(select(Content).where(Content.is_deleted == False))
    items = res.scalars().all()
    tokens = [t.lower() for t in q.split() if len(t) > 2]
    matches: List[Content] = []
    for c in items:
        base = f"{c.title or ''} {c.tags or ''} {c.text or ''}".lower()
        if any(t in base for t in tokens):
            matches.append(c)
    references = [{"id": m.id, "title": m.title, "type": m.type} for m in matches[:5]]
    answer = "This is a preliminary answer based on heuristic matching. Integrate AI service for better results."
    confidence = 0.3 if references else 0.0

    await audit_log(session, "qa_ask", "qa", None, {"question": q, "refs": references}, current["id"], request)
    return {"answer": answer, "references": references, "confidence": confidence}
