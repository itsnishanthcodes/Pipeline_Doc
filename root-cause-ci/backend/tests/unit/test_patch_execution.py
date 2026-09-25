from pathlib import Path

import pytest

from app.services.patches.apply import PatchApplicationError, apply_unified_patch


def test_apply_unified_patch_creates_isolated_workspace(tmp_path: Path) -> None:
    source = tmp_path / "src" / "service.py"
    source.parent.mkdir()
    source.write_text("def total():\n    return 1\n", encoding="utf-8")
    patch = "--- a/src/service.py\n+++ b/src/service.py\n@@ -1,2 +1,2 @@\n def total():\n-    return 1\n+    return 2\n"

    workspace = apply_unified_patch(tmp_path, patch)
    try:
        assert workspace.path != tmp_path
        assert (workspace.path / "src/service.py").read_text(encoding="utf-8").endswith("return 2\n")
        assert source.read_text(encoding="utf-8").endswith("return 1\n")
    finally:
        workspace.close()


def test_apply_unified_patch_rejects_bad_context(tmp_path: Path) -> None:
    source = tmp_path / "service.py"
    source.write_text("return 1\n", encoding="utf-8")
    patch = "--- a/service.py\n+++ b/service.py\n@@ -1 +1 @@\n-return 9\n+return 2\n"

    with pytest.raises(PatchApplicationError):
        apply_unified_patch(tmp_path, patch)