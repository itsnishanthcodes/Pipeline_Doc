from fastapi.testclient import TestClient

from app.main import APP_VERSION, app


def test_root_endpoint_reports_version() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json()["version"] == APP_VERSION
