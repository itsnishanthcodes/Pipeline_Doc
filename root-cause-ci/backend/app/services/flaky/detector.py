from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from app.schemas.classification import FlakyAnalysis, FlakyEvidenceItem


@dataclass(slots=True)
class TestRunRecord:
    outcome: str
    commit_sha: str | None = None


@dataclass(slots=True)
class TestHistoryStore:
    _history: dict[str, list[TestRunRecord]] = field(default_factory=dict)

    def add_run(self, test_name: str, outcome: str, commit_sha: str | None = None) -> None:
        self._history.setdefault(test_name, []).append(TestRunRecord(outcome=outcome.upper(), commit_sha=commit_sha))

    def get_runs(self, test_name: str) -> list[TestRunRecord]:
        return list(self._history.get(test_name, []))


class FlakyTestDetector:
    def __init__(self, store: TestHistoryStore | None = None) -> None:
        self._store = store or TestHistoryStore()

    def record_run(self, test_name: str, outcome: str, commit_sha: str | None = None) -> None:
        self._store.add_run(test_name, outcome=outcome, commit_sha=commit_sha)

    def analyze(self, test_name: str) -> FlakyAnalysis:
        runs = self._store.get_runs(test_name)
        if not runs:
            return FlakyAnalysis(
                flaky_probability=0.0,
                classification="INSUFFICIENT_HISTORY",
                evidence=[],
                historical_runs=[],
            )

        outcomes = [run.outcome.upper() for run in runs]
        failure_count = sum(1 for outcome in outcomes if outcome == "FAIL")
        pass_count = sum(1 for outcome in outcomes if outcome == "PASS")
        transitions = sum(1 for left, right in zip(outcomes, outcomes[1:]) if left != right)
        # Interleaving means the test failed and later passed again (a recovery), not merely that a
        # long green history ends in its first failure, which is what a genuine regression looks like.
        recovered = any(a == "FAIL" and "PASS" in outcomes[i + 1:] for i, a in enumerate(outcomes))
        intermittent = 1.0 if recovered else 0.0
        failure_rate = failure_count / len(outcomes)
        transition_rate = transitions / max(len(outcomes) - 1, 1)
        repeat_failure_signal = 1.0 if self._has_consecutive_failures(outcomes) else 0.0

        score_breakdown = [
            FlakyEvidenceItem(
                signal="failure_rate",
                observed_value=f"{failure_count}/{len(outcomes)}",
                score_contribution=round(failure_rate * 0.45, 3),
                explanation="Higher historical failure rate increases flaky probability.",
            ),
            FlakyEvidenceItem(
                signal="pass_fail_interleaving",
                observed_value=f"{pass_count} passes, {failure_count} fails, {transitions} transitions",
                score_contribution=round(intermittent * 0.35, 3),
                explanation="Interleaved passing and failing runs indicate intermittent behavior.",
            ),
            FlakyEvidenceItem(
                signal="transition_rate",
                observed_value=f"{transitions}/{max(len(outcomes) - 1, 1)} transitions",
                score_contribution=round(transition_rate * 0.25, 3),
                explanation="Frequent outcome changes across runs are a strong flaky-test signal.",
            ),
            FlakyEvidenceItem(
                signal="consecutive_failures",
                observed_value="present" if repeat_failure_signal else "absent",
                score_contribution=round(repeat_failure_signal * 0.10, 3),
                explanation="Consecutive failures strengthen the evidence that the test is unstable.",
            ),
        ]

        flaky_probability = min(
            1.0,
            round(
                score_breakdown[0].score_contribution
                + score_breakdown[1].score_contribution
                + score_breakdown[2].score_contribution
                + score_breakdown[3].score_contribution,
                3,
            ),
        )
        if flaky_probability >= 0.7:
            classification = "LIKELY_FLAKY"
        elif flaky_probability >= 0.4:
            classification = "POSSIBLY_FLAKY"
        else:
            classification = "LIKELY_STABLE"

        return FlakyAnalysis(
            flaky_probability=flaky_probability,
            classification=classification,
            evidence=score_breakdown,
            historical_runs=outcomes,
        )

    def _has_consecutive_failures(self, outcomes: Iterable[str]) -> bool:
        last = None
        for outcome in outcomes:
            if outcome == "FAIL" and last == "FAIL":
                return True
            last = outcome
        return False


_service = FlakyTestDetector()


def get_flaky_test_detector() -> FlakyTestDetector:
    return _service
