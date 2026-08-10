from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from app.schemas.git import BlameResult, ChangedLine, CommitMetadata


class GitCommandError(RuntimeError):
    pass


@dataclass(slots=True)
class RawCommitInfo:
    commit_sha: str
    author_name: str
    author_email: str
    timestamp: datetime
    parents: list[str]
    subject: str


class GitRepositoryClient:
    def __init__(self, repository_path: str | Path) -> None:
        self.repository_path = Path(repository_path)

    def _run_git(self, args: Sequence[str]) -> str:
        completed = subprocess.run(
            ["git", "-C", str(self.repository_path), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise GitCommandError(completed.stderr.strip() or completed.stdout.strip() or "git command failed")
        return completed.stdout.strip()

    def get_commit_metadata(self, commit_sha: str) -> CommitMetadata:
        raw = self._run_git(["show", "-s", "--format=%H%n%an%n%ae%n%at%n%P%n%s", commit_sha])
        lines = raw.splitlines()
        if len(lines) < 6:
            raise GitCommandError(f"Unexpected git show output for {commit_sha}")
        timestamp = datetime.fromtimestamp(int(lines[3]), tz=UTC)
        parents = [parent for parent in lines[4].split() if parent]
        return CommitMetadata(
            commit_sha=lines[0],
            author_name=lines[1],
            author_email=lines[2],
            timestamp=timestamp,
            parents=parents,
            subject=lines[5],
        )

    def list_commits(self, revision_range: str) -> list[CommitMetadata]:
        output = self._run_git(["rev-list", "--reverse", revision_range])
        if not output:
            return []
        return [self.get_commit_metadata(commit_sha) for commit_sha in output.splitlines() if commit_sha]

    def get_changed_files(self, base_commit: str, head_commit: str) -> list[str]:
        output = self._run_git(["diff", "--name-only", base_commit, head_commit])
        return [line for line in output.splitlines() if line.strip()]

    def get_changed_lines(self, base_commit: str, head_commit: str, file_path: str) -> list[ChangedLine]:
        output = self._run_git(["diff", "--unified=0", base_commit, head_commit, "--", file_path])
        changed_lines: list[ChangedLine] = []
        for line in output.splitlines():
            match = re.match(r"@@ -(?P<old_start>\d+)(?:,(?P<old_len>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_len>\d+))? @@", line)
            if not match:
                continue
            new_start = int(match.group("new_start"))
            new_len = int(match.group("new_len") or "1")
            for offset in range(new_len):
                changed_lines.append(
                    ChangedLine(
                        file_path=file_path,
                        line_number=new_start + offset,
                        change_type="modified" if base_commit else "added",
                    )
                )
        return changed_lines

    def blame_line(self, commit_sha: str, file_path: str, line_number: int) -> BlameResult:
        output = self._run_git(["blame", "--porcelain", commit_sha, "-L", f"{line_number},{line_number}", "--", file_path])
        header = output.splitlines()[0]
        header_parts = header.split()
        if len(header_parts) < 1:
            raise GitCommandError("Unexpected git blame output")

        commit = header_parts[0]
        author_name = ""
        author_email = ""
        timestamp = datetime.now(tz=UTC)
        summary = ""
        for line in output.splitlines()[1:]:
            if line.startswith("author "):
                author_name = line.removeprefix("author ")
            elif line.startswith("author-mail "):
                author_email = line.removeprefix("author-mail ").strip("<>")
            elif line.startswith("author-time "):
                author_time = line.removeprefix("author-time ")
                timestamp = datetime.fromtimestamp(int(author_time), tz=UTC)
            elif line.startswith("summary "):
                summary = line.removeprefix("summary ")

        return BlameResult(
            file_path=file_path,
            line_number=line_number,
            commit_sha=commit,
            author_name=author_name,
            author_email=author_email,
            timestamp=timestamp,
            summary=summary,
        )

    def diff_for_commit(self, commit_sha: str, file_path: str | None = None) -> str:
        args = ["show", "--format=medium", "--unified=0", commit_sha]
        if file_path:
            args.extend(["--", file_path])
        return self._run_git(args)

    def resolve_commit_range(self, base_commit: str, head_commit: str) -> list[str]:
        output = self._run_git(["rev-list", "--ancestry-path", "--reverse", f"{base_commit}..{head_commit}"])
        return [line for line in output.splitlines() if line.strip()]

    def exists(self) -> bool:
        try:
            self._run_git(["rev-parse", "--is-inside-work-tree"])
            return True
        except GitCommandError:
            return False


_client: GitRepositoryClient | None = None


def get_git_repository_client(repository_path: str | Path) -> GitRepositoryClient:
    global _client
    if _client is None or Path(repository_path) != _client.repository_path:
        _client = GitRepositoryClient(repository_path)
    return _client
