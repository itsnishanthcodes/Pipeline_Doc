from typing import Dict, List, Any
from collections import defaultdict

class AttributionScorer:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "temporal_proximity": 0.20,
            "file_overlap": 0.20,
            "stack_trace_overlap": 0.20,
            "function_overlap": 0.20,
            "dependency_relationship": 0.15,
            "historical_evidence": 0.05
        }

    def score_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculates confidence score for candidate commits.
        Expects candidates to have pre-calculated raw signals [0, 1].
        """
        for candidate in candidates:
            total_score = 0.0
            contributions = {}
            
            computed_weight = 0.0
            for signal, weight in self.weights.items():
                # Get the raw signal value, default to 0 if not present
                raw_signal = candidate.get("signals", {}).get(signal)
                is_computed = raw_signal is not None
                raw_val = float(raw_signal or 0.0) if is_computed else 0.0
                contribution = raw_val * weight
                total_score += contribution
                if is_computed:
                    computed_weight += weight
                contributions[signal] = {
                    "raw_value": raw_val,
                    "weight": weight,
                    "contribution": contribution
                    ,"status": "COMPUTED" if is_computed else "UNAVAILABLE"
                }
            
            candidate["confidence_score"] = round(total_score / computed_weight, 4) if computed_weight else 0.0
            candidate["contributions"] = contributions
            
        # Sort by confidence descending
        candidates.sort(key=lambda x: x["confidence_score"], reverse=True)
        return candidates

