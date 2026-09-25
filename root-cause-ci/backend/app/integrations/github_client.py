from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote

import httpx

API_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class GitHubClient:
    """Thin async wrapper around the GitHub REST and GraphQL APIs used by the analyzer."""

    def __init__(self, token: str | None = None):
        self.token = token.strip() if token and token.strip() else None
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    # ------------------------------------------------------------------ low level
    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(f"{self.base_url}{endpoint}", headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    async def _post(self, endpoint: str, data: dict) -> Any:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(f"{self.base_url}{endpoint}", headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------ workflow runs and jobs
    async def get_workflow_run(self, repo: str, run_id: int) -> dict:
        return await self._get(f"/repos/{repo}/actions/runs/{run_id}")

    async def get_jobs_for_run(self, repo: str, run_id: int) -> list[dict]:
        data = await self._get(f"/repos/{repo}/actions/runs/{run_id}/jobs", params={"per_page": 100})
        return data.get("jobs", [])

    async def get_failed_jobs(self, repo: str, run_id: int) -> list[dict]:
        jobs = await self.get_jobs_for_run(repo, run_id)
        return [job for job in jobs if job.get("conclusion") in ("failure", "timed_out")]

    async def get_job_logs(self, repo: str, job_id: int) -> str:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
            response = await client.get(
                f"{self.base_url}/repos/{repo}/actions/jobs/{job_id}/logs",
                headers=self.headers,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response.text

    async def list_workflow_runs(
        self, repo: str, workflow_id: int, branch: str | None = None, per_page: int = 20
    ) -> list[dict]:
        params: dict[str, Any] = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        data = await self._get(f"/repos/{repo}/actions/workflows/{workflow_id}/runs", params=params)
        return data.get("workflow_runs", [])

    async def list_runs_for_branch(self, repo: str, branch: str, per_page: int = 10) -> list[dict]:
        data = await self._get(f"/repos/{repo}/actions/runs", params={"branch": branch, "per_page": per_page})
        return data.get("workflow_runs", [])

    async def get_latest_workflow_run(self, repo_full_name: str) -> dict | None:
        try:
            data = await self._get(f"/repos/{repo_full_name}/actions/runs", params={"per_page": 1})
            runs = data.get("workflow_runs", [])
            return runs[0] if runs else None
        except Exception:
            return None

    async def check_has_workflows(self, repo_full_name: str) -> bool:
        try:
            data = await self._get(f"/repos/{repo_full_name}/actions/workflows")
            return data.get("total_count", 0) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------ commits, trees, files
    async def compare_commits(self, repo: str, base: str, head: str) -> dict:
        return await self._get(f"/repos/{repo}/compare/{base}...{head}")

    async def get_commit(self, repo: str, sha: str) -> dict:
        return await self._get(f"/repos/{repo}/commits/{sha}")

    async def get_commit_changes(self, repo: str, commit_sha: str) -> list[str]:
        commit_data = await self.get_commit(repo, commit_sha)
        return [f["filename"] for f in commit_data.get("files", [])]

    async def get_tree_paths(self, repo: str, sha: str) -> list[str]:
        data = await self._get(f"/repos/{repo}/git/trees/{sha}", params={"recursive": 1})
        return [item["path"] for item in data.get("tree", []) if item.get("type") == "blob"]

    async def get_file_content(self, repo: str, file_path: str, ref: str) -> str | None:
        """Raw file content at a ref, or None when the file does not exist or is not text."""
        try:
            data = await self._get(f"/repos/{repo}/contents/{quote(file_path)}", params={"ref": ref})
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        if isinstance(data, dict) and data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return None

    async def blame_line(self, repo: str, ref: str, path: str, line: int) -> str | None:
        """Commit SHA that last touched `line` of `path` at `ref` (GraphQL blame). None if unavailable."""
        if not self.token:
            return None
        owner, name = repo.split("/", 1)
        query = """
        query($owner: String!, $name: String!, $ref: String!, $path: String!) {
          repository(owner: $owner, name: $name) {
            object(expression: $ref) {
              ... on Commit {
                blame(path: $path) { ranges { startingLine endingLine commit { oid } } }
              }
            }
          }
        }
        """
        variables = {"owner": owner, "name": name, "ref": ref, "path": path}
        try:
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/graphql", headers=self.headers, json={"query": query, "variables": variables}
                )
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return None
        obj = ((payload.get("data") or {}).get("repository") or {}).get("object") or {}
        for rng in (obj.get("blame") or {}).get("ranges", []):
            if rng["startingLine"] <= line <= rng["endingLine"]:
                return rng["commit"]["oid"]
        return None

    # ------------------------------------------------------------------ pull requests
    async def get_pull_requests_for_commit(self, repo: str, commit_sha: str) -> list[dict]:
        return await self._get(f"/repos/{repo}/commits/{commit_sha}/pulls")

    async def get_pull_request_changes(self, repo: str, pull_number: int) -> list[str]:
        files = await self._get(f"/repos/{repo}/pulls/{pull_number}/files")
        return [f["filename"] for f in files]

    async def post_pr_comment(self, repo: str, pull_number: int, comment: str) -> dict:
        return await self._post(f"/repos/{repo}/issues/{pull_number}/comments", {"body": comment})

    async def get_user_repositories(self) -> list[dict]:
        try:
            return await self._get("/user/repos", params={"sort": "updated", "per_page": 100})
        except Exception:
            return []

    async def create_branch(self, repo: str, branch_name: str, sha: str) -> dict:
        return await self._post(f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch_name}", "sha": sha})

    async def create_or_update_file(self, repo: str, file_path: str, message: str, content: str, branch: str) -> dict:
        file_sha = None
        try:
            existing = await self._get(f"/repos/{repo}/contents/{quote(file_path)}", params={"ref": branch})
            file_sha = existing.get("sha")
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
        data = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "branch": branch,
        }
        if file_sha:
            data["sha"] = file_sha
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.put(
                f"{self.base_url}/repos/{repo}/contents/{quote(file_path)}", headers=self.headers, json=data
            )
            response.raise_for_status()
            return response.json()

    async def create_pull_request(self, repo: str, title: str, body: str, head: str, base: str) -> dict:
        return await self._post(f"/repos/{repo}/pulls", {"title": title, "body": body, "head": head, "base": base})

    async def find_open_pull_request(self, repo: str, head_branch: str) -> dict | None:
        owner = repo.split("/", 1)[0]
        pulls = await self._get(f"/repos/{repo}/pulls", params={"head": f"{owner}:{head_branch}", "state": "open"})
        return pulls[0] if pulls else None
