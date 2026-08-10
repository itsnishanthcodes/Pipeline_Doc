from __future__ import annotations

from pydantic import BaseModel, Field


class FailureClassification(BaseModel):
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    explanation: str


class FlakyEvidenceItem(BaseModel):
    signal: str
    observed_value: str
    score_contribution: float = Field(ge=0.0, le=1.0)
    explanation: str


class FlakyAnalysis(BaseModel):
    flaky_probability: float = Field(ge=0.0, le=1.0)
    classification: str
    evidence: list[FlakyEvidenceItem] = Field(default_factory=list)
    historical_runs: list[str] = Field(default_factory=list)
