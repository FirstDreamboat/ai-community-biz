"""认证相关 Schema。"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class UserInfo(BaseModel):
    id: int
    username: str
    real_name: str | None = None
    dept: str | None = None
    roles: list[str] = []
    permissions: list[str] = []


class LoginResponse(BaseModel):
    token: str
    expires_in: int
    user: UserInfo


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=100)
    new_password: str = Field(min_length=6, max_length=100)
