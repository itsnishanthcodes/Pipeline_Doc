from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.integrations.github_client import GitHubClient
from app.services.classification.failure_classifier import get_failure_classifier
from app.schemas.ingestion import Failure
from app.models.user import User
from app.models.analysis_report import AnalysisReport


class PipelineAnalyzer:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = get_failure_classifier()

    async def analyze_pipeline(self, repo: str, run_id: int, user_id: int) -> Dict[str, Any]:
        repo = repo.strip()
        from app.core.config import get_settings
        user = self.db.scalar(select(User).where(User.id == user_id))
        token = (user.github_token if user and user.github_token else None) or get_settings().github_token

        github = GitHubClient(token)

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

        # 6. Build Evidence Chain (Phase 3)
        from app.services.attribution.scorer import AttributionScorer
        from app.services.evidence.generator import EvidenceGenerator
        from app.services.ast.parser import ASTParser
        from app.services.graph.builder import GraphBuilder
        
        # Real Program Analysis
        ast_parser = ASTParser()
        graph = GraphBuilder()
        
        found_functions = []
        function_overlap_score = 0.0
        file_overlap_score = 0.0

        if changed_files:
            # Check for file overlap in logs
            for file_path in changed_files:
                graph.add_file(file_path)
                graph.add_commit_modification(commit_sha, file_path)
                
                # Simple file overlap heuristic
                if file_path.split("/")[-1] in log_text:
                    file_overlap_score += 1.0
                
                # Fetch code and parse AST if it's Python
                if file_path.endswith(".py"):
                    try:
                        content = await github.get_file_content(repo, file_path, commit_sha)
                        if content:
                            ast_data = ast_parser.parse_code(content)
                            for func in ast_data.get("functions", []):
                                func_name = func["name"]
                                found_functions.append(func_name)
                                graph.add_function(func_name, file_path)
                                graph.add_commit_modification(commit_sha, file_path, func_name)
                                
                                # Simple function overlap heuristic
                                if func_name in log_text:
                                    function_overlap_score += 1.0
                    except Exception as e:
                        pass
        
        # Normalize scores
        if changed_files:
            file_overlap_score = min(1.0, file_overlap_score / len(changed_files))
        if found_functions:
            function_overlap_score = min(1.0, function_overlap_score / len(found_functions))
            
        real_candidate = {
            "commit_sha": commit_sha,
            "changed_files": changed_files,
            "changed_functions": found_functions,
            "signals": {
                "temporal_proximity": 0.9,  # Would be derived from commit timestamp vs run timestamp
                "file_overlap": file_overlap_score,
                "stack_trace_overlap": function_overlap_score, # For MVP, tie these together
                "function_overlap": function_overlap_score,
                "dependency_relationship": 0.5 if function_overlap_score > 0 else 0.0
            }
        }
        
        scorer = AttributionScorer()
        scored_candidates = scorer.score_candidates([real_candidate])
        best_candidate = scored_candidates[0]
        
        evidence_gen = EvidenceGenerator()
        evidence_chain = evidence_gen.generate_chain(best_candidate)
        confidence = best_candidate.get("confidence_score", 0.0)

        # 7. Generate Constrained Patch (Phase 4)
        from app.services.llm_service import generate_constrained_patch
        patch_result = await generate_constrained_patch(
            failure_log=log_text,
            evidence_chain=evidence_chain,
            repo=repo,
            run_id=run_id,
            changed_files=changed_files,
        )
        
        llm_summary = patch_result.get("summary", "No summary generated.")
        patch_code = patch_result.get("patch")

        evidence_md = "\n".join([f"- **{e['signal']}**: {e['explanation']}" for e in evidence_chain])

        report_body = (
            f"## 🔍 Orbit Root Cause & Impact Analysis Report\n\n"
            f"**Pipeline Run:** #{run_id} | **Job:** `{job_name}`\n\n"
            f"### 🎯 Root Cause Attribution\n"
            f"**Confidence Score:** {confidence * 100:.1f}%\n\n"
            f"**Evidence Chain:**\n{evidence_md}\n\n"
            f"### 🤖 AI Failure Summary\n"
            f"{llm_summary}\n\n"
        )
        
        if patch_code:
            report_body += (
                f"### 🛠️ Proposed Fix (Constrained Scope)\n"
                f"```diff\n{patch_code}\n```\n\n"
            )

        report_body += (
            f"### 📊 Classification Details\n"
            f"- **Error Category:** `{classification.category}`\n"
            f"- **Rule Signal:** {classification.explanation}\n\n"
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
            llm_summary=llm_summary,
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
            "llm_summary": llm_summary,
            "report_preview": report_body,
            "evidence_chain": evidence_chain,
            "confidence_score": confidence,
            "patch_code": patch_code
        }
