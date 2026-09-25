import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.pipeline_analyzer as analyzer_module
from app.models import AnalysisReport, Base, User
from app.services.pipeline_analyzer import PipelineAnalyzer

HEAD, BASE = "c3" * 20, "c0" * 20
C1, C2 = "c1" * 20, "c2" * 20
CALC_PATCH = "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a + b\n+    return a + b + 1\n"
JOB_LOG = """2026-09-25T10:00:00.0000000Z ##[group]Run pytest -q
2026-09-25T10:00:02.4000000Z >       assert add(2, 3) == 5
2026-09-25T10:00:02.5000000Z E       assert 6 == 5
2026-09-25T10:00:02.6000000Z E        +  where 6 = add(2, 3)
2026-09-25T10:00:02.7000000Z tests/test_calc.py:4: AssertionError
2026-09-25T10:00:02.8000000Z FAILED tests/test_calc.py::test_add - assert 6 == 5
2026-09-25T10:00:03.0000000Z ##[error]Process completed with exit code 1.
"""
FILES = {
    "src/calc.py": "def add(a, b):\n    return a + b + 1\n",
    "tests/test_calc.py": "from src.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
}


class FakeGitHub:
    """Deterministic stand-in for the GitHub API (no network)."""

    def __init__(self, token=None):
        self.comments = []

    async def get_workflow_run(self, repo, run_id):
        return {"id": 300, "status": "completed", "conclusion": "failure", "head_branch": "main", "head_sha": HEAD,
                "workflow_id": 7, "run_number": 12, "name": "CI", "html_url": "https://github.com/acme/app/actions/runs/300"}

    async def get_jobs_for_run(self, repo, run_id):
        if run_id == 300:
            return [{"id": 900, "name": "test", "conclusion": "failure", "html_url": "job-url",
                     "steps": [{"name": "Run tests", "conclusion": "failure"}]}]
        return [{"id": run_id * 10, "name": "test", "conclusion": "success"}]

    async def get_job_logs(self, repo, job_id):
        return JOB_LOG

    async def get_tree_paths(self, repo, sha):
        return ["README.md", "src/calc.py", "tests/test_calc.py", "tests/test_other.py"]

    async def list_workflow_runs(self, repo, workflow_id, branch=None, per_page=20):
        return [
            {"id": 300, "run_number": 12, "status": "completed", "conclusion": "failure", "head_sha": HEAD},
            {"id": 299, "run_number": 11, "status": "completed", "conclusion": "success", "head_sha": BASE},
            {"id": 298, "run_number": 10, "status": "completed", "conclusion": "success", "head_sha": "b" * 40},
        ]

    async def compare_commits(self, repo, base, head):
        assert base == BASE and head == HEAD
        return {"commits": [{"sha": C1}, {"sha": C2}, {"sha": HEAD}]}

    async def get_commit(self, repo, sha):
        files = {
            C1: [{"filename": "README.md", "patch": "@@ -1 +1 @@\n-a\n+b\n"}],
            C2: [{"filename": "src/calc.py", "patch": CALC_PATCH}],
            HEAD: [{"filename": "tests/test_other.py", "patch": "@@ -1 +1 @@\n-x\n+y\n"}],
        }[sha]
        return {"sha": sha, "commit": {"message": f"commit {sha[:2]}", "author": {"name": "dev", "date": "2026-09-24"}},
                "author": {"login": "dev"}, "files": files}

    async def get_file_content(self, repo, path, ref):
        return FILES.get(path)

    async def blame_line(self, repo, ref, path, line):
        return None

    async def get_pull_requests_for_commit(self, repo, sha):
        return []

    async def post_pr_comment(self, repo, number, body):
        self.comments.append(body)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, full_name="Dev", email="dev@example.com", hashed_password="x", github_token="t"))
    session.commit()
    yield session
    session.close()


def test_analyzer_ranks_the_real_culprit_and_targets_the_source_file(db, monkeypatch):
    monkeypatch.setattr(analyzer_module, "GitHubClient", FakeGitHub)
    result = asyncio.run(PipelineAnalyzer(db).analyze_pipeline("acme/app", 300, 1))

    assert result["classification"]["category"] == "CODE_REGRESSION"
    assert result["jobs"][0]["error_message"] == "assert 6 == 5"
    assert result["jobs"][0]["failed_tests"] == ["tests/test_calc.py::test_add"]
    assert result["base_sha"] == BASE
    # the culprit is the middle commit, not the latest one
    assert result["candidates"][0]["commit_sha"] == C2
    assert len(result["candidates"]) == 3
    assert result["target_file"] == "src/calc.py"
    # no LLM key in tests: the patch is skipped with an explicit reason, never invented
    assert result["patch"]["status"] == "skipped"
    assert "LLM_API_KEY" in result["patch"]["reason"]
    assert result["flaky"]["classification"] == "INSUFFICIENT_HISTORY"
    saved = db.get(AnalysisReport, result["report_id"])
    assert saved.branch == "main" and saved.details_dict()["candidates"][0]["commit_sha"] == C2


def test_flaky_history_skips_the_patch(db, monkeypatch):
    class FlakyGitHub(FakeGitHub):
        async def list_workflow_runs(self, repo, workflow_id, branch=None, per_page=20):
            runs = [{"id": 300, "run_number": 12, "status": "completed", "conclusion": "failure", "head_sha": HEAD}]
            for i, concl in enumerate(["success", "failure", "success", "failure", "success"]):
                runs.append({"id": 290 + i, "run_number": 5 + i, "status": "completed", "conclusion": concl,
                             "head_sha": HEAD if concl == "success" and i == 4 else f"{i}" * 40})
            return runs

        async def get_jobs_for_run(self, repo, run_id):
            if run_id == 300:
                return await super().get_jobs_for_run(repo, run_id)
            concl = {290: "success", 291: "failure", 292: "success", 293: "failure", 294: "success"}[run_id]
            return [{"id": run_id * 10, "name": "test", "conclusion": concl}]

        async def compare_commits(self, repo, base, head):
            return {"commits": [{"sha": HEAD}]}

    monkeypatch.setattr(analyzer_module, "GitHubClient", FlakyGitHub)
    result = asyncio.run(PipelineAnalyzer(db).analyze_pipeline("acme/app", 300, 1))
    assert result["flaky"]["classification"] == "LIKELY_FLAKY"
    assert result["flaky"]["same_commit_passed"] is True
    assert result["patch"]["status"] == "skipped"
    assert "flaky" in result["patch"]["reason"]
