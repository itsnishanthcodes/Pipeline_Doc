from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.git.analysis import GitAnalysisService


def run_git(repo_path: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def create_commit(repo_path: Path, file_path: Path, content: str, message: str) -> str:
    file_path.write_text(content, encoding="utf-8")
    run_git(repo_path, "add", str(file_path.relative_to(repo_path)))
    run_git(repo_path, "commit", "-m", message)
    return run_git(repo_path, "rev-parse", "HEAD")


def test_git_analysis_extracts_metadata_diff_blame_and_candidates() -> None:
    with TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        run_git(repo_path, "init")
        run_git(repo_path, "config", "user.name", "Test User")
        run_git(repo_path, "config", "user.email", "test@example.com")

        source_dir = repo_path / "src"
        source_dir.mkdir()
        file_path = source_dir / "app.txt"

        base_commit = create_commit(repo_path, file_path, "alpha\nbeta\n", "base state")
        failing_commit = create_commit(repo_path, file_path, "alpha\ngamma\n", "introduce regression")

        service = GitAnalysisService(repo_path)
        result = service.analyze_failure(
            failing_commit_sha=failing_commit,
            previous_successful_commit_sha=base_commit,
            file_path="src/app.txt",
            line_number=2,
        )

        assert result.failing_commit.commit_sha == failing_commit
        assert result.previous_successful_commit is not None
        assert result.previous_successful_commit.commit_sha == base_commit
        assert "src/app.txt" in result.changed_files
        assert any(change.line_number == 2 for change in result.changed_lines)
        assert result.blame is not None
        assert result.blame.commit_sha == failing_commit
        assert result.candidates
        assert result.candidates[0].commit_sha == failing_commit
        assert result.candidates[0].file_overlap_score == 1.0
        assert result.candidates[0].blame_score == 1.0
        assert result.candidates[0].rank_score > 0.0
