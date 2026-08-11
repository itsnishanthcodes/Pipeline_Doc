from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.services.pipeline_analyzer import PipelineAnalyzer

# We need the user from the token to get their github_token
# Using the same auth verification logic (we can just create a simple dependency)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token
from app.models.user import User
from sqlalchemy import select

router = APIRouter(prefix="/analysis", tags=["analysis"])
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


class AnalysisRequest(BaseModel):
    repository: str
    run_id: int


@router.post("/github")
async def analyze_github_pipeline(
    request: AnalysisRequest,
    db: Session = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id)
):
    try:
        analyzer = PipelineAnalyzer(db)
        result = await analyzer.analyze_pipeline(request.repository, request.run_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/history")
def get_analysis_history(
    db: Session = Depends(get_db_session),
    user_id: int = Depends(get_current_user_id)
):
    from app.models.analysis_report import AnalysisReport
    reports = db.scalars(
        select(AnalysisReport)
        .where(AnalysisReport.user_id == user_id)
        .order_by(AnalysisReport.created_at.desc())
    ).all()

    history = []
    for r in reports:
        history.append({
            "run_id": r.run_id,
            "job_name": r.job_name,
            "is_healthy": r.is_healthy,
            "pr_title": r.pr_title,
            "pr_number": r.pr_number,
            "author": r.author,
            "classification": {
                "category": r.category,
                "explanation": r.explanation
            },
            "comment_posted": r.comment_posted,
            "llm_summary": r.llm_summary,
            "report_preview": r.report_body,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "repository": r.repository,
        })

    return {"reports": history}
