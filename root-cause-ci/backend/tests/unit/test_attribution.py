from app.services.attribution.scorer import AttributionScorer
from app.services.evidence.generator import EvidenceGenerator

def test_attribution_scorer_and_evidence_generator():
    scorer = AttributionScorer()
    candidates = [
        {
            "commit_sha": "commit_A",
            "changed_files": ["app/main.py"],
            "changed_functions": ["process"],
            "signals": {
                "temporal_proximity": 0.9,
                "file_overlap": 1.0,
                "stack_trace_overlap": 0.8,
                "function_overlap": 1.0,
                "dependency_relationship": 0.5,
                "historical_evidence": 0.0
            }
        },
        {
            "commit_sha": "commit_B",
            "changed_files": ["docs/readme.md"],
            "signals": {
                "temporal_proximity": 0.5,
                "file_overlap": 0.0,
                "stack_trace_overlap": 0.0,
                "function_overlap": 0.0,
                "dependency_relationship": 0.0,
                "historical_evidence": 0.0
            }
        }
    ]
    
    scored = scorer.score_candidates(candidates)
    
    # Check scoring
    assert scored[0]["commit_sha"] == "commit_A"
    assert scored[0]["confidence_score"] > 0.5
    
    assert scored[1]["commit_sha"] == "commit_B"
    assert scored[1]["confidence_score"] == 0.1  # 0.5 * 0.2
    
    # Check evidence generator
    generator = EvidenceGenerator()
    chain = generator.generate_chain(scored[0])
    
    assert len(chain) > 0
    signals = [c["signal"] for c in chain]
    assert "File overlap" in signals
    assert "Temporal correlation" in signals

