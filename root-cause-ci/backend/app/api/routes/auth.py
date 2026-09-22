from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import create_simple_token, decode_token, hash_password, verify_password
from app.core.config import get_settings
from app.models.user import User
import httpx
from app.schemas.auth import (
    GitHubVerifyRequest,
    GitHubVerifyResponse,
    TokenResponse,
    UserLogin,
    UserProfileResponse,
    UserRegister,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()


async def verify_github_credentials(username: str | None, token: str | None) -> tuple[bool, str, str | None]:
    """
    Validates GitHub username and token against GitHub REST API.
    Returns (is_valid, message, avatar_url).
    """
    clean_user = username.strip() if username else None
    clean_token = token.strip() if token else None

    if not clean_user and not clean_token:
        return True, "No GitHub credentials provided", None

    headers = {"Accept": "application/vnd.github.v3+json"}
    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"

    avatar_url: str | None = None

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Check token validity if token is provided
        if clean_token:
            res = await client.get("https://api.github.com/user", headers=headers)
            if res.status_code in (401, 403):
                return False, "Invalid GitHub Personal Access Token (Authentication Failed)", None
            if res.status_code == 200:
                data = res.json()
                gh_login = data.get("login", "")
                avatar_url = data.get("avatar_url")
                if clean_user and gh_login.lower() != clean_user.lower():
                    return False, f"GitHub Token belongs to @{gh_login}, which does not match username @{clean_user}", None

        # 2. Check username validity on GitHub if username is provided
        if clean_user:
            res = await client.get(f"https://api.github.com/users/{clean_user}", headers=headers)
            if res.status_code == 404:
                return False, f"GitHub Username '@{clean_user}' does not exist on GitHub", None
            if res.status_code == 200:
                avatar_url = avatar_url or res.json().get("avatar_url")

    return True, f"Successfully verified GitHub account @{clean_user or 'token'}", avatar_url


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.scalar(select(User).where(User.id == int(user_id)))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


@router.post("/verify-github", response_model=GitHubVerifyResponse)
async def verify_github(data: GitHubVerifyRequest) -> GitHubVerifyResponse:
    valid, message, avatar_url = await verify_github_credentials(data.github_username, data.github_token)
    return GitHubVerifyResponse(valid=valid, message=message, avatar_url=avatar_url)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: Session = Depends(get_db_session)) -> TokenResponse:
    existing = db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Verify GitHub credentials if provided
    if data.github_username or data.github_token:
        valid, msg, _ = await verify_github_credentials(data.github_username, data.github_token)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

    user = User(
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),
        github_username=data.github_username,
        github_token=data.github_token,
        role=data.role or "DevOps Engineer",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_simple_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        expires_in=get_settings().auth_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db_session)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_simple_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        expires_in=get_settings().auth_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)


@router.put("/me", response_model=UserProfileResponse)
async def update_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserProfileResponse:
    # Verify GitHub credentials if username or token is modified
    check_user = data.github_username if data.github_username is not None else current_user.github_username
    check_token = data.github_token if data.github_token is not None else current_user.github_token

    if data.github_username is not None or data.github_token is not None:
        valid, msg, _ = await verify_github_credentials(check_user, check_token)
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg,
            )

    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.github_username is not None:
        current_user.github_username = data.github_username
    if data.github_token is not None:
        current_user.github_token = data.github_token
    if data.role is not None:
        current_user.role = data.role

    if data.new_password:
        if not data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password",
            )
        if not verify_password(data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )
        current_user.hashed_password = hash_password(data.new_password)

    db.commit()
    db.refresh(current_user)
    return UserProfileResponse.model_validate(current_user)
