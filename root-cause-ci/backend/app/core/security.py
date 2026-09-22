from __future__ import annotations

import hashlib
import hmac
import base64
import json
import time

from app.core.config import get_settings


def hash_password(password: str) -> str:
    salt = "rootcause_salt_2026"
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()


def verify_password(password: str, hashed_password: str) -> bool:
    return hash_password(password) == hashed_password


def create_simple_token(user_id: int, email: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + (get_settings().auth_token_expire_minutes * 60),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _encode_part(header)
    encoded_payload = _encode_part(payload)
    unsigned_token = f"{encoded_header}.{encoded_payload}"
    signature = _sign(unsigned_token)
    return f"{unsigned_token}.{signature}"


def decode_token(token: str) -> dict:
    try:
        encoded_header, encoded_payload, signature = token.split(".")
        unsigned_token = f"{encoded_header}.{encoded_payload}"
        if not hmac.compare_digest(signature, _sign(unsigned_token)):
            return {}

        payload = json.loads(_decode_part(encoded_payload))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return {}
        return payload
    except Exception:
        return {}


def _encode_part(value: dict) -> str:
    encoded = json.dumps(value, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).rstrip(b"=").decode("ascii")


def _decode_part(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")


def _sign(value: str) -> str:
    digest = hmac.new(
        get_settings().auth_secret.encode("utf-8"),
        value.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_webhook_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    if not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)

