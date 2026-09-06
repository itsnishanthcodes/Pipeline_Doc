import tree_sitter
import tree_sitter_python
from pathlib import Path
from typing import List, Dict, Any

class ASTParser:
    def __init__(self):
        # Initialize the Python language parser
        self.language = tree_sitter.Language(tree_sitter_python.language())
        self.parser = tree_sitter.Parser()
        self.parser.language = self.language

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Python file and extract functions, classes, and calls."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        code = file_path.read_bytes()
        tree = self.parser.parse(code)
        
        return self._extract_nodes(tree.root_node, code)

    def parse_code(self, code: str) -> Dict[str, Any]:
        """Parse a string of Python code and extract nodes."""
        code_bytes = code.encode('utf-8')
        tree = self.parser.parse(code_bytes)
        
        return self._extract_nodes(tree.root_node, code_bytes)

    def _extract_nodes(self, root_node: tree_sitter.Node, code: bytes) -> Dict[str, Any]:
        result = {
            "functions": [],
            "classes": [],
            "calls": [],
        }

        # Query to extract function/class definitions and function calls
        query_code = """
        (function_definition
            name: (identifier) @function.def)
            
        (class_definition
            name: (identifier) @class.def)
            
        (call
            function: [
                (identifier) @function.call
                (attribute attribute: (identifier) @function.call)
            ])
        """
        query = tree_sitter.Query(self.language, query_code)
        cursor = tree_sitter.QueryCursor(query)
        captures = cursor.captures(root_node)

        # captures is a dict mapping string names to lists of Nodes
        if isinstance(captures, dict):
            for tag, nodes in captures.items():
                for node in nodes:
                    self._process_node(node, tag, result)
        else:
            for node, tag in captures:
                self._process_node(node, tag, result)

        return result

    def _process_node(self, node: tree_sitter.Node, tag: str, result: Dict[str, Any]):
        name = node.text.decode('utf-8')
        start_point = node.start_point
        end_point = node.end_point
        
        node_info = {
            "name": name,
            "start_line": start_point.row + 1,
            "end_line": end_point.row + 1
        }
        
        if tag == "function.def":
            result["functions"].append(node_info)
        elif tag == "class.def":
            result["classes"].append(node_info)
        elif tag == "function.call":
            result["calls"].append(node_info)
