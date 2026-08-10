from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_github_webhook_accepts_workflow_run_event() -> None:
    payload = {
        "repository": {"full_name": "acme/shopping-app"},
        "workflow_run": {
            "id": 123,
            "name": "CI",
            "head_branch": "main",
            "head_sha": "abc123",
            "status": "completed",
            "conclusion": "failure",
        },
        "log_excerpt": "AssertionError: expected 1 but got 0",
    }

    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "workflow_run", "X-GitHub-Delivery": "delivery-1"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["event_type"] == "workflow_run"
    assert body["ingestion"]["pipeline_run"]["repository"] == "acme/shopping-app"
    assert body["ingestion"]["failure"]["failure_type"] == "CODE_REGRESSION"
    assert body["ingestion"]["classification"]["category"] == "CODE_REGRESSION"
    assert body["ingestion"]["flaky_analysis"] is None
