"""Password hashing, signed access tokens, secret encryption and webhook signatures."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

PBKDF2_ITERATIONS = 390_000
LEGACY_SALT = "rootcause_salt_2026"  # static salt used by the first prototype; only accepted for upgrade
ENCRYPTED_PREFIX = "enc:"


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    """PBKDF2-SHA256 with a unique random salt per password."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def _legacy_hash(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), LEGACY_SALT.encode("utf-8"), 100000).hex()


def verify_password(password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, digest = hashed_password.split("$", 3)
        except ValueError:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
        return hmac.compare_digest(candidate.hex(), digest)
    # accounts created before per-user salts; callers upgrade the hash after a successful login
    return hmac.compare_digest(_legacy_hash(password), hashed_password)


def needs_rehash(hashed_password: str) -> bool:
    return not hashed_password.startswith(f"pbkdf2_sha256${PBKDF2_ITERATIONS}$")


# ------------------------------------------------------------------ access tokens
def create_access_token(user_id: int, email: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Return the verified payload, or {} when the token is invalid, forged or expired."""
    try:
        return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return {}


# ------------------------------------------------------------------ secrets at rest (GitHub tokens)
def _fernet() -> Fernet:
    settings = get_settings()
    material = settings.token_encryption_key or settings.jwt_secret
    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return ENCRYPTED_PREFIX + _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt a stored secret. Values saved before encryption existed are returned unchanged."""
    if not value:
        return None
    if not value.startswith(ENCRYPTED_PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(ENCRYPTED_PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def secret_hint(value: str | None) -> str | None:
    """Last four characters of a secret, for display only."""
    plain = decrypt_secret(value)
    return plain[-4:] if plain and len(plain) >= 8 else None


# ------------------------------------------------------------------ webhooks
def verify_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={digest}", signature)
