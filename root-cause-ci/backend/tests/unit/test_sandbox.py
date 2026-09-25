from pathlib import Path

from app.services.patches.sandbox import DockerSandbox


def test_sandbox_returns_explicit_failure_when_docker_is_unavailable(tmp_path: Path) -> None:
    result = DockerSandbox(timeout_seconds=1).run(tmp_path, "true", "pytest -q")

    assert result.status == "FAILED"
    assert result.build.exit_code == 127
    assert "Docker" in result.build.stderr