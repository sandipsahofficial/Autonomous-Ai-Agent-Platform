from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[str] = Field(default="operator")


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(default="Default Automation Key", max_length=128)
    expires_in_days: Optional[int] = Field(default=30, ge=1, le=365)


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    raw_api_key: str
    expires_at: Optional[datetime]
    created_at: datetime


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
