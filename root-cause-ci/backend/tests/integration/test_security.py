import base64
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

import app.api.routes.repositories as repositories_module
from app.core.config import Settings, get_settings
from app.core.database import get_session_factory
from app.core.security import (
    _legacy_hash,
    create_access_token,
    decode_token,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.main import app
from app.models.user import User
from app.services.analysis.log_analysis import redact_secrets


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register(client, email, **extra):
    body = {"full_name": "Test User", "email": email, "password": "correct-horse-1", **extra}
    res = client.post("/auth/register", json=body)
    assert res.status_code == 201, res.text
    return res.json()


# ------------------------------------------------------------------ passwords
def test_passwords_use_unique_salts_and_verify():
    a, b = hash_password("same-password"), hash_password("same-password")
    assert a != b
    assert verify_password("same-password", a) and verify_password("same-password", b)
    assert not verify_password("wrong-password", a)
    assert not needs_rehash(a)


def test_legacy_hashes_still_verify_and_are_flagged_for_upgrade():
    legacy = _legacy_hash("old-password")
    assert verify_password("old-password", legacy)
    assert needs_rehash(legacy)


def test_login_upgrades_legacy_hash_and_encrypts_plaintext_token(client):
    db = get_session_factory()()
    db.add(User(full_name="Old", email="old@example.com", hashed_password=_legacy_hash("old-password"),
                github_token="ghp_plaintextlegacytoken1234"))
    db.commit()
    res = client.post("/auth/login", json={"email": "old@example.com", "password": "old-password"})
    assert res.status_code == 200
    db.expire_all()
    user = db.query(User).filter_by(email="old@example.com").one()
    assert user.hashed_password.startswith("pbkdf2_sha256$")
    assert user.github_token.startswith("enc:")
    assert decrypt_secret(user.github_token) == "ghp_plaintextlegacytoken1234"
    assert res.json()["user"]["github_token_hint"] == "1234"
    db.close()


# ------------------------------------------------------------------ tokens
def test_forged_expired_and_tampered_tokens_are_rejected(client):
    body = _register(client, "tokens@example.com")
    good = body["access_token"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {good}"}).status_code == 200

    forged = base64.b64encode(f"{body['user']['id']}:tokens@example.com".encode()).decode()  # old token format
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {good[:-3]}abc"}).status_code == 401
    expired = jwt.encode({"sub": str(body["user"]["id"]), "email": "tokens@example.com",
                          "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         get_settings().jwt_secret, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/analysis/history").status_code == 401


def test_token_payload_round_trip():
    payload = decode_token(create_access_token(7, "a@b.com"))
    assert payload["sub"] == "7" and payload["email"] == "a@b.com"
    assert decode_token("not-a-token") == {}


# ------------------------------------------------------------------ GitHub tokens at rest
def test_github_token_is_encrypted_and_never_returned(client, monkeypatch):
    async def ok(username, token):
        return True, "ok", None
    monkeypatch.setattr("app.api.routes.auth.verify_github_credentials", ok)
    body = _register(client, "gh@example.com", github_token="ghp_abcdefghijklmnopqrstuvwxyz0123456789")
    assert "github_token" not in body["user"]
    assert body["user"]["has_github_token"] is True and body["user"]["github_token_hint"] == "6789"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
    assert "github_token" not in me
    db = get_session_factory()()
    stored = db.query(User).filter_by(email="gh@example.com").one().github_token
    assert stored.startswith("enc:") and "abcdefghij" not in stored
    db.close()


def test_encrypt_round_trip_and_legacy_passthrough():
    assert decrypt_secret(encrypt_secret("ghp_secret_value_123")) == "ghp_secret_value_123"
    assert decrypt_secret("plain-old-token") == "plain-old-token"
    assert encrypt_secret(None) is None


# ------------------------------------------------------------------ webhooks and redaction
def test_production_rejects_unsigned_webhooks(client):
    app.dependency_overrides[get_settings] = lambda: Settings(APP_ENV="production", GITHUB_WEBHOOK_SECRET="",
                                                              JWT_SECRET="x" * 32)
    try:
        res = client.post("/webhooks/github", headers={"X-GitHub-Event": "workflow_run"}, json={})
        assert res.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_secrets_are_redacted_from_logs():
    log = (
        "token=ghp_abcdefghijklmnopqrstuvwxyz012345\n"
        "Authorization: Bearer abcdefghijklmnopqrstuvwx\n"
        "DATABASE_URL=postgres://admin:hunter2secret@db:5432/app\n"
        "export API_KEY='sk-live-abcdefghijklmnopqrstuv'\n"
    )
    clean = redact_secrets(log)
    for secret in ("ghp_abcdef", "abcdefghijklmnopqrstuvwx", "hunter2secret", "sk-live-abc"):
        assert secret not in clean
    assert "[REDACTED]" in clean


# ------------------------------------------------------------------ run picker
def test_recent_runs_endpoint_lists_runs(client, monkeypatch):
    class FakeClient:
        def __init__(self, token):
            assert token == "ghp_runs_token_value_000"

        async def list_recent_runs(self, repo, per_page=25):
            return [{"id": 11, "name": "CI", "run_number": 4, "status": "completed", "conclusion": "failure",
                     "head_branch": "main", "head_sha": "abc", "head_commit": {"message": "Fix totals\n\nbody"},
                     "actor": {"login": "dev"}, "event": "push", "created_at": "2026-09-25T10:00:00Z",
                     "html_url": "u"},
                    {"id": 10, "name": "CI", "head_commit": {"message": ""}}]

    monkeypatch.setattr(repositories_module, "GitHubClient", FakeClient)
    monkeypatch.setattr("app.api.routes.auth.verify_github_credentials",
                        lambda u, t: __import__("asyncio").sleep(0, result=(True, "ok", None)))
    body = _register(client, "runs@example.com", github_token="ghp_runs_token_value_000")
    res = client.get("/repositories/acme/app/runs", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert res.status_code == 200
    runs = res.json()["runs"]
    assert runs[0]["commit_message"] == "Fix totals" and runs[0]["conclusion"] == "failure"
    assert runs[1]["commit_message"] == ""
    bad = client.get("/repositories/acme/../runs", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert bad.status_code in (404, 422)


def test_evaluation_summary_is_public(client):
    res = client.get("/evaluation/summary")
    assert res.status_code == 200
    assert res.json()["summary"]["scenarios"] >= 10
