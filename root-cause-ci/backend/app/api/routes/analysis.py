from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import decode_token
from app.models.analysis_report import AnalysisReport
from app.services.pipeline_analyzer import PipelineAnalyzer
from app.services.report_serializer import serialize_report

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
    user_id: int = Depends(get_current_user_id),
):
    try:
        return await PipelineAnalyzer(db).analyze_pipeline(request.repository, request.run_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/history")
def get_analysis_history(db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    reports = db.scalars(
        select(AnalysisReport).where(AnalysisReport.user_id == user_id).order_by(AnalysisReport.created_at.desc())
    ).all()
    return {"reports": [serialize_report(r) for r in reports]}


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    report = db.get(AnalysisReport, report_id)
    if not report or report.user_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize_report(report)
