from typing import Dict, List, Any

class EvidenceGenerator:
    def __init__(self):
        pass

    def generate_chain(self, candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Translates raw signals and contributions into a human-readable evidence chain.
        """
        chain = []
        contributions = candidate.get("contributions", {})

        def add(signal: str, label: str, evidence_type: str, source: str, description: str, value: object, supports: str) -> None:
            component = contributions.get(signal, {})
            if component.get("status") != "COMPUTED" or not component.get("raw_value"):
                return
            chain.append({
                "type": evidence_type,
                "signal": label,
                "source": source,
                "description": description,
                "value": value,
                "location": source,
                "supports": supports,
                "relevance": component.get("raw_value"),
                "explanation": description,
                "score_contribution": component.get("contribution", 0.0),
            })
        
        # 1. Temporal Proximity
        if contributions.get("temporal_proximity", {}).get("raw_value", 0) > 0.5:
            add("temporal_proximity", "Temporal correlation", "TEMPORAL", candidate.get("commit_sha", ""), "Commit timing was computed from the available history.", candidate.get("timestamp"), "candidate commit")
            
        # 2. File Overlap
        if contributions.get("file_overlap", {}).get("raw_value", 0) > 0:
            files = candidate.get('changed_files', [])
            file_str = ", ".join(files[:3]) + ("..." if len(files) > 3 else "")
            add("file_overlap", "File overlap", "FILE_OVERLAP", candidate.get("commit_sha", ""), f"Commit modified involved files ({file_str}).", files, "candidate root cause")
            
        # 3. Stack Trace Overlap
        if contributions.get("stack_trace_overlap", {}).get("raw_value", 0) > 0:
            add("stack_trace_overlap", "Stack trace overlap", "STACK_TRACE", candidate.get("commit_sha", ""), "The failure location overlaps the commit's changed area.", candidate.get("changed_lines", []), "candidate root cause")
            
        # 4. Function Overlap
        if contributions.get("function_overlap", {}).get("raw_value", 0) > 0:
            funcs = candidate.get('changed_functions', [])
            func_str = ", ".join(funcs[:3]) + ("..." if len(funcs) > 3 else "")
            add("function_overlap", "Function overlap", "FUNCTION_OVERLAP", candidate.get("commit_sha", ""), f"Commit modified functions ({func_str}) associated with the failure.", funcs, "candidate root cause")
            
        # 5. Dependency Relationship
        if contributions.get("dependency_relationship", {}).get("raw_value", 0) > 0:
            add("dependency_relationship", "Dependency relationship", "DEPENDENCY_PATH", candidate.get("commit_sha", ""), "The graph established a dependency path from the failing test.", candidate.get("dependency_path", []), "candidate root cause")
            
        return chain

