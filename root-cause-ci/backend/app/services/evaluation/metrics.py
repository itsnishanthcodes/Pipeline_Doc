from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class RCABenchmarkCase:
    expected_commit: str
    ranked_commits: list[str]
    evidence_available: int
    evidence_total: int
    files_analyzed: int
    graph_nodes_analyzed: int
    candidate_count: int
    duration_seconds: float
    functions_analyzed: int = 0
    localization_correct: bool | None = None
    dependency_path_correct: bool | None = None
    status: str = "SUPPORTED"


def calculate_rca_metrics(cases: list[RCABenchmarkCase]) -> dict[str, Any]:
    if not cases:
        return {
            "case_count": 0,
            "top_1_accuracy": None,
            "top_3_accuracy": None,
            "evidence_coverage": None,
            "average_files_analyzed": None,
            "average_graph_nodes_analyzed": None,
            "average_candidate_commits": None,
            "average_analysis_time_seconds": None,
            "localization_accuracy": None,
            "dependency_path_accuracy": None,
            "supported_cases": 0,
            "partial_cases": 0,
            "insufficient_evidence_cases": 0,
            "incorrect_cases": 0,
            "status": "NO_DATA",
        }

    top_1 = sum(bool(case.ranked_commits and case.ranked_commits[0] == case.expected_commit) for case in cases)
    top_3 = sum(case.expected_commit in case.ranked_commits[:3] for case in cases)
    coverage = [case.evidence_available / case.evidence_total for case in cases if case.evidence_total > 0]
    localization = [case.localization_correct for case in cases if case.localization_correct is not None]
    dependency = [case.dependency_path_correct for case in cases if case.dependency_path_correct is not None]
    return {
        "case_count": len(cases),
        "top_1_accuracy": round(top_1 / len(cases), 4),
        "top_3_accuracy": round(top_3 / len(cases), 4),
        "evidence_coverage": round(mean(coverage), 4) if coverage else None,
        "average_files_analyzed": round(mean(case.files_analyzed for case in cases), 3),
        "average_graph_nodes_analyzed": round(mean(case.graph_nodes_analyzed for case in cases), 3),
        "average_functions_analyzed": round(mean(case.functions_analyzed for case in cases), 3),
        "average_candidate_commits": round(mean(case.candidate_count for case in cases), 3),
        "average_analysis_time_seconds": round(mean(case.duration_seconds for case in cases), 4),
        "localization_accuracy": round(sum(localization) / len(localization), 4) if localization else None,
        "dependency_path_accuracy": round(sum(dependency) / len(dependency), 4) if dependency else None,
        "supported_cases": sum(case.status == "SUPPORTED" for case in cases),
        "partial_cases": sum(case.status == "PARTIAL" for case in cases),
        "insufficient_evidence_cases": sum(case.status == "INSUFFICIENT_EVIDENCE" for case in cases),
        "incorrect_cases": sum(case.status == "INCORRECT" for case in cases),
        "status": "COMPUTED",
    }