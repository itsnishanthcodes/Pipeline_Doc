from __future__ import annotations

import hashlib
import hmac
import base64


def hash_password(password: str) -> str:
    salt = "rootcause_salt_2026"
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()


def verify_password(password: str, hashed_password: str) -> bool:
    return hash_password(password) == hashed_password


def create_simple_token(user_id: int, email: str) -> str:
    raw = f"{user_id}:{email}"
    return base64.b64encode(raw.encode("utf-8")).decode("utf-8")


def verify_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)

