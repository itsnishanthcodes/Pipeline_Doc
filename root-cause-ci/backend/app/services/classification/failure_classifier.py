from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.schemas.classification import FailureClassification
from app.schemas.ingestion import Failure


@dataclass(slots=True)
class ClassificationRule:
    category: str
    confidence: float
    signal: str
    explanation: str


class FailureClassifier:
    def classify(self, failure: Failure, log_text: str | None = None) -> FailureClassification:
        signals: list[str] = []
        rule = self._apply_rules(failure, log_text or failure.error_message or "")
        if rule is None:
            return FailureClassification(
                category="UNKNOWN",
                confidence=0.25,
                signals=["insufficient_deterministic_signals"],
                explanation="No deterministic failure signals were strong enough for a reliable classification.",
            )

        signals.append(rule.signal)
        return FailureClassification(
            category=rule.category,
            confidence=rule.confidence,
            signals=signals,
            explanation=rule.explanation,
        )

    def _apply_rules(self, failure: Failure, text: str) -> ClassificationRule | None:
        lowered = text.lower()
        candidates: list[ClassificationRule] = []

        if "environment variable" in lowered or "not set" in lowered:
            candidates.append(
                ClassificationRule(
                    category="CONFIGURATION_FAILURE",
                    confidence=0.96,
                    signal="missing_environment_variable",
                    explanation="The failure text references a missing or unset environment variable.",
                )
            )
        if "docker daemon" in lowered or "cannot connect to the docker daemon" in lowered or "docker: command not found" in lowered:
            candidates.append(
                ClassificationRule(
                    category="INFRASTRUCTURE_FAILURE",
                    confidence=0.97,
                    signal="docker_unavailable",
                    explanation="The failure text indicates Docker is unavailable or unreachable in the execution environment.",
                )
            )
        if "no matching distribution found" in lowered or "could not find a version that satisfies" in lowered:
            candidates.append(
                ClassificationRule(
                    category="DEPENDENCY_FAILURE",
                    confidence=0.95,
                    signal="package_installation_failed",
                    explanation="The failure text shows an installation or dependency resolution error.",
                )
            )
        if "module not found" in lowered or "modulenotfounderror" in lowered:
            candidates.append(
                ClassificationRule(
                    category="DEPENDENCY_FAILURE",
                    confidence=0.92,
                    signal="missing_runtime_dependency",
                    explanation="The failure text shows a missing import or runtime dependency.",
                )
            )
        if "pytest" in lowered and "failed" in lowered and failure.commit_sha:
            candidates.append(
                ClassificationRule(
                    category="CODE_REGRESSION",
                    confidence=0.84,
                    signal="test_failure_after_code_change",
                    explanation="The failing test appears after a code change and the text looks like an assertion-driven failure.",
                )
            )
        if "assertionerror" in lowered or "assert " in lowered or "expected" in lowered and "got" in lowered:
            candidates.append(
                ClassificationRule(
                    category="CODE_REGRESSION",
                    confidence=0.9,
                    signal="assertion_failure",
                    explanation="The failure text contains an assertion-style mismatch typical of a code regression.",
                )
            )

        if not candidates:
            return None

        return max(candidates, key=lambda candidate: candidate.confidence)


_service = FailureClassifier()


def get_failure_classifier() -> FailureClassifier:
    return _service
