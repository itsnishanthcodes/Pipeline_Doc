from typing import Any, Dict, List

# (signal key, display name, threshold, fallback explanation)
SIGNALS = [
    ("temporal_proximity", "Temporal correlation", 0.5,
     "Commit {sha} was merged shortly before the failure."),
    ("file_overlap", "File overlap", 0.0,
     "Commit modified files ({files}) that are involved in the failure."),
    ("stack_trace_overlap", "Stack trace overlap", 0.0,
     "The failure stack trace references lines modified by this commit."),
    ("function_overlap", "Function overlap", 0.0,
     "Commit modified functions ({functions}) that lie on the failing execution path."),
    ("dependency_relationship", "Dependency relationship", 0.0,
     "The modified code is a direct dependency of the failing test."),
    ("historical_evidence", "Historical evidence", 0.0,
     "The previous run of this workflow passed, so the failure was introduced recently."),
]


class EvidenceGenerator:
    def generate_chain(self, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Translate scored signals into a human-readable evidence chain.

        Uses the concrete reason recorded for each signal (file names, line numbers, functions)
        when available, and a generic explanation otherwise.
        """
        chain = []
        contributions = candidate.get("contributions", {})
        reasons = candidate.get("reasons", {})
        files = candidate.get("changed_files", [])
        funcs = candidate.get("changed_functions", [])
        fmt = {
            "sha": str(candidate.get("commit_sha", ""))[:7],
            "files": ", ".join(files[:3]) + ("..." if len(files) > 3 else ""),
            "functions": ", ".join(funcs[:3]) + ("..." if len(funcs) > 3 else ""),
        }
        for key, name, threshold, fallback in SIGNALS:
            info = contributions.get(key, {})
            if info.get("raw_value", 0) > threshold:
                chain.append({
                    "signal": name,
                    "explanation": reasons.get(key) or fallback.format(**fmt),
                    "score_contribution": info.get("contribution", 0.0),
                })
        return chain
