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
        
        # 1. Temporal Proximity
        if contributions.get("temporal_proximity", {}).get("raw_value", 0) > 0.5:
            chain.append({
                "signal": "Temporal correlation",
                "explanation": f"Commit {candidate.get('commit_sha')} was recently merged, closely preceding the failure.",
                "score_contribution": contributions["temporal_proximity"]["contribution"]
            })
            
        # 2. File Overlap
        if contributions.get("file_overlap", {}).get("raw_value", 0) > 0:
            files = candidate.get('changed_files', [])
            file_str = ", ".join(files[:3]) + ("..." if len(files) > 3 else "")
            chain.append({
                "signal": "File overlap",
                "explanation": f"Commit modified files ({file_str}) that are known to be involved in the failure.",
                "score_contribution": contributions["file_overlap"]["contribution"]
            })
            
        # 3. Stack Trace Overlap
        if contributions.get("stack_trace_overlap", {}).get("raw_value", 0) > 0:
            chain.append({
                "signal": "Stack trace overlap",
                "explanation": f"Failure stack trace references lines modified by this commit.",
                "score_contribution": contributions["stack_trace_overlap"]["contribution"]
            })
            
        # 4. Function Overlap
        if contributions.get("function_overlap", {}).get("raw_value", 0) > 0:
            funcs = candidate.get('changed_functions', [])
            func_str = ", ".join(funcs[:3]) + ("..." if len(funcs) > 3 else "")
            chain.append({
                "signal": "Function overlap",
                "explanation": f"Commit modified functions ({func_str}) that lie on the failing execution path.",
                "score_contribution": contributions["function_overlap"]["contribution"]
            })
            
        # 5. Dependency Relationship
        if contributions.get("dependency_relationship", {}).get("raw_value", 0) > 0:
            chain.append({
                "signal": "Dependency relationship",
                "explanation": f"The modified code is a direct dependency of the failing test.",
                "score_contribution": contributions["dependency_relationship"]["contribution"]
            })
            
        return chain

