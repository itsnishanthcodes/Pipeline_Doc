from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FailureLocalizationRecord(Base):
    __tablename__ = "failure_localizations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_report_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_reports.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exception_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exception_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_test: Mapped[str | None] = mapped_column(String(500), nullable=True)
    frames_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CandidateCommitRecord(Base):
    __tablename__ = "candidate_commits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_report_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_reports.id"), index=True, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    components_json: Mapped[str] = mapped_column(Text, nullable=False)
    changed_files_json: Mapped[str] = mapped_column(Text, nullable=False)
    changed_lines_json: Mapped[str] = mapped_column(Text, nullable=False)


class EvidenceItemRecord(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_report_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_reports.id"), index=True, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    relevance: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    supports: Mapped[str | None] = mapped_column(Text, nullable=True)


class DependencyPathRecord(Base):
    __tablename__ = "dependency_paths"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_report_id: Mapped[int] = mapped_column(Integer, ForeignKey("analysis_reports.id"), index=True, nullable=False)
    path_json: Mapped[str] = mapped_column(Text, nullable=False)