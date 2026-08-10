from app.schemas.ingestion import Failure
from app.services.classification.failure_classifier import FailureClassifier


def test_failure_classifier_detects_configuration_failure() -> None:
    classifier = FailureClassifier()
    failure = Failure(
        id="1",
        pipeline_id="p1",
        job_id="j1",
        failure_type="unknown",
        error_message="Required environment variable DATABASE_URL is not set",
        commit_sha=None,
    )

    result = classifier.classify(failure)

    assert result.category == "CONFIGURATION_FAILURE"
    assert result.confidence >= 0.9
    assert "missing_environment_variable" in result.signals


def test_failure_classifier_detects_code_regression() -> None:
    classifier = FailureClassifier()
    failure = Failure(
        id="2",
        pipeline_id="p2",
        job_id="j2",
        failure_type="unknown",
        error_message="AssertionError: expected 1 but got 0",
        commit_sha="abc123",
    )

    result = classifier.classify(failure)

    assert result.category == "CODE_REGRESSION"
    assert result.confidence >= 0.85
    assert "assertion_failure" in result.signals
