from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


class PatchApplicationError(RuntimeError):
    pass


class AppliedPatchWorkspace:
    def __init__(self, temporary_directory: TemporaryDirectory[str], path: Path) -> None:
        self.temporary_directory = temporary_directory
        self.path = path

    def close(self) -> None:
        self.temporary_directory.cleanup()


def apply_unified_patch(repository_path: str | Path, patch: str) -> AppliedPatchWorkspace:
    source = Path(repository_path).resolve()
    if not source.is_dir():
        raise PatchApplicationError("Repository workspace does not exist.")

    temporary_directory = TemporaryDirectory(prefix="root-cause-patch-")
    destination = Path(temporary_directory.name) / "workspace"
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    patch_file = destination.parent / "change.patch"
    patch_file.write_text(patch, encoding="utf-8")

    check = subprocess.run(
        ["git", "-C", str(destination), "apply", "--check", str(patch_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode != 0:
        temporary_directory.cleanup()
        raise PatchApplicationError(check.stderr.strip() or "Patch does not apply cleanly.")

    applied = subprocess.run(
        ["git", "-C", str(destination), "apply", str(patch_file)],
        capture_output=True,
        text=True,
        check=False,
    )
    if applied.returncode != 0:
        temporary_directory.cleanup()
        raise PatchApplicationError(applied.stderr.strip() or "Patch application failed.")
    return AppliedPatchWorkspace(temporary_directory, destination)