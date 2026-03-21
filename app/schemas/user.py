from pydantic import BaseModel, EmailStr
from typing import Optional

from uuid import UUID
from app.models.user import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role_id: UUID

class RoleResponse(BaseModel):
    code: str

    model_config = {
        "from_attributes": True
    }

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: RoleResponse

    model_config = {
        "from_attributes": True
    }

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[UUID] = None