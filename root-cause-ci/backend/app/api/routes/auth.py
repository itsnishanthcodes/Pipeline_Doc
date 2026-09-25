from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import create_access_token, hash_password, needs_rehash, verify_password
from app.models.user import User
from app.schemas.auth import (
    GitHubVerifyRequest,
    GitHubVerifyResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.services.github_tokens import github_token_for, public_user, store_github_token

router = APIRouter(prefix="/auth", tags=["auth"])


async def verify_github_credentials(username: str | None, token: str | None) -> tuple[bool, str, str | None]:
    """Validate a GitHub username and token against the GitHub API. Returns (valid, message, avatar_url)."""
    clean_user = username.strip() if username else None
    clean_token = token.strip() if token else None
    if not clean_user and not clean_token:
        return True, "No GitHub account connected.", None

    headers = {"Accept": "application/vnd.github.v3+json"}
    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"
    avatar_url: str | None = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if clean_token:
                res = await client.get("https://api.github.com/user", headers=headers)
                if res.status_code in (401, 403):
                    return False, "GitHub rejected this token. Check that it is valid and not expired.", None
                if res.status_code == 200:
                    data = res.json()
                    login = data.get("login", "")
                    avatar_url = data.get("avatar_url")
                    if clean_user and login.lower() != clean_user.lower():
                        return False, f"This token belongs to @{login}, not @{clean_user}.", None
                    clean_user = clean_user or login
            if clean_user:
                res = await client.get(f"https://api.github.com/users/{clean_user}", headers=headers)
                if res.status_code == 404:
                    return False, f"There is no GitHub account named @{clean_user}.", None
                if res.status_code == 200:
                    avatar_url = avatar_url or res.json().get("avatar_url")
    except httpx.HTTPError:
        return False, "GitHub could not be reached. Try again in a moment.", None
    return True, f"Connected to GitHub as @{clean_user}.", avatar_url


def _token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, user.email),
        expires_in=get_settings().access_token_ttl_minutes * 60,
        user=public_user(user),
    )


@router.post("/verify-github", response_model=GitHubVerifyResponse)
async def verify_github(data: GitHubVerifyRequest) -> GitHubVerifyResponse:
    valid, message, avatar_url = await verify_github_credentials(data.github_username, data.github_token)
    return GitHubVerifyResponse(valid=valid, message=message, avatar_url=avatar_url)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: Session = Depends(get_db_session)) -> TokenResponse:
    email = data.email.lower()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(status_code=400, detail="An account with this email already exists. Sign in instead.")
    if data.github_username or data.github_token:
        valid, msg, _ = await verify_github_credentials(data.github_username, data.github_token)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        hashed_password=hash_password(data.password),
        github_username=(data.github_username or "").strip() or None,
        role=data.role or "DevOps Engineer",
    )
    store_github_token(user, data.github_token)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db_session)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower()))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="That email and password don't match an account.")
    changed = False
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(data.password)  # upgrade legacy static-salt hashes
        changed = True
    if user.github_token and not user.github_token.startswith("enc:"):
        store_github_token(user, user.github_token)  # encrypt tokens saved before encryption existed
        changed = True
    if changed:
        db.commit()
        db.refresh(user)
    return _token_response(user)


@router.get("/me", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    return public_user(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserResponse:
    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Your current password is incorrect.")

    username_changed = data.github_username is not None and data.github_username != current_user.github_username
    token_changed = bool(data.github_token)
    if (username_changed or token_changed) and not data.remove_github_token:
        check_user = data.github_username if data.github_username is not None else current_user.github_username
        check_token = data.github_token if token_changed else github_token_for(current_user)
        valid, msg, _ = await verify_github_credentials(check_user, check_token)
        if not valid:
            raise HTTPException(status_code=400, detail=msg)

    if data.full_name is not None:
        current_user.full_name = data.full_name.strip()
    if data.github_username is not None:
        current_user.github_username = data.github_username.strip() or None
    if data.remove_github_token:
        current_user.github_token = None
    elif token_changed:
        store_github_token(current_user, data.github_token)
    if data.role is not None:
        current_user.role = data.role
    if data.new_password:
        current_user.hashed_password = hash_password(data.new_password)

    db.commit()
    db.refresh(current_user)
    return public_user(current_user)
