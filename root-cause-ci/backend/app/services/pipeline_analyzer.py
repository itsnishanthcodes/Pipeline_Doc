"""End-to-end, evidence-first analysis of a failed GitHub Actions workflow run.

Deterministic stages (log parsing, classification, flaky scoring, commit attribution, evidence)
always run first; the LLM is only asked for a patch after that evidence exists.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.github_client import GitHubClient
from app.models.analysis_report import AnalysisReport
from app.models.user import User
from app.schemas.classification import FlakyAnalysis, FlakyEvidenceItem
from app.schemas.ingestion import Failure
from app.services.analysis.log_analysis import StackFrame, analyze_log, is_test_path, resolve_repo_path
from app.services.ast.parser import ASTParser
from app.services.attribution.scorer import AttributionScorer
from app.services.attribution.signals import (
    CandidateCommit,
    CommitFile,
    SignalInputs,
    imported_modules,
    module_matches_path,
    score_signals,
)
from app.services.classification.failure_classifier import get_failure_classifier
from app.services.evidence.generator import EvidenceGenerator
from app.services.flaky.detector import FlakyTestDetector, TestHistoryStore
from app.services.github_tokens import github_token_for
from app.services.patch.patch_service import choose_target_file, generate_patch
from app.services.report_serializer import serialize_report

FAILED_CONCLUSIONS = ("failure", "timed_out")
MAX_JOBS = 5
MAX_CANDIDATES = 10
HISTORY_RUNS = 10
MAX_AST_FILES = 8


class PipelineAnalyzer:
    def __init__(self, db: Session):
        self.db = db
        self.classifier = get_failure_classifier()

    # ================================================================== public entry point
    async def analyze_pipeline(
        self, repo: str, run_id: int, user_id: int, source: str = "manual", post_comment: bool = True
    ) -> dict[str, Any]:
        repo = repo.strip()
        user = self.db.scalar(select(User).where(User.id == user_id))
        github = GitHubClient(github_token_for(user))
        warnings: list[str] = []

        try:
            run = await github.get_workflow_run(repo, run_id)
        except Exception as exc:
            raise ValueError(
                f"Could not fetch GitHub run #{run_id} for repo '{repo}'. Check repo name and permissions. ({exc})"
            ) from exc

        status, conclusion = run.get("status"), run.get("conclusion")
        branch, head_sha = run.get("head_branch"), run.get("head_sha")
        run_info = {
            "id": run_id, "url": run.get("html_url"), "workflow": run.get("name"), "branch": branch,
            "head_sha": head_sha, "run_number": run.get("run_number"), "event": run.get("event"),
            "conclusion": conclusion, "run_attempt": run.get("run_attempt"),
        }

        if status != "completed":
            raise ValueError(f"Run #{run_id} is still '{status}'. Analyse it after it has completed.")
        if conclusion == "success":
            return self._save_healthy(repo, run_id, user_id, branch, source, run_info)

        jobs = await github.get_jobs_for_run(repo, run_id)
        failed_jobs = [j for j in jobs if j.get("conclusion") in FAILED_CONCLUSIONS]
        if not failed_jobs:
            return {"message": f"No failed jobs found for this run (conclusion: {conclusion}).",
                    "status": status, "conclusion": conclusion}

        # ---------------------------------------------------------- 1. every failed job: logs, parsing, classification
        job_results = await asyncio.gather(*[self._analyze_job(github, repo, run_id, head_sha, j)
                                             for j in failed_jobs[:MAX_JOBS]])
        if len(failed_jobs) > MAX_JOBS:
            warnings.append(f"{len(failed_jobs)} jobs failed; only the first {MAX_JOBS} were analysed.")
        primary = next((j for j in job_results if j["classification"].category == "CODE_REGRESSION"), job_results[0])
        log = primary["log"]

        # ---------------------------------------------------------- 2. repository tree and repo-relative frames
        try:
            tree = await github.get_tree_paths(repo, head_sha)
        except Exception as exc:
            tree = []
            warnings.append(f"Could not read the repository tree: {exc}")
        frames = self._resolve_frames(log.frames, tree)
        failing_tests = self._failing_test_files(log.failed_tests, frames, tree)

        # ---------------------------------------------------------- 3. run history: flaky score, last green commit
        history = await self._job_history(github, repo, run, primary["name"], warnings)
        flaky = self._flaky_analysis(primary["name"], history)

        # ---------------------------------------------------------- 4. candidate commits since the last green run
        candidates = await self._candidate_commits(github, repo, history["base_sha"], head_sha, warnings)

        # ---------------------------------------------------------- 5. code evidence: AST, test imports, blame
        test_sources = await self._fetch_many(github, repo, head_sha, failing_tests[:3])
        functions_by_file = await self._functions_by_file(github, repo, head_sha, candidates, frames, test_sources)
        blame_frame = self._blame_frame(frames)
        blame_sha = None
        if blame_frame:
            blame_sha = await github.blame_line(repo, head_sha, blame_frame.file, blame_frame.line)

        inputs = SignalInputs(
            frames=frames,
            log_text=log.clean_log[-20000:],
            functions_by_file=functions_by_file,
            test_sources=test_sources,
            blame_sha=blame_sha,
            newly_failing=history["newly_failing"],
        )
        scored = AttributionScorer().score_candidates(score_signals(candidates, inputs)) if candidates else []
        best = scored[0] if scored else None
        evidence = EvidenceGenerator().generate_chain(best) if best else []
        confidence = best["confidence_score"] if best else 0.0

        # ---------------------------------------------------------- 6. constrained patch (skipped for flaky failures)
        test_imports: set[str] = set()
        for src in test_sources.values():
            test_imports |= imported_modules(src)
        imported_changed = [p for p in (best["changed_files"] if best else [])
                            if not is_test_path(p) and any(module_matches_path(m, p) for m in test_imports)]
        target = choose_target_file(frames, best, imported_changed)
        if flaky.classification == "LIKELY_FLAKY":
            patch = {"status": "skipped", "file_path": None, "summary": None, "new_content": None, "diff": None,
                     "reason": "The failure looks flaky, so no code change is proposed. Re-run the job to confirm."}
        else:
            original = None
            if target:
                try:
                    original = await github.get_file_content(repo, target, head_sha)
                except Exception as exc:
                    warnings.append(f"Could not read {target}: {exc}")
            culprit_patch = None
            if best:
                for c in candidates:
                    if c.sha == best["commit_sha"]:
                        culprit_patch = next((f.patch for f in c.files if f.path == target), None)
            patch = await generate_patch(
                repo=repo, run_id=run_id, target_file=target, original=original,
                error_lines=log.key_lines, evidence=evidence, culprit_patch=culprit_patch,
                category=primary["classification"].category, allowed_scope={target} if target else set(),
            )

        # ---------------------------------------------------------- 7. pull request context and PR comment
        pr_title = pr_number = None
        author = (best or {}).get("author") or (user.github_username if user else None)
        prs = []
        try:
            prs = await github.get_pull_requests_for_commit(repo, head_sha)
        except Exception:
            prs = []
        if prs:
            pr_title, pr_number = prs[0].get("title"), prs[0].get("number")

        classification = primary["classification"]
        llm_summary = patch.get("summary") or (
            f"The '{primary['name']}' job failed. {classification.explanation}"
            + (f" The most likely cause is commit {best['commit_sha'][:7]}." if best else "")
        )
        report_body = self._markdown_report(run_id, primary, classification, flaky, best, evidence, confidence,
                                            llm_summary, patch)
        comment_posted = False
        if prs and post_comment:
            try:
                await github.post_pr_comment(repo, pr_number, report_body)
                comment_posted = True
            except Exception as exc:
                warnings.append(f"Could not comment on PR #{pr_number}: {exc}")

        details = {
            "run": run_info,
            "jobs": [self._job_summary(j) for j in job_results],
            "primary_job": primary["name"],
            "classification_confidence": classification.confidence,
            "flaky": {**flaky.model_dump(), "same_commit_passed": history["same_commit_passed"],
                      "runs_considered": len(history["outcomes"])},
            "base_sha": history["base_sha"],
            "newly_failing": history["newly_failing"],
            "candidates": scored,
            "evidence_chain": evidence,
            "confidence_score": confidence,
            "target_file": target,
            "patch": patch,
            "warnings": warnings,
        }
        report = AnalysisReport(
            user_id=user_id, repository=repo, run_id=str(run_id), job_name=primary["name"],
            category=classification.category, explanation=classification.explanation, is_healthy=False,
            comment_posted=comment_posted, llm_summary=llm_summary, report_body=report_body,
            pr_title=pr_title, pr_number=pr_number, author=author, source=source, branch=branch,
            details=json.dumps(details, default=str),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return serialize_report(report)

    # ================================================================== stages
    async def _analyze_job(self, github: GitHubClient, repo: str, run_id: int, head_sha: str, job: dict) -> dict:
        try:
            raw = await github.get_job_logs(repo, job["id"])
        except Exception:
            raw = ""
        log = analyze_log(raw)
        failure = Failure(
            id=f"{run_id}:{job['id']}", pipeline_id=str(run_id), job_id=str(job["id"]), failure_type="UNKNOWN",
            test_name=log.failed_tests[0] if log.failed_tests else None,
            error_message="\n".join(log.key_lines)[-4000:], commit_sha=head_sha,
        )
        classification = self.classifier.classify(failure, "\n".join(log.key_lines))
        failed_step = next((s.get("name") for s in job.get("steps", []) if s.get("conclusion") == "failure"), None)
        return {"id": job["id"], "name": job.get("name", "job"), "conclusion": job.get("conclusion"),
                "html_url": job.get("html_url"), "failed_step": failed_step, "log": log,
                "classification": classification, "log_available": bool(raw)}

    @staticmethod
    def _job_summary(j: dict) -> dict:
        c = j["classification"]
        return {
            "id": j["id"], "name": j["name"], "conclusion": j["conclusion"], "html_url": j["html_url"],
            "failed_step": j["failed_step"], "log_available": j["log_available"],
            "category": c.category, "confidence": c.confidence, "explanation": c.explanation, "signals": c.signals,
            "error_message": j["log"].error_message, "failed_tests": j["log"].failed_tests[:10],
            "error_signatures": j["log"].error_signatures,
            "frames": [{"file": f.file, "line": f.line, "function": f.function} for f in j["log"].frames[:15]],
            "key_lines": j["log"].key_lines[-20:],
        }

    @staticmethod
    def _resolve_frames(frames: list[StackFrame], tree: list[str]) -> list[StackFrame]:
        out: list[StackFrame] = []
        seen = set()
        for f in frames:
            path = resolve_repo_path(f.file, tree) if tree else f.file
            if path and (path, f.line) not in seen:
                seen.add((path, f.line))
                out.append(StackFrame(file=path, line=f.line, function=f.function))
        return out

    @staticmethod
    def _failing_test_files(failed_tests: list[str], frames: list[StackFrame], tree: list[str]) -> list[str]:
        files: list[str] = []
        for t in failed_tests:
            path = resolve_repo_path(t.split("::", 1)[0], tree) if tree else t.split("::", 1)[0]
            if path and path not in files:
                files.append(path)
        for f in frames:
            if is_test_path(f.file) and f.file not in files:
                files.append(f.file)
        return files

    async def _job_history(self, github: GitHubClient, repo: str, run: dict, job_name: str,
                           warnings: list[str]) -> dict:
        """Outcomes of the same job in earlier runs of this workflow on the same branch."""
        result = {"outcomes": [], "base_sha": None, "newly_failing": False, "same_commit_passed": False}
        workflow_id, branch = run.get("workflow_id"), run.get("head_branch")
        if not workflow_id:
            return result
        try:
            runs = await github.list_workflow_runs(repo, workflow_id, branch=branch, per_page=30)
        except Exception as exc:
            warnings.append(f"Could not read workflow history: {exc}")
            return result
        current_no = run.get("run_number") or 0
        prior = sorted(
            (r for r in runs if r.get("status") == "completed" and (r.get("run_number") or 0) < current_no),
            key=lambda r: r.get("run_number") or 0,
        )
        greens = [r for r in prior if r.get("conclusion") == "success"]
        if greens:
            result["base_sha"] = greens[-1].get("head_sha")
        if prior:
            result["newly_failing"] = prior[-1].get("conclusion") == "success"
        result["same_commit_passed"] = any(
            r.get("head_sha") == run.get("head_sha") and r.get("conclusion") == "success" and r.get("id") != run.get("id")
            for r in runs
        )

        recent = prior[-HISTORY_RUNS:]

        async def outcome(r: dict) -> str | None:
            try:
                jobs = await github.get_jobs_for_run(repo, r["id"])
            except Exception:
                return None
            job = next((j for j in jobs if j.get("name") == job_name), None)
            if not job:
                return None
            if job.get("conclusion") == "success":
                return "PASS"
            if job.get("conclusion") in FAILED_CONCLUSIONS:
                return "FAIL"
            return None

        outcomes = await asyncio.gather(*[outcome(r) for r in recent])
        result["outcomes"] = [o for o in outcomes if o]
        return result

    @staticmethod
    def _flaky_analysis(job_name: str, history: dict) -> FlakyAnalysis:
        detector = FlakyTestDetector(TestHistoryStore())
        for o in history["outcomes"]:
            detector.record_run(job_name, outcome=o)
        detector.record_run(job_name, outcome="FAIL")
        analysis = detector.analyze(job_name)
        if len(history["outcomes"]) < 3 and not history["same_commit_passed"]:
            analysis.classification = "INSUFFICIENT_HISTORY"
        if history["same_commit_passed"]:
            analysis.evidence.append(FlakyEvidenceItem(
                signal="same_commit_passed", observed_value="yes", score_contribution=0.4,
                explanation="Another run of the same commit passed, so the code itself can succeed.",
            ))
            analysis.flaky_probability = min(1.0, round(analysis.flaky_probability + 0.4, 3))
            analysis.classification = "LIKELY_FLAKY" if analysis.flaky_probability >= 0.7 else "POSSIBLY_FLAKY"
        return analysis

    async def _candidate_commits(self, github: GitHubClient, repo: str, base_sha: str | None, head_sha: str,
                                 warnings: list[str]) -> list[CandidateCommit]:
        shas = [head_sha]
        if base_sha and base_sha != head_sha:
            try:
                cmp = await github.compare_commits(repo, base_sha, head_sha)
                shas = [c["sha"] for c in cmp.get("commits", [])][-MAX_CANDIDATES:] or [head_sha]
            except Exception as exc:
                warnings.append(f"Could not compare {base_sha[:7]}...{head_sha[:7]}: {exc}")

        async def load(sha: str) -> CandidateCommit | None:
            try:
                data = await github.get_commit(repo, sha)
            except Exception:
                return None
            info = data.get("commit", {})
            author = (data.get("author") or {}).get("login") or (info.get("author") or {}).get("name")
            files = [CommitFile(path=f["filename"], patch=f.get("patch"), status=f.get("status", "modified"))
                     for f in data.get("files", [])]
            return CandidateCommit(sha=sha, message=info.get("message", ""), author=author,
                                   date=(info.get("author") or {}).get("date"), files=files)

        loaded = await asyncio.gather(*[load(s) for s in shas])
        return [c for c in loaded if c is not None]

    async def _fetch_many(self, github: GitHubClient, repo: str, ref: str, paths: list[str]) -> dict[str, str]:
        async def one(p: str):
            try:
                return p, await github.get_file_content(repo, p, ref)
            except Exception:
                return p, None
        pairs = await asyncio.gather(*[one(p) for p in paths])
        return {p: c for p, c in pairs if c is not None}

    async def _functions_by_file(self, github: GitHubClient, repo: str, ref: str, candidates: list[CandidateCommit],
                                 frames: list[StackFrame], test_sources: dict[str, str]) -> dict[str, list[dict]]:
        frame_files = {f.file for f in frames}
        imports: set[str] = set()
        for src in test_sources.values():
            imports |= imported_modules(src)
        py_files: list[str] = []
        for c in reversed(candidates):  # newest first so the most relevant files win the cap
            for f in c.files:
                if f.path.endswith(".py") and f.status != "removed" and f.path not in py_files:
                    py_files.append(f.path)
        py_files.sort(key=lambda p: (p not in frame_files, not any(module_matches_path(m, p) for m in imports)))
        contents = await self._fetch_many(github, repo, ref, py_files[:MAX_AST_FILES])
        parser = ASTParser()
        out = {}
        for path, src in contents.items():
            try:
                out[path] = parser.parse_code(src)["functions"]
            except Exception:
                out[path] = []
        return out

    @staticmethod
    def _blame_frame(frames: list[StackFrame]) -> StackFrame | None:
        source = [f for f in frames if not is_test_path(f.file)]
        if source:
            return source[-1]
        return frames[-1] if frames else None

    # ================================================================== reports
    def _save_healthy(self, repo: str, run_id: int, user_id: int, branch: str | None, source: str,
                      run_info: dict) -> dict:
        body = (
            f"## Healthy Pipeline Report\n\n**Pipeline Run:** #{run_id} | **Repository:** `{repo}`\n"
            f"**Status:** `SUCCESS`\n\nAll workflow jobs in this run completed successfully."
        )
        report = AnalysisReport(
            user_id=user_id, repository=repo, run_id=str(run_id), job_name="all-jobs-passed", category="HEALTHY",
            explanation="All workflow jobs in this pipeline run completed successfully.", is_healthy=True,
            comment_posted=False, llm_summary="Pipeline run is healthy and all jobs passed.", report_body=body,
            source=source, branch=branch, details=json.dumps({"run": run_info}, default=str),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return serialize_report(report)

    @staticmethod
    def _markdown_report(run_id, primary, classification, flaky, best, evidence, confidence, summary, patch) -> str:
        lines = [
            "## Root Cause CI Analysis Report", "",
            f"**Pipeline Run:** #{run_id} | **Job:** `{primary['name']}`", "",
            "### Classification",
            f"- **Category:** `{classification.category}` ({classification.confidence:.0%} confidence)",
            f"- **Rule signal:** {classification.explanation}",
            f"- **Flaky-test verdict:** {flaky.classification} ({flaky.flaky_probability:.0%})", "",
        ]
        if primary["log"].error_message:
            lines += ["### Error", f"```\n{primary['log'].error_message}\n```", ""]
        if best:
            lines += [
                "### Root Cause Attribution",
                f"**Most likely commit:** `{best['commit_sha'][:7]}` {best.get('message', '')} "
                f"(by {best.get('author') or 'unknown'}), confidence **{confidence:.1%}**", "",
                "**Evidence chain:**",
            ]
            lines += [f"- **{e['signal']}:** {e['explanation']}" for e in evidence] or ["- No strong signals."]
            lines.append("")
        lines += ["### Summary", summary, ""]
        if patch.get("status") == "generated" and patch.get("diff"):
            lines += [f"### Proposed Fix for `{patch['file_path']}`", f"```diff\n{patch['diff'][:6000]}\n```"]
        elif patch.get("reason"):
            lines += ["### Proposed Fix", f"No patch: {patch['reason']}"]
        return "\n".join(lines)
