from fastapi import APIRouter
from app.api import auth, documents, users, views

router = APIRouter()

router.include_router(auth.router)
router.include_router(documents.router)
router.include_router(users.router)
router.include_router(views.router)