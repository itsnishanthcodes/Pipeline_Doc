"""Access to a user's GitHub token, which is stored encrypted."""
from __future__ import annotations

from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret, secret_hint
from app.models.user import User
from app.schemas.auth import UserResponse


def github_token_for(user: User | None) -> str | None:
    """The user's decrypted token, or the server-wide GITHUB_TOKEN when the user has none."""
    token = decrypt_secret(user.github_token) if user else None
    return token or get_settings().github_token


def store_github_token(user: User, raw_token: str | None) -> None:
    cleaned = raw_token.strip() if raw_token else None
    user.github_token = encrypt_secret(cleaned) if cleaned else None


def public_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        github_username=user.github_username,
        role=user.role,
        has_github_token=bool(user.github_token),
        github_token_hint=secret_hint(user.github_token),
    )
