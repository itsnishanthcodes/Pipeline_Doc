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


# Dummy comment to trigger hot-reload and clear lru_cache
import json
import re


_SECRET_LINE = re.compile(
    r"(?im)^.*(?:token|api[_-]?key|secret|password|authorization|private[_-]?key)\s*[:=].*$"
)


def redact_sensitive_log_lines(log_text: str) -> str:
    """Remove common credential-bearing log lines before sending context to an LLM."""
    return _SECRET_LINE.sub("[REDACTED SENSITIVE LOG LINE]", log_text)

async def generate_constrained_patch(
    failure_log: str,
    evidence_chain: list[dict],
    repo: str,
    run_id: int,
    changed_files: list[str],
) -> dict:
    """
    Generates a structured JSON unified diff based on deterministic evidence.
    """
    settings = get_settings()

    if not settings.llm_api_key or not settings.llm_api_key.strip():
        return {
            "summary": "LLM_API_KEY not set. Cannot generate patch.",
            "patch": None,
            "modified_files": []
        }

    relevant_log = redact_sensitive_log_lines(extract_relevant_log(failure_log))
    changed_files_str = ", ".join(changed_files) if changed_files else "none"
    
    evidence_str = ""
    for idx, ev in enumerate(evidence_chain):
        evidence_str += f"{idx+1}. {ev['signal']}: {ev['explanation']} (Score: {ev['score_contribution']})\n"

    prompt = f"""You are an expert software engineer fixing a CI/CD pipeline failure.
You MUST output your response in strict JSON format.

Evidence:
- Repository: {repo} (Run #{run_id})
- Allowed Scope (Changed Files): {changed_files_str}
- Deterministic Evidence Chain:
{evidence_str}

Key Error Lines from Job Log:
{relevant_log}

Your task is to generate a fix.
Constraints:
1. Try to ONLY modify files explicitly listed in the Allowed Scope. However, if the Allowed Scope is 'none', you are authorized to propose a patch for the file mentioned in the error logs.
2. Return a strict JSON object with this exact schema:
{{
  "summary": "Concise root cause summary based on evidence",
    "patch": "A unified diff beginning with --- a/ and +++ b/, or null if no patch can be safely generated",
  "modified_files": ["list", "of", "files", "modified"]
}}
"""

    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(settings.llm_api_url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return json.loads(content)
    except Exception as e:
        return {
            "summary": f"Failed to generate fix: {e}",
            "patch": None,
            "modified_files": []
        }
