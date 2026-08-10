from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_endpoint_returns_phase_marker() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["phase"] == "phase-1"
