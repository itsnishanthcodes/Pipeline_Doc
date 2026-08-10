from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.classification import FailureClassification, FlakyAnalysis


class PipelineRun(BaseModel):
    id: str
    repository: str
    workflow: str
    branch: str | None = None
    commit_sha: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    status: str


class Job(BaseModel):
    id: str
    name: str
    status: str
    conclusion: str | None = None


class Failure(BaseModel):
    id: str
    pipeline_id: str
    job_id: str
    failure_type: str
    test_name: str | None = None
    error_message: str | None = None
    stack_trace: str | None = None
    file_path: str | None = None
    line_number: int | None = None
    commit_sha: str | None = None
    timestamp: datetime | None = None


class ErrorSignature(BaseModel):
    name: str
    pattern: str
    matched_text: str | None = None


class IngestionResult(BaseModel):
    pipeline_run: PipelineRun
    job: Job
    failure: Failure | None = None
    classification: FailureClassification | None = None
    flaky_analysis: FlakyAnalysis | None = None
    error_signatures: list[ErrorSignature] = Field(default_factory=list)


class WebhookIngestionResponse(BaseModel):
    status: str
    delivery_id: str | None = None
    event_type: str | None = None
    ingestion: IngestionResult
