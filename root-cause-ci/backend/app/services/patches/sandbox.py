from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass(frozen=True)
class SandboxResult:
    patch_applied: bool
    build: CommandResult
    original_test: CommandResult
    related_tests: CommandResult | None
    status: str
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class DockerSandbox:
    def __init__(self, image: str = "python:3.12-slim", timeout_seconds: int = 300) -> None:
        self.image = image
        self.timeout_seconds = timeout_seconds

    def run(self, workspace: str | Path, build_command: str, test_command: str, related_command: str | None = None) -> SandboxResult:
        workspace = Path(workspace).resolve()
        build = self._run(workspace, build_command)
        if build.exit_code != 0:
            return SandboxResult(True, build, self._not_run(test_command), None, "FAILED", "Build failed.")
        original = self._run(workspace, test_command)
        if original.exit_code != 0:
            return SandboxResult(True, build, original, None, "FAILED", "Original failing test did not pass.")
        related = self._run(workspace, related_command) if related_command else None
        if related and related.exit_code != 0:
            return SandboxResult(True, build, original, related, "FAILED", "Related tests failed.")
        return SandboxResult(True, build, original, related, "PASSED")

    def _run(self, workspace: Path, command: str) -> CommandResult:
        started = time.perf_counter()
        docker_command = [
            "docker", "run", "--rm", "--network", "none", "--cpus", "1", "--memory", "1g",
            "-v", f"{workspace}:/workspace:rw", "-w", "/workspace", self.image, "sh", "-lc", command,
        ]
        try:
            completed = subprocess.run(docker_command, capture_output=True, text=True, timeout=self.timeout_seconds, check=False)
            stderr = completed.stderr[-12000:]
            if completed.returncode == 127 and ("dockerDesktop" in stderr or "Cannot connect" in stderr):
                stderr = f"Docker daemon unavailable: {stderr}"
            return CommandResult(command, completed.returncode, completed.stdout[-12000:], stderr, round(time.perf_counter() - started, 4))
        except FileNotFoundError:
            return CommandResult(command, 127, "", "Docker executable is not available.", round(time.perf_counter() - started, 4))
        except subprocess.TimeoutExpired as error:
            return CommandResult(command, 124, error.stdout or "", error.stderr or "Command timed out.", round(time.perf_counter() - started, 4))

    def _not_run(self, command: str) -> CommandResult:
        return CommandResult(command, -1, "", "Not run because an earlier stage failed.", 0.0)