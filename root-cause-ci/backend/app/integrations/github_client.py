import httpx
from typing import Any, List, Dict

class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token and self.token.strip():
            self.headers["Authorization"] = f"Bearer {self.token.strip()}"

    async def _get(self, endpoint: str) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}{endpoint}", headers=self.headers)
            response.raise_for_status()
            return response.json()

    async def _post(self, endpoint: str, data: dict) -> Any:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.base_url}{endpoint}", headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()

    async def get_workflow_run(self, repo: str, run_id: int) -> dict:
        return await self._get(f"/repos/{repo}/actions/runs/{run_id}")

    async def get_failed_jobs(self, repo: str, run_id: int) -> List[dict]:
        data = await self._get(f"/repos/{repo}/actions/runs/{run_id}/jobs")
        jobs = data.get("jobs", [])
        return [job for job in jobs if job.get("conclusion") == "failure"]

    async def get_job_logs(self, repo: str, job_id: int) -> str:
        # For logs, the API redirects or returns raw text
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/repos/{repo}/actions/jobs/{job_id}/logs",
                headers=self.headers,
                follow_redirects=True
            )
            response.raise_for_status()
            return response.text

    async def get_pull_requests_for_commit(self, repo: str, commit_sha: str) -> List[dict]:
        # Returns PRs associated with a commit
        return await self._get(f"/repos/{repo}/commits/{commit_sha}/pulls")

    async def get_pull_request_changes(self, repo: str, pull_number: int) -> List[str]:
        files = await self._get(f"/repos/{repo}/pulls/{pull_number}/files")
        return [f["filename"] for f in files]

    async def post_pr_comment(self, repo: str, pull_number: int, comment: str) -> dict:
        return await self._post(f"/repos/{repo}/issues/{pull_number}/comments", {"body": comment})

    async def get_user_repositories(self) -> List[dict]:
        """Fetch repositories for the authenticated user."""
        try:
            return await self._get("/user/repos?sort=updated&per_page=100")
        except Exception:
            return []

    async def check_has_workflows(self, repo_full_name: str) -> bool:
        """Check if a repository has any GitHub Actions workflows."""
        try:
            data = await self._get(f"/repos/{repo_full_name}/actions/workflows")
            return data.get("total_count", 0) > 0
        except Exception:
            return False

    async def get_latest_workflow_run(self, repo_full_name: str) -> dict | None:
        """Fetch the most recent workflow run for a repository."""
        try:
            data = await self._get(f"/repos/{repo_full_name}/actions/runs?per_page=1")
            runs = data.get("workflow_runs", [])
            if runs:
                return runs[0]
            return None
        except Exception:
            return None
