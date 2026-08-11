import httpx
from typing import Optional
from app.core.config import get_settings


def extract_relevant_log(failure_log: str) -> str:
    """Extract lines most likely describing the failure."""
    error_lines = [
        line for line in failure_log.splitlines()
        if any(kw in line.lower() for kw in
               ["error", "importerror", "exception", "failed",
                "assert", "syntaxerror", "traceback", "no module", "exit code"])
    ]
    return "\n".join(error_lines[:25]) if error_lines else failure_log[-1000:]


def fallback_summary(category: str, explanation: str, repo: str, run_id: int) -> str:
    return (
        f"Pipeline #{run_id} in {repo} failed with category '{category}'. "
        f"{explanation} Please inspect the failed step logs for details."
    )


async def generate_llm_summary(
    failure_log: str,
    category: str,
    explanation: str,
    repo: str,
    run_id: int,
    pr_title: Optional[str] = None,
    changed_files: Optional[list[str]] = None,
) -> str:
    settings = get_settings()

    if not settings.llm_api_key:
        return fallback_summary(category, explanation, repo, run_id)

    relevant_log = extract_relevant_log(failure_log)
    changed_files_str = ", ".join(changed_files) if changed_files else "unknown"
    pr_str = pr_title if pr_title else "Direct push / unknown PR"

    prompt = f"""You are an expert DevOps engineer analyzing a CI/CD pipeline failure.

Evidence:
- Repository: {repo} (Run #{run_id})
- Associated PR/Branch: {pr_str}
- Category: {category}
- Explanation: {explanation}
- Changed Files: {changed_files_str}
- Key Error Lines from Job Log:
{relevant_log}

Write a concise 3-5 sentence root cause summary focused on the actual error.
Explain clearly what went wrong and suggest the immediate fix or next action.
Do not invent details."""

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 400,
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.llm_api_url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return (
            f"{fallback_summary(category, explanation, repo, run_id)}\n\n"
            f"_(LLM narrative fallback: {e})_"
        )
