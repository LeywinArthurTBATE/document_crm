from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse

from app.core.templates import templates  # ✅ теперь правильно
from app.dependencies.auth import get_current_user

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/admin/users", response_class=HTMLResponse)
async def users_page(
    request: Request
):
    return templates.TemplateResponse("users.html", {"request": request})