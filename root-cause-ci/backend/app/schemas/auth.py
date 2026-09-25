from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    github_username: str | None = None
    github_token: str | None = None
    role: str = "DevOps Engineer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public view of a user. The GitHub token itself is never returned."""

    id: int
    full_name: str
    email: str
    github_username: str | None = None
    role: str
    has_github_token: bool = False
    github_token_hint: str | None = None


# kept as an alias so older imports keep working
UserProfileResponse = UserResponse


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    github_username: str | None = None
    github_token: str | None = None
    remove_github_token: bool = False
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class GitHubVerifyRequest(BaseModel):
    github_username: str | None = None
    github_token: str | None = None


class GitHubVerifyResponse(BaseModel):
    valid: bool
    message: str
    avatar_url: str | None = None
