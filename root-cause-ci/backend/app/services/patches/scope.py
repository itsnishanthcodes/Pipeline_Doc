from __future__ import annotations

import re
from dataclasses import dataclass


_FILE_HEADER = re.compile(r"^\+\+\+ b/(.+)$")
_DANGEROUS_CONTENT = re.compile(
    r"(curl\s+[^\n]*\|\s*(sh|bash)|wget\s+[^\n]*\|\s*(sh|bash)|rm\s+-rf\s+/|-----BEGIN\s+[^-]+KEY-----)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PatchValidation:
    valid: bool
    reason: str | None
    modified_files: list[str]


def validate_unified_patch(
    patch: str,
    allowed_files: set[str],
    max_lines: int = 400,
) -> PatchValidation:
    """Validate the boundary of an LLM patch before anything can be applied."""
    if not patch.strip():
        return PatchValidation(False, "Patch is empty.", [])
    if len(patch.splitlines()) > max_lines:
        return PatchValidation(False, f"Patch exceeds the {max_lines}-line limit.", [])
    if not patch.startswith("--- a/"):
        return PatchValidation(False, "Patch must be a unified diff.", [])

    modified_files: list[str] = []
    for line in patch.splitlines():
        match = _FILE_HEADER.match(line)
        if match:
            path = match.group(1).strip()
            if path not in modified_files:
                modified_files.append(path)

    if not modified_files:
        return PatchValidation(False, "Unified diff contains no modified files.", [])
    if not set(modified_files).issubset(allowed_files):
        outside_scope = sorted(set(modified_files) - allowed_files)
        return PatchValidation(
            False,
            f"Patch modifies files outside the allowed scope: {', '.join(outside_scope)}.",
            modified_files,
        )
    if any(path.startswith((".github/", ".env", "secrets/")) for path in modified_files):
        return PatchValidation(False, "Patch cannot modify CI configuration or secrets.", modified_files)
    if _DANGEROUS_CONTENT.search(patch):
        return PatchValidation(False, "Patch contains a potentially dangerous command or secret.", modified_files)

    return PatchValidation(True, None, modified_files)