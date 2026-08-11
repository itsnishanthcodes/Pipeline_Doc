from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    github_username: str | None = None
    github_token: str | None = None
    role: str = "DevOps Engineer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    github_username: str | None = None
    github_token: str | None = None
    role: str

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: int
    full_name: str
    email: str
    github_username: str | None = None
    github_token: str | None = None
    role: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: str | None = None
    github_username: str | None = None
    github_token: str | None = None
    current_password: str | None = None
    new_password: str | None = None
    role: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GitHubVerifyRequest(BaseModel):
    github_username: str | None = None
    github_token: str | None = None


class GitHubVerifyResponse(BaseModel):
    valid: bool
    message: str
    avatar_url: str | None = None
