from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole, UserStatus

class UserBase(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.student

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    status: Optional[UserStatus] = None
    role: Optional[UserRole] = None

class UserInDBBase(UserBase):
    id: int
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class UserResponse(UserInDBBase):
    pass
