from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db_session
from app.models.analysis_report import AnalysisReport
from app.models.user import User
from app.services.pipeline_analyzer import PipelineAnalyzer
from app.services.report_serializer import serialize_report

router = APIRouter(prefix="/analysis", tags=["analysis"])


class AnalysisRequest(BaseModel):
    repository: str = Field(pattern=r"^[\w.-]+/[\w.-]+$")
    run_id: int = Field(gt=0)


@router.post("/github")
async def analyze_github_pipeline(
    request: AnalysisRequest,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    try:
        return await PipelineAnalyzer(db).analyze_pipeline(request.repository, request.run_id, user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@router.get("/history")
def get_analysis_history(db: Session = Depends(get_db_session), user: User = Depends(get_current_user)):
    reports = db.scalars(
        select(AnalysisReport).where(AnalysisReport.user_id == user.id).order_by(AnalysisReport.created_at.desc())
    ).all()
    return {"reports": [serialize_report(r) for r in reports]}


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db_session), user: User = Depends(get_current_user)):
    report = db.get(AnalysisReport, report_id)
    if not report or report.user_id != user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return serialize_report(report)
