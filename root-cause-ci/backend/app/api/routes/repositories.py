from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db_session
from app.api.routes.analysis import get_current_user_id
from app.models.user import User
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.integrations.github_client import GitHubClient
from app.core.config import get_settings
import asyncio

router = APIRouter(prefix="/repositories", tags=["repositories"])

@router.get("")
async def list_repositories(
    db: Session = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id)
):
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    token = user.github_token or get_settings().github_token
    if not token:
        raise HTTPException(status_code=400, detail="No GitHub token available")
        
    github = GitHubClient(token)
    repos = await github.get_user_repositories()
    
    # Check top 30 recently updated to avoid too many API calls
    top_repos = repos[:30]
    
    async def _check_repo(repo):
        has_wf = await github.check_has_workflows(repo["full_name"])
        if has_wf:
            latest_run = await github.get_latest_workflow_run(repo["full_name"])
            latest_run_id = latest_run.get("id") if latest_run else None
            latest_run_status = latest_run.get("status") if latest_run else None
            latest_run_conclusion = latest_run.get("conclusion") if latest_run else None
            
            return {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description", ""),
                "html_url": repo["html_url"],
                "updated_at": repo["updated_at"],
                "latest_run_id": latest_run_id,
                "latest_run_status": latest_run_status,
                "latest_run_conclusion": latest_run_conclusion
            }
        return None

    results = await asyncio.gather(*[_check_repo(r) for r in top_repos])
    ci_repos = [r for r in results if r is not None]
    
    return {"repositories": ci_repos}

