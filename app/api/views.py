from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.templates import templates  # ✅ теперь правильно
from app.dependencies.auth import get_current_user
from app.models import Document, User
from app.repositories.document_repo import DocumentRepository

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/admin/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    user=Depends(get_current_user)
):
    return templates.TemplateResponse("users.html", {"request": request})

def get_status_class(status):
    mapping = {
        "NEW": "bg-yellow-100 text-yellow-800",
        "IN_PROGRESS": "bg-blue-100 text-blue-800",
        "ON_REVIEW": "bg-purple-100 text-purple-800",
        "REJECTED": "bg-red-100 text-red-800",
        "REVISION": "bg-orange-100 text-orange-800",
        "CANCELLED": "bg-gray-100 text-gray-800",
        "PAUSED": "bg-gray-200 text-gray-700",
        "DONE": "bg-green-100 text-green-800",
    }
    return mapping.get(str(status), "bg-gray-100")


def get_status_text(status):
    mapping = {
        "NEW": "Ожидает",
        "IN_PROGRESS": "В работе",
        "ON_REVIEW": "На проверке",
        "REJECTED": "Отклонено",
        "REVISION": "На доработке",
        "CANCELLED": "Отменено",
        "PAUSED": "Пауза",
        "DONE": "Выполнено",
    }
    return mapping.get(str(status), str(status))

@router.get("/documents/{doc_id}/view")
async def document_page(
    request: Request,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    result = await db.execute(
        select(Document)
        .options(
            joinedload(Document.author),
            joinedload(Document.executor)
        )
        .where(Document.id == doc_id)
    )

    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(404)

    return templates.TemplateResponse("document_detail.html", {
        "request": request,
        "doc": doc,
        "get_status_class": get_status_class,
        "get_status_text": get_status_text,
        "user": user,
    })