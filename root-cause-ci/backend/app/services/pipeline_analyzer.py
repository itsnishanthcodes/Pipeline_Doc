from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.integrations.github_client import GitHubClient
from app.services.classification.failure_classifier import get_failure_classifier
from app.services.llm_service import generate_llm_summary
from app.schemas.ingestion import Failure
from app.models.user import User
from app.models.analysis_report import AnalysisReport


class PipelineAnalyzer:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = get_failure_classifier()

    async def analyze_pipeline(self, repo: str, run_id: int, user_id: int) -> Dict[str, Any]:
        repo = repo.strip()
        user = self.db.scalar(select(User).where(User.id == user_id))
        if not user or not user.github_token:
            raise ValueError("User not found or GitHub token missing")

        github = GitHubClient(user.github_token)

        # 1. Fetch workflow run
        try:
            run_data = await github.get_workflow_run(repo, run_id)
        except Exception as e:
            raise ValueError(f"Could not fetch GitHub run #{run_id} for repo '{repo}'. Check repo name and permissions. ({e})")

        status = run_data.get("status")
        conclusion = run_data.get("conclusion")

        # 2. Check if healthy / successful
        if status == "completed" and conclusion == "success":
            healthy_report = (
                f"## ✅ Healthy Pipeline Report\n\n"
                f"**Pipeline Run:** #{run_id} | **Repository:** `{repo}`\n"
                f"**Status:** `SUCCESS` (Healthy)\n\n"
                f"### 🟢 Status Summary\n"
                f"All workflow jobs in this pipeline execution completed successfully. "
                f"No regressions, failures, or errors were detected."
            )
            report_record = AnalysisReport(
                user_id=user_id,
                repository=repo,
                run_id=str(run_id),
                job_name="all-jobs-passed",
                category="HEALTHY",
                explanation="All workflow jobs in this pipeline run completed successfully.",
                is_healthy=True,
                comment_posted=False,
                llm_summary="✅ Pipeline run is healthy and all tests passed cleanly.",
                report_body=healthy_report,
            )
            self.db.add(report_record)
            self.db.commit()

            return {
                "run_id": run_id,
                "job_name": "all-jobs-passed",
                "is_healthy": True,
                "classification": {
                    "category": "HEALTHY",
                    "explanation": "All workflow jobs in this pipeline run completed successfully."
                },
                "comment_posted": False,
                "llm_summary": "✅ Pipeline run is healthy and all tests passed cleanly.",
                "report_preview": healthy_report
            }

        # 3. Get failed jobs
        failed_jobs = await github.get_failed_jobs(repo, run_id)
        if not failed_jobs:
            return {"message": "No failed jobs found for this pipeline run", "status": status, "conclusion": conclusion}
        
        target_job = failed_jobs[0]
        job_id = target_job["id"]
        job_name = target_job["name"]

        # 3. Get job logs
        try:
            log_text = await github.get_job_logs(repo, job_id)
        except Exception:
            log_text = "Could not fetch job logs."

        # 4. Classify Failure
        failure = Failure(
            id=f"{run_id}:{job_id}",
            pipeline_id=str(run_id),
            job_id=str(job_id),
            failure_type="UNKNOWN",
            error_message=log_text[-2000:],  # Pass last 2000 chars as excerpt
            commit_sha=run_data.get("head_sha")
        )
        
        classification = self.classifier.classify(failure, log_text)

        # 5. Fetch PR and changed files
        commit_sha = run_data.get("head_sha")
        pr_title = None
        pr_number = None
        author = user.github_username or "Unknown Developer"
        changed_files = []
        try:
            prs = await github.get_pull_requests_for_commit(repo, commit_sha)
            if prs:
                target_pr = prs[0]
                pr_title = target_pr.get("title")
                pr_number = target_pr.get("number")
                author = (target_pr.get("user") or {}).get("login", author)
                changed_files = await github.get_pull_request_changes(repo, pr_number)
        except Exception:
            prs = []

        # 6. Generate LLM Narrative Summary
        llm_narrative = await generate_llm_summary(
            failure_log=log_text,
            category=classification.category,
            explanation=classification.explanation,
            repo=repo,
            run_id=run_id,
            pr_title=pr_title,
            changed_files=changed_files,
        )

        report_body = (
            f"## 🔍 Orbit Root Cause & Impact Analysis Report\n\n"
            f"**Pipeline Run:** #{run_id} | **Job:** `{job_name}`\n\n"
            f"### 🤖 AI Failure Summary\n"
            f"{llm_narrative}\n\n"
            f"### 📊 Classification Details\n"
            f"- **Error Category:** `{classification.category}`\n"
            f"- **Rule Signal:** {classification.explanation}\n\n"
            f"### 📝 Log Excerpt\n```\n{log_text[-1000:] if len(log_text) > 1000 else log_text}\n```\n"
        )

        comment_posted = False
        if prs:
            pr_number = prs[0]["number"]
            try:
                await github.post_pr_comment(repo, pr_number, report_body)
                comment_posted = True
            except Exception:
                pass

        report_record = AnalysisReport(
            user_id=user_id,
            repository=repo,
            run_id=str(run_id),
            job_name=job_name,
            category=classification.category,
            explanation=classification.explanation,
            is_healthy=False,
            comment_posted=comment_posted,
            llm_summary=llm_narrative,
            report_body=report_body,
            pr_title=pr_title,
            pr_number=pr_number,
            author=author,
        )
        self.db.add(report_record)
        self.db.commit()

        return {
            "run_id": run_id,
            "job_name": job_name,
            "is_healthy": False,
            "pr_title": pr_title,
            "pr_number": pr_number,
            "author": author,
            "changed_files": changed_files,
            "classification": {
                "category": classification.category,
                "explanation": classification.explanation
            },
            "comment_posted": comment_posted,
            "llm_summary": llm_narrative,
            "report_preview": report_body
        }
