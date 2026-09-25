import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db_session
from app.integrations.github_client import GitHubClient
from app.models.analysis_report import AnalysisReport
from app.models.user import User
from app.services.report_serializer import serialize_report
from app.services.verification import verification_from_runs

router = APIRouter(prefix="/patches", tags=["patches"])


class CreatePRRequest(BaseModel):
    report_id: int


def _load_report(db: Session, report_id: int, user: User) -> AnalysisReport:
    report = db.get(AnalysisReport, report_id)
    if not report or report.user_id != user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


def _client(user: User) -> GitHubClient:
    token = user.github_token or get_settings().github_token
    if not token:
        raise HTTPException(status_code=401, detail="GitHub token missing. Add one in your profile.")
    return GitHubClient(token)


@router.post("/create-pr")
async def create_fix_pr(
    request: CreatePRRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Open a pull request from the validated patch stored with an analysis report.

    The content written to the repository always comes from the stored, validated patch; the client
    cannot supply arbitrary file content or paths.
    """
    report = _load_report(db, request.report_id, current_user)
    details = report.details_dict()
    patch = details.get("patch") or {}
    if patch.get("status") != "generated" or not patch.get("new_content") or not patch.get("file_path"):
        raise HTTPException(status_code=400, detail="This report has no validated patch to apply.")
    if report.fix_pr_url:
        return serialize_report(report)

    github = _client(current_user)
    repo, run_id = report.repository, int(report.run_id)
    try:
        run = await github.get_workflow_run(repo, run_id)
        base_branch, head_sha = run.get("head_branch"), run.get("head_sha")
        if not base_branch or not head_sha:
            raise HTTPException(status_code=400, detail="Could not determine branch or commit SHA from run.")

        branch = f"rootcause-fix-{run_id}"
        try:
            await github.create_branch(repo, branch, head_sha)
        except httpx.HTTPStatusError as e:
            if "already exists" not in e.response.text:
                raise HTTPException(status_code=502, detail=f"Failed to create branch: {e.response.text}")

        commit = await github.create_or_update_file(
            repo=repo, file_path=patch["file_path"],
            message=f"fix: resolve pipeline failure in {patch['file_path']}\n\n{patch.get('summary') or ''}",
            content=patch["new_content"], branch=branch,
        )
        fix_sha = (commit.get("commit") or {}).get("sha")

        existing = await github.find_open_pull_request(repo, branch)
        if existing:
            pr = existing
        else:
            best = (details.get("candidates") or [{}])[0]
            evidence = "\n".join(f"- **{e['signal']}:** {e['explanation']}" for e in details.get("evidence_chain", []))
            body = (
                f"## Root Cause CI automated fix\n\n"
                f"Generated for failing workflow run #{run_id} (job `{report.job_name}`).\n\n"
                f"**Root cause:** {patch.get('summary') or report.llm_summary}\n\n"
                f"**Most likely culprit commit:** `{str(best.get('commit_sha', ''))[:7]}` "
                f"({details.get('confidence_score', 0):.0%} confidence)\n\n"
                f"**Evidence:**\n{evidence or '- none recorded'}\n\n"
                f"> This change is verified automatically: Root Cause CI marks it verified only when the "
                f"repository's CI passes on this branch. Please review before merging."
            )
            pr = await github.create_pull_request(
                repo=repo, title=f"Fix pipeline failure in {patch['file_path']} (run #{run_id})",
                body=body, head=branch, base=base_branch,
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e.response.text}")

    report.fix_branch = branch
    report.fix_commit_sha = fix_sha
    report.fix_pr_url = pr.get("html_url")
    report.fix_pr_number = pr.get("number")
    report.verification_status = "pending"
    db.commit()
    db.refresh(report)
    return serialize_report(report)


@router.get("/{report_id}/verification")
async def check_verification(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    """Check the CI result of the fix branch and store the verdict on the report."""
    report = _load_report(db, report_id, current_user)
    if not report.fix_branch:
        raise HTTPException(status_code=400, detail="No fix pull request has been created for this report.")
    github = _client(current_user)
    try:
        runs = await github.list_runs_for_branch(report.repository, report.fix_branch, per_page=20)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"GitHub API error: {e.response.text}")
    verdict = verification_from_runs(runs, report.fix_commit_sha)
    report.verification_status = verdict["status"]
    details = report.details_dict()
    details["verification"] = verdict
    report.details = json.dumps(details, default=str)
    db.commit()
    db.refresh(report)
    return serialize_report(report)
