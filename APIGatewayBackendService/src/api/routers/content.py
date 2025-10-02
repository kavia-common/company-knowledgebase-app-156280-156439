from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any, List
import os
import json
from ..core.db import get_session
from ..core.security import get_current_user, audit_log
from ..core.utils import validate_and_classify, storage_path
from ..core.config import settings
from ..models.models import Content, ContentVersion
from ..schemas.schemas import ContentOut, ContentUpdateRequest

router = APIRouter()

# PUBLIC_INTERFACE
@router.get("", response_model=List[ContentOut], summary="List/search content")
async def list_content(q: Optional[str] = None, type: Optional[str] = None, session: AsyncSession = Depends(get_session), current=Depends(get_current_user)):
    """List content with optional query and type filter."""
    stmt = select(Content).where(Content.is_deleted == False)
    if type:
        stmt = stmt.where(Content.type == type)
    res = await session.execute(stmt.order_by(Content.created_at.desc()))
    items = res.scalars().all()
    if q:
        ql = q.lower()
        items = [i for i in items if (i.title and ql in i.title.lower()) or (i.tags and ql in i.tags.lower()) or (i.text and ql in i.text.lower())]
    return [i for i in items]

# PUBLIC_INTERFACE
@router.post("", status_code=201, summary="Upload new content")
async def upload_content(
    file: UploadFile = File(..., description="File to upload"),
    title: str = Form(..., description="Title of the content"),
    metadata: Optional[str] = Form(None, description="JSON metadata"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    category: Optional[str] = Form(None, description="Category or folder"),
    session: AsyncSession = Depends(get_session),
    current=Depends(get_current_user),
    request: Request = None
):
    """Upload new content (text/video/audio). Validates file types and stores securely."""
    # Validate size by reading incrementally
    total = 0
    chunk_size = 1024 * 1024
    classifier, ext = validate_and_classify(file.filename)
    tmp_filename = f"{current['id']}_{os.path.basename(file.filename)}"
    path = storage_path(classifier, tmp_filename)

    with open(path, "wb") as out:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > settings.max_upload_size_mb * 1024 * 1024:
                out.close()
                os.remove(path)
                raise HTTPException(status_code=400, detail="File too large")
            out.write(chunk)

    meta_obj: Any = None
    if metadata:
        try:
            meta_obj = json.loads(metadata)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")

    # For text files, attempt to load text content (simple)
    text_content = None
    if classifier == "text":
        try:
            # only for .txt; pdf/docx parsing would require extra libs; keep placeholder
            if ext == ".txt":
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()
        except Exception:
            text_content = None

    content = Content(
        owner_id=current["id"],
        title=title,
        type=classifier,
        path=path if classifier in ("video", "audio", "text") else None,
        text=text_content,
        metadata=meta_obj,
        tags=tags,
        category=category,
        is_deleted=False
    )
    session.add(content)
    await session.flush()

    # Initial version
    version = ContentVersion(
        content_id=content.id,
        version=1,
        path=content.path,
        text=content.text,
        metadata=content.metadata,
        tags=content.tags
    )
    session.add(version)
    await session.commit()

    await audit_log(session, "upload_content", "content", str(content.id), {"type": classifier, "title": title}, current["id"], request)
    return {"message": "Content uploaded", "id": content.id}

# PUBLIC_INTERFACE
@router.get("/{id}", response_model=ContentOut, summary="Get content by ID")
async def get_content(id: int, session: AsyncSession = Depends(get_session), current=Depends(get_current_user)):
    """Get a content item by ID."""
    obj = await session.get(Content, id)
    if not obj or obj.is_deleted:
        raise HTTPException(status_code=404, detail="Not found")
    return obj

# PUBLIC_INTERFACE
@router.put("/{id}", summary="Update content")
async def update_content(id: int, body: ContentUpdateRequest, session: AsyncSession = Depends(get_session), current=Depends(get_current_user), request: Request = None):
    """Update content metadata/tags/title/category or text; creates a new version."""
    obj = await session.get(Content, id)
    if not obj or obj.is_deleted:
        raise HTTPException(status_code=404, detail="Not found")
    changed = False
    if body.title is not None:
        obj.title = body.title; changed = True
    if body.category is not None:
        obj.category = body.category; changed = True
    if body.metadata is not None:
        obj.metadata = body.metadata; changed = True
    if body.tags is not None:
        obj.tags = ",".join(body.tags) if isinstance(body.tags, list) else body.tags; changed = True
    if body.text is not None:
        obj.text = body.text; changed = True

    if changed:
        # version increment
        last_ver = await session.scalar(select(ContentVersion.version).where(ContentVersion.content_id == id).order_by(ContentVersion.version.desc()))
        next_ver = (last_ver or 0) + 1
        v = ContentVersion(content_id=id, version=next_ver, path=obj.path, text=obj.text, metadata=obj.metadata, tags=obj.tags)
        session.add(v)
        await session.commit()
        await audit_log(session, "update_content", "content", str(id), {"version": next_ver}, current["id"], request)
    return {"message": "Content updated", "id": id}

# PUBLIC_INTERFACE
@router.delete("/{id}", status_code=204, summary="Delete content")
async def delete_content(id: int, hard: bool = False, session: AsyncSession = Depends(get_session), current=Depends(get_current_user), request: Request = None):
    """Soft delete by default; hard delete if explicitly requested. Logs audit event."""
    obj = await session.get(Content, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    if hard:
        # Remove file if present
        if obj.path and os.path.exists(obj.path):
            try:
                os.remove(obj.path)
            except Exception:
                pass
        await session.delete(obj)
    else:
        obj.is_deleted = True
    await session.commit()
    await audit_log(session, "delete_content_hard" if hard else "delete_content_soft", "content", str(id), None, current["id"], request)
    return
