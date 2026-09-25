import pytest
from app.services.graph.builder import GraphBuilder

def test_graph_builder_tracks_dependencies_and_paths():
    builder = GraphBuilder()
    
    # 1. Add files
    builder.add_file("auth/service.py")
    builder.add_file("tests/test_auth.py")
    
    # 2. Add functions
    builder.add_function("validate_token", "auth/service.py")
    
    # 3. Add tests
    builder.add_test("test_invalid_token", "tests/test_auth.py")
    
    # 4. Add calls
    builder.add_call("tests/test_auth.py::test_invalid_token", "validate_token")
    
    # 5. Add commit modifications
    builder.add_commit_modification("ABC1234", "auth/service.py", "validate_token")
    
    # Verify graph structure
    assert builder.graph.has_node("auth/service.py")
    assert builder.graph.has_node("tests/test_auth.py::test_invalid_token")
    
    # Find path from failing test to commit
    paths = builder.find_paths_from_test_to_commits("test_invalid_token")
    
    assert len(paths) > 0
    # Expected path: Test -> Function -> Commit
    # Or Test -> Calls -> Function <- ModifiedBy <- Commit
    assert "ABC1234" in paths[0]
    assert "tests/test_auth.py::test_invalid_token" in paths[0]


def test_graph_builder_connects_ast_calls():
    builder = GraphBuilder()
    builder.add_ast_result(
        "src/service.py",
        {
            "functions": [{"name": "checkout"}, {"name": "calculate_total"}],
            "calls": [{"name": "calculate_total", "caller": "checkout"}],
            "imports": [],
        },
    )
    assert builder.graph.has_edge("src/service.py::checkout", "src/service.py::calculate_total")
    assert builder.graph["src/service.py::checkout"]["src/service.py::calculate_total"][0]["relation"] == "CALLS"

