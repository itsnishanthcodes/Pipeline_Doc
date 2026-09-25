from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.core.database import _add_missing_columns
from app.main import app
from app.services.auto_analysis import should_auto_analyze
from app.services.flaky.detector import FlakyTestDetector


def test_successful_workflow_run_webhook_no_longer_crashes():
    client = TestClient(app)
    response = client.post(
        "/webhooks/github",
        headers={"X-GitHub-Event": "workflow_run"},
        json={"repository": {"full_name": "a/b"}, "workflow_run": {"id": 1, "status": "completed", "conclusion": "success"}},
    )
    assert response.status_code == 200
    assert response.json()["ingestion"]["failure"] is None
    assert response.json()["auto_analysis_scheduled"] is False


def test_only_completed_failed_runs_trigger_auto_analysis():
    failed = {"action": "completed", "repository": {"full_name": "acme/app"},
              "workflow_run": {"id": 42, "status": "completed", "conclusion": "failure"}}
    assert should_auto_analyze("workflow_run", failed) == ("acme/app", 42)
    assert should_auto_analyze("workflow_job", failed) is None
    assert should_auto_analyze("workflow_run", {**failed, "action": "requested"}) is None
    ok = {**failed, "workflow_run": {"id": 42, "status": "completed", "conclusion": "success"}}
    assert should_auto_analyze("workflow_run", ok) is None


def test_missing_report_columns_are_added_to_old_databases():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE analysis_reports (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, "
                          "repository VARCHAR(255) NOT NULL, run_id VARCHAR(100) NOT NULL)"))
    _add_missing_columns(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("analysis_reports")}
    assert {"details", "fix_pr_url", "fix_branch", "verification_status", "branch", "source"} <= columns


def test_first_failure_after_green_history_is_not_flaky():
    detector = FlakyTestDetector()
    for outcome in ["PASS"] * 9 + ["FAIL"]:
        detector.record_run("job", outcome=outcome)
    assert detector.analyze("job").classification == "LIKELY_STABLE"


def test_cors_origins_accept_comma_separated_env(monkeypatch):
    from app.core.config import Settings
    monkeypatch.setenv("BACKEND_CORS_ORIGINS", "http://localhost:5173, http://localhost:5174")
    assert Settings().cors_origins == ["http://localhost:5173", "http://localhost:5174"]
