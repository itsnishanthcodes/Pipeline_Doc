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
            "imports": [],
            "parse_errors": [],
        }
        self._walk(root_node, code, result, current_function=None, current_class=None)
        return result

    def _walk(
        self,
        node: tree_sitter.Node,
        code: bytes,
        result: Dict[str, Any],
        current_function: str | None,
        current_class: str | None,
    ) -> None:
        if node.has_error and node.type == "ERROR":
            result["parse_errors"].append(self._range(node))

        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, code) if name_node else "<anonymous>"
            qualified_name = f"{current_class}.{name}" if current_class else name
            result["functions"].append({"name": name, "qualified_name": qualified_name, **self._range(node)})
            for child in node.children:
                self._walk(child, code, result, qualified_name, current_class)
            return

        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            name = self._node_text(name_node, code) if name_node else "<anonymous>"
            result["classes"].append({"name": name, **self._range(node)})
            for child in node.children:
                self._walk(child, code, result, current_function, name)
            return

        if node.type == "call":
            function_node = node.child_by_field_name("function")
            name = self._node_text(function_node, code) if function_node else "<unknown>"
            result["calls"].append({"name": name.split(".")[-1], "callee": name, "caller": current_function, **self._range(node)})

        if node.type in {"import_statement", "import_from_statement"}:
            result["imports"].append({"name": self._node_text(node, code), **self._range(node)})

        for child in node.children:
            self._walk(child, code, result, current_function, current_class)

    def _node_text(self, node: tree_sitter.Node | None, code: bytes) -> str:
        return node.text.decode("utf-8") if node is not None and node.text else ""

    def _range(self, node: tree_sitter.Node) -> Dict[str, int]:
        return {
            "start_line": node.start_point.row + 1,
            "start_column": node.start_point.column,
            "end_line": node.end_point.row + 1,
            "end_column": node.end_point.column,
        }
