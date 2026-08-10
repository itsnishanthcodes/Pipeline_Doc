from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.schemas.git import BlameResult, ChangedLine, CommitCandidate, CommitMetadata, GitAnalysisResult
from app.services.git.repository import GitRepositoryClient, get_git_repository_client


@dataclass(slots=True)
class CandidateWeights:
    temporal: float = 0.30
    file_overlap: float = 0.25
    function_overlap: float = 0.10
    blame: float = 0.20
    diff_relevance: float = 0.10
    stack_overlap: float = 0.05


class GitAnalysisService:
    def __init__(self, repository_path: str | Path, client: GitRepositoryClient | None = None) -> None:
        self.repository_path = Path(repository_path)
        self._client = client or get_git_repository_client(self.repository_path)

    def analyze_failure(
        self,
        failing_commit_sha: str,
        previous_successful_commit_sha: str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> GitAnalysisResult:
        failing_commit = self._client.get_commit_metadata(failing_commit_sha)
        previous_commit = self._client.get_commit_metadata(previous_successful_commit_sha) if previous_successful_commit_sha else None
        changed_files = self._client.get_changed_files(previous_successful_commit_sha, failing_commit_sha) if previous_successful_commit_sha else []
        changed_lines = self._client.get_changed_lines(previous_successful_commit_sha, failing_commit_sha, file_path) if previous_successful_commit_sha and file_path else []
        blame = self._client.blame_line(failing_commit_sha, file_path, line_number) if file_path and line_number else None
        candidates = self.build_candidate_commits(
            previous_successful_commit_sha=previous_successful_commit_sha,
            failing_commit_sha=failing_commit_sha,
            file_path=file_path,
            line_number=line_number,
        )
        return GitAnalysisResult(
            repository_path=str(self.repository_path),
            failing_commit=failing_commit,
            previous_successful_commit=previous_commit,
            changed_files=changed_files,
            changed_lines=changed_lines,
            blame=blame,
            candidates=candidates,
        )

    def build_candidate_commits(
        self,
        previous_successful_commit_sha: str | None,
        failing_commit_sha: str,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> list[CommitCandidate]:
        if not previous_successful_commit_sha:
            return [self._candidate_from_commit(failing_commit_sha, file_path=file_path, line_number=line_number, rank_position=0, total=1)]

        commit_range = self._client.resolve_commit_range(previous_successful_commit_sha, failing_commit_sha)
        if failing_commit_sha not in commit_range:
            commit_range.append(failing_commit_sha)

        total = max(len(commit_range), 1)
        blame_commit_sha = None
        if file_path and line_number:
            try:
                blame_commit_sha = self._client.blame_line(failing_commit_sha, file_path, line_number).commit_sha
            except Exception:
                blame_commit_sha = None

        candidates = [
            self._candidate_from_commit(
                commit_sha,
                file_path=file_path,
                line_number=line_number,
                rank_position=index,
                total=total,
                blame_commit_sha=blame_commit_sha,
            )
            for index, commit_sha in enumerate(commit_range)
        ]
        return sorted(candidates, key=lambda candidate: candidate.rank_score, reverse=True)

    def _candidate_from_commit(
        self,
        commit_sha: str,
        file_path: str | None,
        line_number: int | None,
        rank_position: int,
        total: int,
        blame_commit_sha: str | None = None,
    ) -> CommitCandidate:
        metadata = self._client.get_commit_metadata(commit_sha)
        changed_files = self._client.get_changed_files(metadata.parents[0], commit_sha) if metadata.parents else []
        diff = self._client.diff_for_commit(commit_sha, file_path=file_path)
        file_overlap_score = 1.0 if file_path and file_path in changed_files else 0.0
        blame_score = 1.0 if blame_commit_sha and blame_commit_sha == commit_sha else 0.0
        temporal_score = self._normalized_temporal_score(rank_position, total)

        # naive function extraction from diff (language-agnostic heuristic)
        changed_functions: list[str] = []
        try:
            for line in (diff or "").splitlines():
                line = line.strip()
                if line.startswith("+"):
                    # python: def or class
                    if line.startswith("+def ") or line.startswith("+class "):
                        parts = line[1:].split()
                        if len(parts) >= 2:
                            changed_functions.append(parts[1].split("(")[0].strip(":"))
                    # javascript/ts: function keyword
                    if "function " in line:
                        try:
                            name = line.split("function ", 1)[1].split("(")[0].strip()
                            if name:
                                changed_functions.append(name)
                        except Exception:
                            pass
        except Exception:
            changed_functions = []

        function_overlap_score = 1.0 if changed_functions and file_path and file_path in changed_files else 0.0

        # diff relevance: proportion of diff lines that reference the file_path or mention "error"
        diff_lines = (diff or "").splitlines()
        relevant_hits = 0
        for l in diff_lines:
            low = l.lower()
            if file_path and file_path in l:
                relevant_hits += 1
            elif "error" in low or "exception" in low:
                relevant_hits += 1
        diff_relevance_score = round(min(1.0, relevant_hits / max(1, len(diff_lines))), 3) if diff_lines else 0.0

        # stack overlap: if failing file is among changed files
        stack_overlap_score = 1.0 if file_path and file_path in changed_files else 0.0

        weights = CandidateWeights()
        rank_score = round(
            temporal_score * weights.temporal
            + file_overlap_score * weights.file_overlap
            + function_overlap_score * weights.function_overlap
            + blame_score * weights.blame
            + diff_relevance_score * weights.diff_relevance
            + stack_overlap_score * weights.stack_overlap,
            3,
        )
        return CommitCandidate(
            commit_sha=metadata.commit_sha,
            author=metadata.author_name,
            timestamp=metadata.timestamp,
            changed_files=changed_files,
            changed_functions=changed_functions,
            diff=diff,
            temporal_score=temporal_score,
            file_overlap_score=file_overlap_score,
            function_overlap_score=function_overlap_score,
            blame_score=blame_score,
            rank_score=rank_score,
        )

    def find_related_files(self, commit_sha: str) -> list[str]:
        metadata = self._client.get_commit_metadata(commit_sha)
        if not metadata.parents:
            return []
        return self._client.get_changed_files(metadata.parents[0], commit_sha)

    def find_related_functions(self, commit_sha: str) -> list[str]:
        return []

    def find_failure_path(
        self,
        failing_commit_sha: str,
        previous_successful_commit_sha: str | None = None,
        file_path: str | None = None,
        line_number: int | None = None,
    ) -> GitAnalysisResult:
        return self.analyze_failure(
            failing_commit_sha=failing_commit_sha,
            previous_successful_commit_sha=previous_successful_commit_sha,
            file_path=file_path,
            line_number=line_number,
        )

    def _normalized_temporal_score(self, rank_position: int, total: int) -> float:
        if total <= 1:
            return 1.0
        # rank_position is 0-based; earlier positions are older commits.
        # We normalize so that commits closer to the failing commit (higher index)
        # get a larger score. Assuming commit_range is ordered from older->newer.
        return round((rank_position + 1) / total, 3)


_service_cache: dict[str, GitAnalysisService] = {}


def get_git_analysis_service(repository_path: str | Path) -> GitAnalysisService:
    key = str(Path(repository_path))
    if key not in _service_cache:
        _service_cache[key] = GitAnalysisService(repository_path)
    return _service_cache[key]
