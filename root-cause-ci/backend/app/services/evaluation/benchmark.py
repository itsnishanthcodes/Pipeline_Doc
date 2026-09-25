from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from app.services.ast.project import PythonProjectAnalyzer
from app.services.git.analysis import GitAnalysisService
from app.services.ingestion.log_parser import localize_failure
from app.services.evaluation.metrics import RCABenchmarkCase, calculate_rca_metrics


@dataclass(frozen=True)
class ControlledCase:
    case_id: str
    failure_type: str
    failing_test: str
    failure_log: str
    expected_root_cause_commit: str
    affected_file: str
    affected_function: str
    expected_dependency_path: list[str]
    repository_state: str
    failure_inducing_commit: str
    stack_line: int | None
    expected_status: str = "SUPPORTED"
    expected_evidence: list[str] = None


@dataclass(frozen=True)
class CaseReport:
    case_id: str
    failure_type: str
    expected_commit: str
    top_candidate: str | None
    top_3_candidates: list[str]
    dependency_path: list[str]
    evidence: list[dict[str, object]]
    status: str
    confidence: float | None
    evidence_coverage: float
    files_analyzed: int
    functions_analyzed: int
    graph_nodes: int
    candidate_count: int
    analysis_time_seconds: float
    configuration: str = "full_proposed"


def run_controlled_benchmark(output_path: str | Path | None = None) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    configuration_names = ("logs_only", "logs_git", "logs_git_ast", "logs_git_ast_graph", "full_proposed")
    baseline_cases: dict[str, list[RCABenchmarkCase]] = {name: [] for name in configuration_names}
    for index in range(40):
        with tempfile.TemporaryDirectory(prefix=f"rca-case-{index:02d}-") as temp_dir:
            case, base_commit, failing_commit = _create_case(Path(temp_dir), index)
            localized = localize_failure(case.failure_log)
            case_results: dict[str, object] = {"case_id": case.case_id, "expected_root_cause": case.expected_root_cause_commit, "expected_status": case.expected_status, "failure_type": case.failure_type, "failure_log": case.failure_log, "affected_file": case.affected_file, "affected_function": case.affected_function, "expected_dependency_path": case.expected_dependency_path, "repository_state": case.repository_state, "failure_inducing_commit": case.failure_inducing_commit, "baselines": {}}
            for configuration in configuration_names:
                started = time.perf_counter()
                git_result = None
                ranked: list[str] = []
                if configuration != "logs_only":
                    git_result = GitAnalysisService(Path(temp_dir)).analyze_failure(failing_commit, base_commit, case.affected_file, case.stack_line)
                    ranked = [candidate.commit_sha for candidate in git_result.candidates]
                source_files = [case.affected_file, "tests/test_checkout.py", "src/service.py", "src/analytics.py"]
                project = None
                path: list[str] = []
                if configuration in {"logs_git_ast", "logs_git_ast_graph", "full_proposed"}:
                    project = PythonProjectAnalyzer(Path(temp_dir)).analyze(source_files, test_file="tests/test_checkout.py", test_name="test_checkout_total", max_depth=4, max_files=12, max_import_expansion=8)
                    if configuration in {"logs_git_ast_graph", "full_proposed"} and project.paths:
                        path = max(project.paths, key=len)
                evidence = _evidence_for(case, localized, git_result, path) if git_result else [{"type": "STACK_OVERLAP", "status": "COMPUTED" if localized.frames else "UNAVAILABLE", "value": bool(localized.frames)}, {"type": "FUNCTION_OVERLAP", "status": "UNAVAILABLE", "value": None}, {"type": "DEPENDENCY_PATH", "status": "UNAVAILABLE", "value": None}]
                top = git_result.candidates[0] if git_result and git_result.candidates else None
                elapsed = round(time.perf_counter() - started, 6)
                status = _case_status(case, top.commit_sha if top else None, localized, path, evidence)
                functions = project.functions_analyzed if project else 0
                files = len(project.files_analyzed) if project else (len(git_result.changed_files) if git_result else 0)
                nodes = project.graph.number_of_nodes() if project and configuration in {"logs_git_ast_graph", "full_proposed"} else 0
                localization_correct = bool(localized.frames) == (case.stack_line is not None)
                dependency_correct = bool(path) == bool(case.expected_dependency_path) if configuration in {"logs_git_ast_graph", "full_proposed"} else None
                baseline_cases[configuration].append(RCABenchmarkCase(case.expected_root_cause_commit, ranked, sum(item["status"] == "COMPUTED" for item in evidence), len(evidence), files, nodes, len(ranked), elapsed, functions, localization_correct, dependency_correct, status))
                case_results["baselines"][configuration] = {"top_candidate": top.commit_sha if top else None, "top_3": ranked[:3], "dependency_path": path, "evidence": evidence, "status": status, "confidence": top.rank_score if top else None, "analysis_time_seconds": elapsed, "files_analyzed": files, "functions_analyzed": functions, "graph_nodes": nodes, "candidate_count": len(ranked)}
            reports.append(case_results)

    result = {
        "benchmark_version": "2026-09-23-ablation-v1",
        "case_count": len(reports),
        "baselines": {name: calculate_rca_metrics(cases) for name, cases in baseline_cases.items()},
        "cases": reports,
    }
    if output_path:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _create_case(root: Path, index: int) -> tuple[ControlledCase, str, str]:
    _git(root, "init")
    _git(root, "config", "user.name", "RCA Benchmark")
    _git(root, "config", "user.email", "rca@example.com")
    for directory in (root / "src", root / "tests"):
        directory.mkdir(parents=True, exist_ok=True)
    _write(root / "src" / "analytics.py", "def calculate_total():\n    return 100\n")
    _write(root / "src" / "service.py", "from src.analytics import calculate_total\n\ndef checkout():\n    return calculate_total()\n")
    _write(root / "tests" / "test_checkout.py", "from src.service import checkout\n\ndef test_checkout_total():\n    assert checkout() == 10\n")
    base = _commit(root, "base repository")
    expected = _commit(root, f"failure-inducing change case-{index:02d}", {"src/analytics.py": f"def calculate_total():\n    return {index + 1}\n"})
    if index % 3 == 0:
        _commit(root, "recent unrelated README change", {"README.md": "unrelated\n"})
    elif index % 3 == 1:
        _commit(root, "same file unrelated function", {"src/analytics.py": f"def calculate_total():\n    return {index + 1}\n\ndef helper():\n    return 1\n"})
    else:
        _commit(root, "unrelated API change", {"src/api.py": "def unrelated_api():\n    return True\n"})
    failing = _git(root, "rev-parse", "HEAD")
    missing_stack = index % 10 == 8
    unresolved = index % 10 == 9
    line = None if missing_stack else 2
    log = "FAILED tests/test_checkout.py::test_checkout_total\nAssertionError: expected 10 but got 1"
    if not missing_stack:
        log = f'Traceback (most recent call last):\n  File "src/analytics.py", line 2, in calculate_total\nAssertionError: expected 10 but got {index + 1}\n' + log
    if unresolved:
        log += "\nNameError: name 'missing_function' is not defined"
    case = ControlledCase(
        case_id=f"case-{index + 1:02d}",
        failure_type="NO_STACK_TRACE" if missing_stack else ("UNRESOLVED_DEPENDENCY" if unresolved else "CODE_REGRESSION"),
        failing_test="tests/test_checkout.py::test_checkout_total",
        failure_log=log,
        expected_root_cause_commit=expected,
        affected_file="src/analytics.py",
        affected_function="calculate_total",
        expected_dependency_path=["tests.test_checkout::test_checkout_total", "src.service::checkout", "src.analytics::calculate_total"],
        repository_state=failing,
        failure_inducing_commit=expected,
        stack_line=line,
        expected_status="PARTIAL" if missing_stack or unresolved else "SUPPORTED",
        expected_evidence=["CHANGED_LINE", "BLAME"] if missing_stack else ["STACK_OVERLAP", "CHANGED_LINE", "BLAME"],
    )
    return case, base, failing


def _evidence_for(case, localized, git_result, path):
    candidate = git_result.candidates[0] if git_result.candidates else None
    return [
        {"type": "STACK_OVERLAP", "status": "COMPUTED" if case.stack_line and candidate and candidate.line_overlap_score is not None else "UNAVAILABLE", "value": candidate.line_overlap_score if candidate else None},
        {"type": "FUNCTION_OVERLAP", "status": "COMPUTED" if candidate else "UNAVAILABLE", "value": candidate.function_overlap_score if candidate else None},
        {"type": "CHANGED_LINE", "status": "COMPUTED" if candidate and candidate.changed_lines else "UNAVAILABLE", "value": candidate.changed_lines if candidate else None},
        {"type": "BLAME", "status": "COMPUTED" if git_result.blame else "UNAVAILABLE", "value": git_result.blame.commit_sha if git_result.blame else None},
        {"type": "DEPENDENCY_PATH", "status": "COMPUTED" if path else "UNAVAILABLE", "value": path or None},
        {"type": "HISTORICAL", "status": "UNAVAILABLE", "value": None},
    ]


def _case_status(case, top, localized, path, evidence):
    if not top or not any(item["status"] == "COMPUTED" for item in evidence):
        return "INSUFFICIENT_EVIDENCE"
    if top != case.expected_root_cause_commit:
        return "INCORRECT"
    if localized.status != "COMPLETE" or not path:
        return "PARTIAL"
    return "SUPPORTED"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def _commit(root: Path, message: str, files: dict[str, str] | None = None) -> str:
    for relative, content in (files or {}).items():
        _write(root / relative, content)
    _git(root, "add", ".")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")