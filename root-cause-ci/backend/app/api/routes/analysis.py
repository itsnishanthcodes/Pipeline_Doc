import json
from pathlib import Path

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
from app.models.analysis_report import AnalysisReport
from app.models.rca import CandidateCommitRecord, DependencyPathRecord, EvidenceItemRecord, FailureLocalizationRecord
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


def _owned_report(db: Session, report_id: int, user_id: int) -> AnalysisReport:
    report = db.scalar(
        select(AnalysisReport).where(
            AnalysisReport.id == report_id,
            AnalysisReport.user_id == user_id,
        )
    )
    if not report:
        raise HTTPException(status_code=404, detail="Analysis report not found")
    return report


@router.get("/{report_id}/localization")
def get_localization(report_id: int, db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    _owned_report(db, report_id, user_id)
    record = db.scalar(select(FailureLocalizationRecord).where(FailureLocalizationRecord.analysis_report_id == report_id))
    if not record:
        raise HTTPException(status_code=404, detail="Failure localization not available")
    return {
        "status": record.status,
        "reason": record.reason,
        "exception_type": record.exception_type,
        "exception_message": record.exception_message,
        "failed_test": record.failed_test,
        "frames": json.loads(record.frames_json),
    }


@router.get("/{report_id}/candidates")
def get_candidates(report_id: int, db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    _owned_report(db, report_id, user_id)
    records = db.scalars(select(CandidateCommitRecord).where(CandidateCommitRecord.analysis_report_id == report_id)).all()
    return {"candidates": [{
        "commit_sha": record.commit_sha,
        "subject": record.subject,
        "score": record.score,
        "components": json.loads(record.components_json),
        "changed_files": json.loads(record.changed_files_json),
        "changed_lines": json.loads(record.changed_lines_json),
    } for record in records]}


@router.get("/{report_id}/attribution")
def get_attribution(report_id: int, db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    _owned_report(db, report_id, user_id)
    records = db.scalars(
        select(CandidateCommitRecord)
        .where(CandidateCommitRecord.analysis_report_id == report_id)
        .order_by(CandidateCommitRecord.score.desc())
    ).all()
    return {"root_cause": ({
        "commit_sha": records[0].commit_sha,
        "score": records[0].score,
        "components": json.loads(records[0].components_json),
    } if records else None)}


@router.get("/{report_id}/evidence")
def get_evidence(report_id: int, db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    _owned_report(db, report_id, user_id)
    records = db.scalars(select(EvidenceItemRecord).where(EvidenceItemRecord.analysis_report_id == report_id)).all()
    return {"evidence": [{
        "type": record.evidence_type,
        "source": record.source,
        "description": record.description,
        "value": json.loads(record.value_json),
        "relevance": record.relevance,
        "location": record.location,
        "supports": record.supports,
    } for record in records]}


@router.get("/{report_id}/graph")
def get_dependency_paths(report_id: int, db: Session = Depends(get_db_session), user_id: int = Depends(get_current_user_id)):
    _owned_report(db, report_id, user_id)
    records = db.scalars(select(DependencyPathRecord).where(DependencyPathRecord.analysis_report_id == report_id)).all()
    return {"paths": [json.loads(record.path_json) for record in records]}


@router.get("/evaluation/latest")
def get_latest_evaluation() -> dict:
    result_path = Path(__file__).resolve().parents[3] / "benchmark_results" / "latest.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="No benchmark results have been generated")
    return json.loads(result_path.read_text(encoding="utf-8"))
