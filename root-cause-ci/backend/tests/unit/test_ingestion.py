from app.services.ingestion.github_actions import GitHubActionsIngestionService


def test_ingestion_extracts_failure_signatures() -> None:
    service = GitHubActionsIngestionService()
    payload = {
        "repository": {"full_name": "acme/shopping-app"},
        "workflow_run": {
            "id": 123,
            "name": "CI",
            "head_branch": "main",
            "head_sha": "abc123",
            "status": "completed",
            "conclusion": "failure",
            "run_started_at": "2026-08-09T10:00:00Z",
            "updated_at": "2026-08-09T10:05:00Z",
        },
        "historical_runs": ["PASS", "FAIL", "PASS", "FAIL", "PASS"],
        "log_excerpt": "Traceback (most recent call last):\nAssertionError: expected 1 but got 0\nFile \"src/auth/service.py\", line 42, in validate_token\nFAILED tests/test_auth.py::test_invalid_token",
    }

    result = service.ingest_event("workflow_run", "delivery-1", payload)

    assert result.pipeline_run.repository == "acme/shopping-app"
    assert result.job.conclusion == "failure"
    assert result.failure is not None
    assert result.failure.failure_type == "CODE_REGRESSION"
    assert result.failure.test_name == "tests/test_auth.py::test_invalid_token"
    assert result.failure.file_path == "src/auth/service.py"
    assert result.failure.line_number == 42
    assert len(result.error_signatures) >= 2
    assert result.classification is not None
    assert result.classification.category == "CODE_REGRESSION"
    assert result.flaky_analysis is not None
    assert result.flaky_analysis.classification in {"POSSIBLY_FLAKY", "LIKELY_FLAKY"}

