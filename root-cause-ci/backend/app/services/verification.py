"""Patch verification through the repository's own CI.

After a fix branch is pushed, GitHub Actions runs the repository's workflows on that commit.
The fix is 'verified' only when a run for exactly that commit completes successfully.
"""
from __future__ import annotations

from typing import Any


def verification_from_runs(runs: list[dict[str, Any]], fix_commit_sha: str | None) -> dict[str, Any]:
    """Map the workflow runs on the fix branch to a verification verdict.

    Returns {status, detail, runs}, where status is one of:
    pending (no run yet), running, verified, failed.
    """
    relevant = [r for r in runs if not fix_commit_sha or r.get("head_sha") == fix_commit_sha]
    summary = [
        {"id": r.get("id"), "name": r.get("name"), "status": r.get("status"), "conclusion": r.get("conclusion"),
         "url": r.get("html_url")}
        for r in relevant
    ]
    if not relevant:
        return {"status": "pending", "detail": "Waiting for GitHub Actions to start a run on the fix branch.",
                "runs": summary}
    if any(r.get("status") != "completed" for r in relevant):
        return {"status": "running", "detail": "CI is running on the fix branch.", "runs": summary}
    failed = [r for r in relevant if r.get("conclusion") not in ("success", "skipped", "neutral")]
    if failed:
        names = ", ".join(r.get("name") or str(r.get("id")) for r in failed)
        return {"status": "failed", "detail": f"CI failed on the fix branch: {names}.", "runs": summary}
    return {"status": "verified", "detail": "All CI runs on the fix commit passed.", "runs": summary}
