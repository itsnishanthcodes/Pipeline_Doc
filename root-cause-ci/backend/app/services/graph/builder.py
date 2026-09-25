import networkx as nx
from typing import Dict, Any, List

class GraphBuilder:
    def __init__(self):
        self.graph = nx.MultiDiGraph()

    def add_file(self, file_path: str):
        self.graph.add_node(file_path, type="FILE")

    def add_import(self, file_path: str, import_name: str):
        module_id = f"module::{import_name}"
        self.graph.add_node(module_id, type="MODULE", name=import_name)
        self.graph.add_edge(file_path, module_id, relation="IMPORTS")

    def add_function(self, func_name: str, file_path: str):
        func_id = f"{file_path}::{func_name}"
        self.graph.add_node(func_id, type="FUNCTION", name=func_name, file=file_path)
        self.graph.add_edge(func_id, file_path, relation="DEFINED_IN")

    def add_test(self, test_name: str, file_path: str):
        test_id = f"{file_path}::{test_name}"
        self.graph.add_node(test_id, type="TEST", name=test_name, file=file_path)
        self.graph.add_edge(test_id, file_path, relation="DEFINED_IN")

    def add_test_relationship(self, test_name: str, test_file: str, function_id: str):
        test_id = f"{test_file}::{test_name}"
        self.graph.add_node(test_id, type="TEST", name=test_name, file=test_file)
        if self.graph.has_node(function_id):
            self.graph.add_edge(test_id, function_id, relation="TESTS")

    def add_ast_result(self, file_path: str, ast_result: Dict[str, Any], test_name: str | None = None):
        self.add_file(file_path)
        for imported in ast_result.get("imports", []):
            self.add_import(file_path, imported["name"])
        for function in ast_result.get("functions", []):
            self.add_function(function["name"], file_path)
        for call in ast_result.get("calls", []):
            caller = call.get("caller")
            if caller:
                self.add_call(f"{file_path}::{caller}", call["name"])
        if test_name:
            test_functions = [f for f in ast_result.get("functions", []) if f["name"] == test_name]
            for function in test_functions:
                self.add_test_relationship(test_name, file_path, f"{file_path}::{function['name']}")

    def add_call(self, caller_id: str, callee_name: str):
        """Adds a call edge. Note: callee_name might be ambiguous without full module resolution, 
        so we link to any function matching the name for this prototype."""
        # Find potential callees
        callees = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "FUNCTION" and d.get("name") == callee_name]
        for callee in callees:
            self.graph.add_edge(caller_id, callee, relation="CALLS")

    def add_commit_modification(self, commit_sha: str, file_path: str, func_name: str = None):
        self.graph.add_node(commit_sha, type="COMMIT")
        self.graph.add_edge(commit_sha, file_path, relation="MODIFIED_FILE")
        if func_name:
            func_id = f"{file_path}::{func_name}"
            # Only add the edge if the function exists
            if self.graph.has_node(func_id):
                self.graph.add_edge(commit_sha, func_id, relation="MODIFIED_FUNCTION")

    def find_paths_from_test_to_commits(self, test_name: str, max_depth: int = 5) -> List[List[str]]:
        """Finds all paths from a failing test to modified commits."""
        test_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "TEST" and d.get("name") == test_name]
        commit_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "COMMIT"]
        
        paths = []
        # Since this is a directed graph but we want to traverse relationships regardless of direction 
        # (e.g. Test -> Calls -> Function <- ModifiedBy <- Commit)
        # We use an undirected version of the graph for path finding.
        undirected_g = self.graph.to_undirected()
        
        for test_node in test_nodes:
            for commit_node in commit_nodes:
                try:
                    for path in nx.all_simple_paths(undirected_g, test_node, commit_node, cutoff=max_depth):
                        paths.append(path)
                except nx.NetworkXNoPath:
                    continue
        return paths

    def get_related_functions(self, func_id: str) -> List[str]:
        """Gets functions related by calls."""
        if not self.graph.has_node(func_id):
            return []
        
        related = set()
        # Outgoing calls
        for _, callee, data in self.graph.out_edges(func_id, data=True):
            if data.get("relation") == "CALLS":
                related.add(callee)
        
        # Incoming calls
        for caller, _, data in self.graph.in_edges(func_id, data=True):
            if data.get("relation") == "CALLS":
                related.add(caller)
                
        return list(related)

