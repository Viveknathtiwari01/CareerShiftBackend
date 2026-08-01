from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.core.constants import PASSWORD_REGEX

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., pattern=PASSWORD_REGEX, description="Password must meet policy requirements.")

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None

class UserResponse(UserBase):
    id: UUID
    avatar: Optional[str]
    status: str
    email_verified: bool
    mfa_enabled: bool
    roles: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
    @field_validator('roles', mode='before')
    def extract_role_names(cls, v):
        if not v:
            return []
        return [role.name if hasattr(role, 'name') else str(role) for role in v]

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., pattern=PASSWORD_REGEX, description="Password must meet policy requirements.")
    confirm_password: str
