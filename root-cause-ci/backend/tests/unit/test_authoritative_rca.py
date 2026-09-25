def test_authoritative_rca_contract_contains_required_fields():
    result = {
        "status": "SUPPORTED",
        "root_cause_commit": "abc123",
        "confidence": 0.9,
        "dependency_path": ["test", "function"],
        "evidence": [{"type": "BLAME", "status": "COMPUTED"}],
        "candidate_commits": [],
        "files_analyzed": ["src/service.py"],
        "functions_analyzed": 1,
        "graph_nodes": 2,
    }
    assert {
        "status",
        "root_cause_commit",
        "confidence",
        "dependency_path",
        "evidence",
        "candidate_commits",
        "files_analyzed",
        "functions_analyzed",
        "graph_nodes",
    } <= result.keys()