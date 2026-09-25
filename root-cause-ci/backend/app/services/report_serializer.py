from __future__ import annotations

from typing import Any

from app.models.analysis_report import AnalysisReport


def serialize_report(report: AnalysisReport) -> dict[str, Any]:
    """Single JSON shape for an analysis report, used by analysis, history and verification endpoints."""
    d = report.details_dict()
    classification = {
        "category": report.category,
        "explanation": report.explanation,
        "confidence": d.get("classification_confidence"),
    }
    return {
        "report_id": report.id,
        "repository": report.repository,
        "run_id": report.run_id,
        "job_name": report.job_name,
        "branch": report.branch,
        "source": report.source or "manual",
        "is_healthy": report.is_healthy,
        "classification": classification,
        "llm_summary": report.llm_summary,
        "report_preview": report.report_body,
        "pr_title": report.pr_title,
        "pr_number": report.pr_number,
        "author": report.author,
        "comment_posted": report.comment_posted,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "run": d.get("run"),
        "jobs": d.get("jobs", []),
        "primary_job": d.get("primary_job"),
        "flaky": d.get("flaky"),
        "base_sha": d.get("base_sha"),
        "candidates": d.get("candidates", []),
        "evidence_chain": d.get("evidence_chain", []),
        "confidence_score": d.get("confidence_score"),
        "target_file": d.get("target_file"),
        "patch": d.get("patch"),
        "warnings": d.get("warnings", []),
        "fix_pr_url": report.fix_pr_url,
        "fix_pr_number": report.fix_pr_number,
        "fix_branch": report.fix_branch,
        "verification_status": report.verification_status,
        "verification": d.get("verification"),
    }
