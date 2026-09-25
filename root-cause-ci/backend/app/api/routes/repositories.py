import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_current_user
from app.integrations.github_client import GitHubClient
from app.models.user import User
from app.services.github_tokens import github_token_for

router = APIRouter(prefix="/repositories", tags=["repositories"])

NAME = r"^[\w.-]+$"


def _client_for(user: User) -> GitHubClient:
    token = github_token_for(user)
    if not token:
        raise HTTPException(status_code=400, detail="Connect a GitHub token in Settings to list your repositories.")
    return GitHubClient(token)


def _github_error(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code in (401, 403):
        return HTTPException(status_code=400, detail="GitHub rejected your token. Update it in Settings.")
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="GitHub could not find that repository, or your token cannot see it.")
    return HTTPException(status_code=502, detail=f"GitHub returned an error ({exc.response.status_code}).")


@router.get("")
async def list_repositories(user: User = Depends(get_current_user)):
    github = _client_for(user)
    try:
        repos = await github.get_user_repositories()
    except httpx.HTTPStatusError as exc:
        raise _github_error(exc)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="GitHub could not be reached. Try again in a moment.")

    async def describe(repo: dict):
        if not await github.check_has_workflows(repo["full_name"]):
            return None
        latest = await github.get_latest_workflow_run(repo["full_name"])
        return {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo.get("description") or "",
            "html_url": repo["html_url"],
            "private": repo.get("private", False),
            "updated_at": repo["updated_at"],
            "default_branch": repo.get("default_branch"),
            "latest_run_id": latest.get("id") if latest else None,
            "latest_run_status": latest.get("status") if latest else None,
            "latest_run_conclusion": latest.get("conclusion") if latest else None,
            "latest_run_name": latest.get("name") if latest else None,
            "latest_run_at": latest.get("updated_at") if latest else None,
        }

    # the 30 most recently updated repositories keep the number of API calls reasonable
    results = await asyncio.gather(*[describe(r) for r in repos[:30]])
    return {"repositories": [r for r in results if r is not None]}


@router.get("/{owner}/{name}/runs")
async def list_runs(
    owner: str = Path(pattern=NAME),
    name: str = Path(pattern=NAME),
    user: User = Depends(get_current_user),
):
    """Recent workflow runs of a repository, newest first, for picking a run to analyse."""
    github = _client_for(user)
    try:
        workflow_runs = await github.list_recent_runs(f"{owner}/{name}")
    except httpx.HTTPStatusError as exc:
        raise _github_error(exc)
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="GitHub could not be reached. Try again in a moment.")
    runs = [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "run_number": r.get("run_number"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "branch": r.get("head_branch"),
            "head_sha": r.get("head_sha"),
            "commit_message": next(iter(((r.get("head_commit") or {}).get("message") or "").splitlines()), "")[:120],
            "actor": (r.get("actor") or {}).get("login"),
            "event": r.get("event"),
            "created_at": r.get("created_at"),
            "html_url": r.get("html_url"),
        }
        for r in workflow_runs
    ]
    return {"repository": f"{owner}/{name}", "runs": runs}
