from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    UploadFile, File, Form
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from app.core.database import get_db
from app.core.documents_access import get_doc_or_403
from app.dependencies.auth import get_current_user
from app.models import DocumentHistory, DocumentWatcher, User
from app.repositories.permissions import require_permission
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentListResponse, DocumentUpdate
)
from app.services.document_service import DocumentService
from app.repositories.document_repo import DocumentRepository
from app.utils.file_storage import save_file, save_file_stream

router = APIRouter(prefix="/documents", tags=["documents"])



async def check_owner_or_permission(db, user, doc, perm_own, perm_any):
    if user.id in [doc.author_id, doc.executor_id]:
        await require_permission(db, user, perm_own)
    else:
        await require_permission(db, user, perm_any)
# -------------------- LIST --------------------

@router.get("", response_model=List[DocumentListResponse])
async def get_documents(
    status: Optional[str] = Query(None),
    executor_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    deadline_from: Optional[date] = Query(None),
    deadline_to: Optional[date] = Query(None),
    is_overdue: Optional[bool] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await require_permission(db, user, "document.read")
    return await DocumentRepository.get_list(
        db=db,
        user=user,
        status=status,
        executor_id=executor_id,
        search=search,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        is_overdue=is_overdue,
        limit=limit,
        offset=offset,
    )


# -------------------- CREATE --------------------

@router.post("", response_model=DocumentResponse)
async def create_document(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    executor_id: Optional[UUID] = Form(None),
    deadline: date = Form(...),
    file: UploadFile = File(...),

    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    await require_permission(db, user, "document.create")

    # 🔒 проверка расширения
    ext = file.filename.split(".")[-1].lower()
    allowed = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "png", "webp"}

    if ext not in allowed:
        raise HTTPException(400, "Invalid file type")

    # 💾 сохраняем файл потоково
    try:
        file_name, file_path = await save_file_stream(file)
    except ValueError:
        raise HTTPException(400, "File too large")

    # создаем документ
    doc_data = DocumentCreate(
        title=title,
        description=description,
        executor_id=executor_id,
        deadline=deadline,
        file_name=file_name,
        file_path=file_path,
    )

    return await DocumentService.create_document(
        db=db,
        data=doc_data,
        author_id=user.id,
    )


# -------------------- GET ONE --------------------

@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    await require_permission(
        db, user,
        "document.read" if access == "owner" else "document.read_any"
    )

    return doc

# -------------------- DOWNLOAD --------------------

@router.get("/{doc_id}/download")
async def download_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    await require_permission(
        db, user,
        "document.read" if access == "owner" else "document.read_any"
    )

    return FileResponse(doc.file_path, filename=doc.file_name)

# -------------------- DELETE --------------------
@router.delete("/{doc_id}")
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    await require_permission(
        db, user,
        "document.delete" if access == "owner" else "document.delete_any"
    )

    doc.is_deleted = True
    await db.commit()

    return {"status": "deleted"}


# -------------------- PATCH --------------------

@router.patch("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: UUID,
    data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    # базовое право
    await require_permission(
        db, user,
        "document.edit" if access == "owner" else "document.edit_any"
    )

    # granular
    if data.deadline:
        await require_permission(db, user, "document.edit_deadline")

    if data.executor_id:
        await require_permission(
            db, user,
            "document.assign" if access == "owner" else "document.assign_any"
        )

    if data.status:
        await require_permission(
            db, user,
            "document.change_status" if access == "owner" else "document.change_status_any"
        )

    return await DocumentService.update_document(db, doc, data, user)

@router.get("/{doc_id}/history")
async def get_document_history(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    await require_permission(
        db, user,
        "document.read" if access == "owner" else "document.read_any"
    )

    result = await db.execute(
        select(DocumentHistory)
        .where(DocumentHistory.document_id == doc_id)
        .order_by(DocumentHistory.created_at.desc())
    )

    history = result.scalars().all()

    # сбор user_id
    user_ids = {
        v for h in history for v in [h.old_value, h.new_value]
        if h.field == "executor_id" and v
    }

    users_map = {}

    if user_ids:
        res = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = res.scalars().all()
        users_map = {str(u.id): u.full_name for u in users}

    return [
        {
            "field": h.field,
            "old_value": users_map.get(h.old_value, "—") if h.field == "executor_id" else h.old_value,
            "new_value": users_map.get(h.new_value, "—") if h.field == "executor_id" else h.new_value,
            "created_at": h.created_at,
            "changed_by": str(h.changed_by),
        }
        for h in history
    ]

# app/api/documents.py (добавить в конец файла)

@router.post("/{doc_id}/watchers/{user_id}")
async def add_watcher(
    doc_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    if access not in ["owner", "admin"]:
        raise HTTPException(403, "Not enough permissions")

    # проверка пользователя
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(404, "User not found")

    # уже есть?
    existing = await db.execute(
        select(DocumentWatcher).where(
            DocumentWatcher.document_id == doc_id,
            DocumentWatcher.user_id == user_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, "User already watcher")

    db.add(DocumentWatcher(document_id=doc_id, user_id=user_id))
    await db.commit()

    return {"status": "added"}


@router.delete("/{doc_id}/watchers/{user_id}")
async def remove_watcher(
    doc_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    if access not in ["owner", "admin"] and user.id != user_id:
        raise HTTPException(403)

    result = await db.execute(
        select(DocumentWatcher).where(
            DocumentWatcher.document_id == doc_id,
            DocumentWatcher.user_id == user_id
        )
    )
    watcher = result.scalar_one_or_none()

    if not watcher:
        raise HTTPException(404, "Watcher not found")

    await db.delete(watcher)
    await db.commit()

    return {"status": "removed"}

@router.get("/{doc_id}/watchers")
async def get_watchers(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    doc, access = await get_doc_or_403(db, user, doc_id)

    if access not in ["owner", "admin"]:
        raise HTTPException(403)

    result = await db.execute(
        select(DocumentWatcher.user_id)
        .where(DocumentWatcher.document_id == doc_id)
    )
    watcher_ids = [row[0] for row in result.all()]

    if not watcher_ids:
        return []

    users_res = await db.execute(
        select(User).where(User.id.in_(watcher_ids))
    )
    users = users_res.scalars().all()

    return [
        {"id": u.id, "full_name": u.full_name, "email": u.email}
        for u in users
    ]