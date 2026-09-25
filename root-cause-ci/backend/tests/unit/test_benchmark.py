from pathlib import Path

from app.services.evaluation.benchmark import run_controlled_benchmark


def test_controlled_benchmark_runs_forty_real_git_cases(tmp_path: Path) -> None:
    result = run_controlled_benchmark(tmp_path / "benchmark.json")

    assert result["case_count"] == 40
    assert result["baselines"]["logs_only"]["top_1_accuracy"] == 0.0
    assert result["baselines"]["logs_git"]["top_1_accuracy"] >= 0.95
    assert result["baselines"]["full_proposed"]["top_3_accuracy"] == 1.0
    assert set(result["baselines"]) == {"logs_only", "logs_git", "logs_git_ast", "logs_git_ast_graph", "full_proposed"}
    assert Path(tmp_path / "benchmark.json").exists()