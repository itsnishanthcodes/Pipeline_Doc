from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from app.schemas.classification import FailureClassification, FlakyAnalysis
from app.schemas.ingestion import Failure, IngestionResult, Job, PipelineRun
from app.services.classification.failure_classifier import FailureClassifier, get_failure_classifier
from app.services.flaky.detector import FlakyTestDetector, get_flaky_test_detector
from app.services.ingestion.log_parser import (
    extract_error_signatures,
    extract_failed_test_name,
    extract_stack_trace,
    first_non_empty,
)
from app.services.git.analysis import get_git_analysis_service
from app.schemas.git import GitAnalysisResult


@dataclass(slots=True)
class StoredIngestionEvent:
    event_type: str
    delivery_id: str | None
    payload: dict[str, Any]
    result: IngestionResult
    recorded_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class InMemoryIngestionStore:
    def __init__(self) -> None:
        self._items: list[StoredIngestionEvent] = []
        self._lock = Lock()

    def save(self, event: StoredIngestionEvent) -> None:
        with self._lock:
            self._items.append(event)

    def latest(self) -> StoredIngestionEvent | None:
        with self._lock:
            return self._items[-1] if self._items else None

    def all(self) -> list[StoredIngestionEvent]:
        with self._lock:
            return list(self._items)


class GitHubActionsIngestionService:
    def __init__(
        self,
        store: InMemoryIngestionStore | None = None,
        classifier: FailureClassifier | None = None,
        flaky_detector: FlakyTestDetector | None = None,
    ) -> None:
        self._store = store or InMemoryIngestionStore()
        self._classifier = classifier or get_failure_classifier()
        self._flaky_detector = flaky_detector or get_flaky_test_detector()

    def ingest_event(self, event_type: str, delivery_id: str | None, payload: dict[str, Any]) -> IngestionResult:
        if event_type == "workflow_job":
            result = self._ingest_workflow_job(payload)
        else:
            result = self._ingest_workflow_run(payload)

        self._store.save(
            StoredIngestionEvent(
                event_type=event_type,
                delivery_id=delivery_id,
                payload=payload,
                result=result,
            )
        )
        return result

    def latest_event(self) -> StoredIngestionEvent | None:
        return self._store.latest()

    def _ingest_workflow_run(self, payload: dict[str, Any]) -> IngestionResult:
        repository = first_non_empty([
            payload.get("repository", {}).get("full_name"),
            payload.get("repository", {}).get("name"),
        ]) or "unknown/repository"
        workflow_run = payload.get("workflow_run", {})
        log_excerpt = first_non_empty([
            payload.get("log_excerpt"),
            workflow_run.get("log_excerpt"),
            workflow_run.get("conclusion_message"),
        ])
        pipeline = PipelineRun(
            id=str(workflow_run.get("id") or payload.get("id") or "unknown-run"),
            repository=repository,
            workflow=first_non_empty([workflow_run.get("name"), payload.get("workflow_name")]) or "unknown-workflow",
            branch=first_non_empty([workflow_run.get("head_branch"), payload.get("branch")]),
            commit_sha=first_non_empty([workflow_run.get("head_sha"), payload.get("commit_sha")]),
            started_at=self._parse_datetime(workflow_run.get("run_started_at") or payload.get("started_at")),
            finished_at=self._parse_datetime(workflow_run.get("updated_at") or payload.get("finished_at")),
            status=first_non_empty([workflow_run.get("status"), payload.get("status")]) or "unknown",
        )
        job = Job(
            id=str(workflow_run.get("id") or payload.get("id") or "unknown-job"),
            name=first_non_empty([workflow_run.get("name"), payload.get("job_name")]) or "workflow-run",
            status=first_non_empty([workflow_run.get("status"), payload.get("status")]) or "unknown",
            conclusion=first_non_empty([workflow_run.get("conclusion"), payload.get("conclusion")]),
        )
        failure = self._build_failure(pipeline, job, log_excerpt)
        classification, flaky_analysis, git_analysis = self._analyze_failure(failure, payload)
        if failure is not None and classification is not None:
            failure.failure_type = classification.category
        return IngestionResult(
            pipeline_run=pipeline,
            job=job,
            failure=failure,
            classification=classification,
            flaky_analysis=flaky_analysis,
            git_analysis=git_analysis,
            error_signatures=extract_error_signatures(log_excerpt),
        )

    def _ingest_workflow_job(self, payload: dict[str, Any]) -> IngestionResult:
        repository = first_non_empty([
            payload.get("repository", {}).get("full_name"),
            payload.get("repository", {}).get("name"),
        ]) or "unknown/repository"
        log_excerpt = first_non_empty([payload.get("log_excerpt"), payload.get("logs")])
        pipeline = PipelineRun(
            id=str(payload.get("workflow_run", {}).get("id") or payload.get("run_id") or payload.get("id") or "unknown-run"),
            repository=repository,
            workflow=first_non_empty([payload.get("workflow_name"), payload.get("workflow_run", {}).get("name")]) or "unknown-workflow",
            branch=first_non_empty([payload.get("workflow_run", {}).get("head_branch"), payload.get("branch")]),
            commit_sha=first_non_empty([payload.get("workflow_run", {}).get("head_sha"), payload.get("commit_sha")]),
            started_at=self._parse_datetime(payload.get("started_at")),
            finished_at=self._parse_datetime(payload.get("completed_at")),
            status=first_non_empty([payload.get("status"), payload.get("workflow_run", {}).get("status")]) or "unknown",
        )
        job = Job(
            id=str(payload.get("job_id") or payload.get("id") or "unknown-job"),
            name=first_non_empty([payload.get("name"), payload.get("job_name")]) or "workflow-job",
            status=first_non_empty([payload.get("status")]) or "unknown",
            conclusion=first_non_empty([payload.get("conclusion")]),
        )
        failure = self._build_failure(pipeline, job, log_excerpt)
        classification, flaky_analysis, git_analysis = self._analyze_failure(failure, payload)
        if failure is not None and classification is not None:
            failure.failure_type = classification.category
        return IngestionResult(
            pipeline_run=pipeline,
            job=job,
            failure=failure,
            classification=classification,
            flaky_analysis=flaky_analysis,
            git_analysis=git_analysis,
            error_signatures=extract_error_signatures(log_excerpt),
        )

    def _build_failure(self, pipeline: PipelineRun, job: Job, log_excerpt: str | None) -> Failure | None:
        if job.conclusion == "success" and pipeline.status == "completed":
            return None

        traceback_text, file_path, line_number = extract_stack_trace(log_excerpt)
        test_name = extract_failed_test_name(log_excerpt)
        error_message = first_non_empty([
            log_excerpt,
            job.conclusion,
        ])
        return Failure(
            id=f"{pipeline.id}:{job.id}",
            pipeline_id=pipeline.id,
            job_id=job.id,
            failure_type="UNKNOWN",
            test_name=test_name,
            error_message=error_message,
            stack_trace=traceback_text,
            file_path=file_path,
            line_number=line_number,
            commit_sha=pipeline.commit_sha,
            timestamp=pipeline.finished_at,
        )

    def _analyze_failure(self, failure: Failure | None, payload: dict[str, Any]) -> tuple[FailureClassification | None, FlakyAnalysis | None, GitAnalysisResult | None]:
        if failure is None:
            return None, None

        classification = self._classifier.classify(failure, failure.error_message)

        historical_runs = payload.get("historical_runs") or payload.get("test_history") or []
        if failure.test_name:
            for outcome in historical_runs:
                if isinstance(outcome, str) and outcome.strip():
                    self._flaky_detector.record_run(failure.test_name, outcome=outcome, commit_sha=failure.commit_sha)
            self._flaky_detector.record_run(failure.test_name, outcome="FAIL", commit_sha=failure.commit_sha)
            flaky_analysis = self._flaky_detector.analyze(failure.test_name)
        else:
            flaky_analysis = None

        # optional: perform git analysis if a local repo path is provided in the payload
        git_analysis = None
        try:
            local_path = payload.get("local_repo_path") or payload.get("repository_path")
            if local_path and failure.commit_sha:
                svc = get_git_analysis_service(local_path)
                git_analysis = svc.find_failure_path(
                    failing_commit_sha=failure.commit_sha,
                    previous_successful_commit_sha=payload.get("previous_successful_commit_sha"),
                    file_path=failure.file_path,
                    line_number=failure.line_number,
                )
        except Exception:
            git_analysis = None

        return classification, flaky_analysis, git_analysis

    def _parse_datetime(self, value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None


_service = GitHubActionsIngestionService()


def get_github_actions_ingestion_service() -> GitHubActionsIngestionService:
    return _service
