from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CommitMetadata(BaseModel):
    commit_sha: str
    author_name: str
    author_email: str
    timestamp: datetime
    parents: list[str] = Field(default_factory=list)
    subject: str


class BlameResult(BaseModel):
    file_path: str
    line_number: int
    commit_sha: str
    author_name: str
    author_email: str
    timestamp: datetime
    summary: str


class ChangedLine(BaseModel):
    file_path: str
    line_number: int
    change_type: str


class CommitCandidate(BaseModel):
    commit_sha: str
    author: str
    timestamp: datetime
    changed_files: list[str] = Field(default_factory=list)
    changed_functions: list[str] = Field(default_factory=list)
    changed_lines: list[int] = Field(default_factory=list)
    diff: str = ""
    subject: str = ""
    temporal_score: float = Field(default=0.0, ge=0.0, le=1.0)
    file_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    function_overlap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    line_overlap_score: float | None = Field(default=None, ge=0.0, le=1.0)
    diff_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    blame_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rank_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_components: dict[str, dict[str, object]] = Field(default_factory=dict)


class GitAnalysisResult(BaseModel):
    repository_path: str
    failing_commit: CommitMetadata
    previous_successful_commit: CommitMetadata | None = None
    changed_files: list[str] = Field(default_factory=list)
    changed_lines: list[ChangedLine] = Field(default_factory=list)
    blame: BlameResult | None = None
    candidates: list[CommitCandidate] = Field(default_factory=list)
