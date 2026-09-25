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


def test_github_webhook_replays_duplicate_delivery() -> None:
    payload = {
        "repository": {"full_name": "acme/idempotent-app"},
        "workflow_run": {
            "id": 456,
            "name": "CI",
            "status": "completed",
            "conclusion": "failure",
        },
        "log_excerpt": "AssertionError: expected 1 but got 0",
    }
    headers = {
        "X-GitHub-Event": "workflow_run",
        "X-GitHub-Delivery": "delivery-idempotent-456",
    }

    first = client.post("/webhooks/github", headers=headers, json=payload)
    second = client.post("/webhooks/github", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_github_webhook_accepts_successful_run() -> None:
    payload = {
        "repository": {"full_name": "acme/healthy-app"},
        "workflow_run": {
            "id": 789,
            "name": "CI",
            "status": "completed",
            "conclusion": "success",
        },
    }
    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "workflow_run", "X-GitHub-Delivery": "delivery-success-789"},
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["ingestion"]["failure"] is None
