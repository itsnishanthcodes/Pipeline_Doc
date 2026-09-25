from app.schemas.ingestion import Failure
from app.services.classification.failure_classifier import FailureClassifier
from evaluation.run_evaluation import run_scenario, summarize
from evaluation.scenarios import SCENARIOS


def test_runtime_exception_in_test_is_a_regression():
    failure = Failure(id="1", pipeline_id="p", job_id="j", failure_type="UNKNOWN", commit_sha="abc",
                      error_message="E   ZeroDivisionError: division by zero\nFAILED tests/test_orders.py::test_discount")
    assert FailureClassifier().classify(failure).category == "CODE_REGRESSION"


def test_evaluation_attribution_beats_latest_commit_baseline():
    summary = summarize([run_scenario(sc) for sc in SCENARIOS])
    top1, total = summary["attribution_top1"]
    baseline, _ = summary["baseline_latest_commit_top1"]
    assert total >= 8
    assert top1 > baseline
    assert summary["flaky_false_positives"][0] == 0
