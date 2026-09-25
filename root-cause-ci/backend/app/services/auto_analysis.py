"""Automatic analysis triggered by GitHub webhooks."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_session_factory, init_db
from app.models.analysis_report import AnalysisReport
from app.models.user import User
from app.services.pipeline_analyzer import PipelineAnalyzer

logger = logging.getLogger(__name__)


def users_for_repository(db: Session, repository: str) -> list[int]:
    """Users linked to a repository: its owner by GitHub username, or anyone who analysed it before."""
    owner = repository.split("/", 1)[0].lower()
    ids = set(db.scalars(select(User.id).where(func.lower(User.github_username) == owner)).all())
    ids |= set(db.scalars(select(AnalysisReport.user_id).where(AnalysisReport.repository == repository)).all())
    return sorted(ids)


def should_auto_analyze(event_type: str | None, payload: dict) -> tuple[str, int] | None:
    """Return (repository, run_id) when the event is a completed, failed workflow run."""
    if event_type != "workflow_run" or payload.get("action") not in (None, "completed"):
        return None
    run = payload.get("workflow_run") or {}
    repository = (payload.get("repository") or {}).get("full_name")
    if run.get("status") != "completed" or run.get("conclusion") not in ("failure", "timed_out"):
        return None
    if not repository or not isinstance(run.get("id"), int):
        return None
    return repository, run["id"]


async def auto_analyze(repository: str, run_id: int) -> None:
    """Background task: analyse the run once for every linked user that has not analysed it yet."""
    # Startup creates tables in a background thread; make sure that has finished before querying.
    init_db()
    db = get_session_factory()()
    try:
        for user_id in users_for_repository(db, repository):
            exists = db.scalar(select(AnalysisReport.id).where(
                AnalysisReport.user_id == user_id,
                AnalysisReport.repository == repository,
                AnalysisReport.run_id == str(run_id),
            ))
            if exists:
                continue
            try:
                await PipelineAnalyzer(db).analyze_pipeline(repository, run_id, user_id, source="webhook")
            except Exception:
                logger.exception("Automatic analysis failed for %s run %s (user %s)", repository, run_id, user_id)
                db.rollback()
    finally:
        db.close()
