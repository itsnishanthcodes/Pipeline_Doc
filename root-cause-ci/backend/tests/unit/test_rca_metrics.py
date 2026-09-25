from app.services.evaluation.metrics import RCABenchmarkCase, calculate_rca_metrics


def test_rca_metrics_calculate_top1_top3_and_coverage() -> None:
    metrics = calculate_rca_metrics([
        RCABenchmarkCase("B", ["B", "A", "C"], 4, 5, 3, 8, 3, 0.2),
        RCABenchmarkCase("C", ["A", "B", "C"], 2, 4, 2, 5, 3, 0.4),
    ])

    assert metrics["top_1_accuracy"] == 0.5
    assert metrics["top_3_accuracy"] == 1.0
    assert metrics["evidence_coverage"] == 0.65
    assert metrics["status"] == "COMPUTED"


def test_rca_metrics_do_not_fabricate_empty_results() -> None:
    metrics = calculate_rca_metrics([])
    assert metrics["status"] == "NO_DATA"
    assert metrics["top_1_accuracy"] is None