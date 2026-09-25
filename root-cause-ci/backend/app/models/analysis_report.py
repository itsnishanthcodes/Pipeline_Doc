from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    repository: Mapped[str] = mapped_column(String(255), nullable=False)
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    job_name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=False)
    comment_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_body: Mapped[str] = mapped_column(Text, nullable=False)
    pr_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # Phase 1 additions: full analysis payload, fix pull request and its verification status
    source: Mapped[str | None] = mapped_column(String(20), nullable=True, default="manual")
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    fix_pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    fix_pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fix_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fix_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    def details_dict(self) -> dict[str, Any]:
        if not self.details:
            return {}
        try:
            return json.loads(self.details)
        except ValueError:
            return {}
