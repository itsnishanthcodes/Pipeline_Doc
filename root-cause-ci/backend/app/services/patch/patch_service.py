"""Evidence-grounded, scope-constrained patch generation.

The LLM receives the real content of the target file at the failing commit, the diff of the most
likely culprit commit and the evidence chain. Its answer is validated before it can be used:
the file must be inside the allowed scope, must actually change, and Python output must parse.
"""
from __future__ import annotations

import difflib
import json

import httpx

from app.core.config import get_settings
from app.services.analysis.log_analysis import StackFrame, is_test_path
from app.services.ast.parser import ASTParser

MAX_FILE_CHARS = 16000


def choose_target_file(
    frames: list[StackFrame],
    best_candidate: dict | None,
    test_imports_changed: list[str] | None = None,
) -> str | None:
    """Pick the single file the fix should modify.

    Order of preference:
    1. the deepest non-test frame from the stack trace (where the error was raised);
    2. a non-test file changed by the culprit commit that the failing test imports;
    3. a non-test file changed by the culprit commit;
    4. the deepest frame, even if it is a test file.
    """
    source_frames = [f for f in frames if not is_test_path(f.file)]
    if source_frames:
        return source_frames[-1].file
    if test_imports_changed:
        return test_imports_changed[0]
    if best_candidate:
        changed = [p for p in best_candidate.get("changed_files", []) if not is_test_path(p)]
        if changed:
            return changed[0]
    if frames:
        return frames[-1].file
    return None


def unified_diff(path: str, old: str, new: str) -> str:
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile=f"a/{path}", tofile=f"b/{path}"
        )
    )


def validate_patch(target_file: str, original: str, proposal: dict, allowed_scope: set[str]) -> tuple[str | None, str | None]:
    """Return (new_content, rejection_reason). Exactly one of them is None."""
    path = (proposal.get("file_path") or target_file or "").strip().lstrip("./")
    if path not in allowed_scope:
        return None, f"The model tried to modify '{path}', which is outside the allowed scope ({', '.join(sorted(allowed_scope))})."
    content = proposal.get("new_content") or proposal.get("patch")
    if not isinstance(content, str) or not content.strip():
        return None, "The model did not return file content."
    if content.strip() == original.strip():
        return None, "The proposed content is identical to the current file."
    if path.endswith(".py") and ASTParser().has_syntax_errors(content):
        return None, "The proposed Python file contains syntax errors."
    if not content.endswith("\n"):
        content += "\n"
    return content, None


def build_prompt(repo: str, run_id: int, target_file: str, original: str, error_lines: list[str],
                 evidence: list[dict], culprit_patch: str | None, category: str) -> str:
    evidence_str = "\n".join(f"- {e['signal']}: {e['explanation']}" for e in evidence) or "- none"
    culprit = culprit_patch[:4000] if culprit_patch else "not available"
    return f"""You are an expert software engineer fixing a failing CI pipeline.
Repository: {repo} (workflow run #{run_id})
Failure category: {category}

Deterministic evidence collected before this request:
{evidence_str}

Key lines from the failing job log:
{chr(10).join(error_lines[-25:])}

Diff introduced by the most likely culprit commit for {target_file}:
{culprit}

Current content of {target_file} at the failing commit:
<<<FILE
{original[:MAX_FILE_CHARS]}
FILE>>>

Task: fix the root cause with the smallest correct change to {target_file} only.
Keep everything else in the file unchanged. Do not modify tests to make them pass.
Respond with strict JSON using exactly this schema:
{{"summary": "one or two sentences explaining the root cause and the fix",
  "file_path": "{target_file}",
  "new_content": "the COMPLETE fixed content of {target_file}"}}
If no safe fix is possible, return the same JSON with "new_content": null."""


async def call_llm(prompt: str, max_tokens: int) -> dict:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    body = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        response = await client.post(settings.llm_api_url, headers=headers, json=body)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
    return json.loads(content)


async def generate_patch(
    *, repo: str, run_id: int, target_file: str | None, original: str | None, error_lines: list[str],
    evidence: list[dict], culprit_patch: str | None, category: str, allowed_scope: set[str],
) -> dict:
    """Returns a dict with status in {generated, rejected, skipped, error} plus details."""
    result = {"status": "skipped", "file_path": target_file, "summary": None, "new_content": None,
              "diff": None, "reason": None}
    settings = get_settings()
    if not target_file or original is None:
        result["reason"] = "No source file could be located from the stack trace or the culprit commit."
        return result
    if not settings.llm_api_key or not settings.llm_api_key.strip():
        result["reason"] = "LLM_API_KEY is not configured, so no patch was generated."
        return result

    prompt = build_prompt(repo, run_id, target_file, original, error_lines, evidence, culprit_patch, category)
    max_tokens = min(6000, max(1024, len(original) // 3 + 600))
    try:
        proposal = await call_llm(prompt, max_tokens)
    except Exception as exc:  # network, quota or malformed JSON
        result.update(status="error", reason=f"LLM request failed: {exc}")
        return result

    result["summary"] = proposal.get("summary")
    new_content, rejection = validate_patch(target_file, original, proposal, allowed_scope)
    if rejection:
        result.update(status="rejected", reason=rejection)
        return result
    result.update(status="generated", new_content=new_content, diff=unified_diff(target_file, original, new_content))
    return result
