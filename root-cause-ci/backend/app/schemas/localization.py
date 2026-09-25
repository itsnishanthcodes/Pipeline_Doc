from __future__ import annotations

from pydantic import BaseModel, Field


class StackFrame(BaseModel):
    file_path: str
    line_number: int
    function: str | None = None
    raw: str


class FailureLocalization(BaseModel):
    status: str = "PARTIAL"
    reason: str | None = None
    exception_type: str | None = None
    exception_message: str | None = None
    failed_test: str | None = None
    frames: list[StackFrame] = Field(default_factory=list)
