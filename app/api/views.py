from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.templates import templates  # ✅ теперь правильно

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})