from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import networkx as nx

from app.services.ast.parser import ASTParser


@dataclass(slots=True)
class ProjectAnalysisResult:
    status: str
    graph: nx.MultiDiGraph
    paths: list[list[str]] = field(default_factory=list)
    unresolved: list[dict[str, str]] = field(default_factory=list)
    files_analyzed: list[str] = field(default_factory=list)
    functions_analyzed: int = 0
    initial_files: list[str] = field(default_factory=list)
    expanded_files: list[str] = field(default_factory=list)
    unresolved_imports: list[str] = field(default_factory=list)
    expansion_depth: int = 0
    expansion_reasons: list[str] = field(default_factory=list)


class PythonProjectAnalyzer:
    """Resolve a bounded set of Python files into a source-aware call graph."""

    def __init__(self, root: str | Path, parser: ASTParser | None = None) -> None:
        self.root = Path(root).resolve()
        self.parser = parser or ASTParser()

    def analyze(
        self,
        file_paths: list[str | Path],
        test_file: str | None = None,
        test_name: str | None = None,
        max_depth: int = 4,
        max_files: int = 12,
        max_import_expansion: int = 8,
    ) -> ProjectAnalysisResult:
        graph = nx.MultiDiGraph()
        unresolved: list[dict[str, str]] = []
        parsed: dict[str, dict[str, Any]] = {}
        module_for_file: dict[str, str] = {}

        initial_files = [Path(path).as_posix() for path in file_paths]
        expansion_reasons: list[str] = []
        unresolved_imports: list[str] = []
        pending = list(initial_files)
        expanded_files: list[str] = []
        depth = 0
        while pending and len(parsed) < max_files:
            raw_path = pending.pop(0)
            path = self._safe_path(raw_path)
            if path is None or path.suffix != ".py" or not path.exists():
                continue
            relative = path.relative_to(self.root).as_posix()
            if relative in parsed:
                continue
            module = self._module_name(relative)
            parsed[relative] = self.parser.parse_file(path)
            module_for_file[relative] = module
            if relative not in initial_files:
                expanded_files.append(relative)
            graph.add_node(relative, type="FILE", file=relative, module=module)
            imports = self._imports(parsed[relative].get("imports", []))
            if relative not in initial_files and imports:
                depth = max(depth, 1)
            for imported_module in imports.values():
                source = self._module_to_path(imported_module)
                if source is None:
                    unresolved_imports.append(imported_module)
                    continue
                if source and source not in parsed and source not in pending:
                    if len(expanded_files) < max_import_expansion:
                        pending.append(source)
                        expansion_reasons.append(f"{relative} imports {imported_module}")
                    else:
                        unresolved_imports.append(imported_module)

        functions: dict[str, str] = {}
        by_module_name: dict[tuple[str, str], str] = {}
        for relative, ast_result in parsed.items():
            module = module_for_file[relative]
            for function in ast_result.get("functions", []):
                qualified = function.get("qualified_name", function["name"])
                node_id = f"{module}::{qualified}"
                functions[node_id] = relative
                by_module_name[(module, qualified)] = node_id
                by_module_name.setdefault((module, function["name"]), node_id)
                graph.add_node(
                    node_id,
                    type="FUNCTION",
                    file=relative,
                    module=module,
                    function=qualified,
                    source_range={key: function[key] for key in ("start_line", "end_line", "start_column", "end_column") if key in function},
                )
                graph.add_edge(node_id, relative, relation="DEFINES")

        import_maps = {relative: self._imports(ast_result.get("imports", [])) for relative, ast_result in parsed.items()}
        for relative, ast_result in parsed.items():
            module = module_for_file[relative]
            local_functions = [node for node, file in functions.items() if file == relative]
            for call in ast_result.get("calls", []):
                caller = call.get("caller")
                if not caller:
                    continue
                caller_id = by_module_name.get((module, caller))
                if not caller_id:
                    continue
                target = self._resolve_call(call.get("callee", call.get("name", "")), module, relative, import_maps[relative], by_module_name, local_functions)
                if target:
                    graph.add_edge(caller_id, target, relation="CALLS")
                else:
                    unresolved.append({"file": relative, "caller": caller, "callee": call.get("callee", "")})

        paths: list[list[str]] = []
        if test_file and test_name:
            test_relative = Path(test_file).as_posix()
            test_module = module_for_file.get(test_relative)
            test_node = by_module_name.get((test_module or "", test_name))
            if test_node:
                graph.nodes[test_node]["type"] = "TEST"
                for target in graph.nodes:
                    if graph.nodes[target].get("type") != "FUNCTION" or target == test_node:
                        continue
                    try:
                        paths.append(nx.shortest_path(graph, test_node, target))
                    except nx.NetworkXNoPath:
                        continue
                paths.sort(key=len)

        status = "RESOLVED" if paths else ("PARTIAL" if unresolved or unresolved_imports or test_name else "RESOLVED")
        if len(parsed) >= max_files and pending:
            status = "PARTIAL"
        return ProjectAnalysisResult(
            status=status,
            graph=graph,
            paths=paths[:max(1, len(paths))],
            unresolved=unresolved,
            files_analyzed=list(parsed),
            functions_analyzed=len(functions),
            initial_files=initial_files,
            expanded_files=expanded_files,
            unresolved_imports=unresolved_imports,
            expansion_depth=depth,
            expansion_reasons=expansion_reasons,
        )

    def _safe_path(self, raw_path: str | Path) -> Path | None:
        candidate = (self.root / Path(raw_path)).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            return None
        return candidate

    def _module_name(self, relative: str) -> str:
        value = relative[:-3] if relative.endswith(".py") else relative
        if value.endswith("/__init__"):
            value = value[:-9]
        return value.replace("/", ".")

    def _module_to_path(self, module: str) -> str | None:
        parts = module.split(".")
        for end in range(len(parts), 0, -1):
            normalized = "/".join(parts[:end])
            candidates = (f"{normalized}.py", f"{normalized}/__init__.py")
            for candidate in candidates:
                safe = self._safe_path(candidate)
                if safe and safe.exists():
                    return candidate
        return None

    def _imports(self, imports: list[dict[str, Any]]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for item in imports:
            text = item.get("name", "").strip()
            if text.startswith("import "):
                for part in text[7:].split(","):
                    pieces = part.strip().split(" as ")
                    module = pieces[0].strip()
                    aliases[pieces[-1].strip().split(".")[0]] = module
            elif text.startswith("from ") and " import " in text:
                module, names = text[5:].split(" import ", 1)
                for part in names.split(","):
                    pieces = part.strip().split(" as ")
                    aliases[pieces[-1].strip()] = f"{module.strip()}.{pieces[0].strip()}"
        return aliases

    def _resolve_call(self, callee: str, module: str, relative: str, aliases: dict[str, str], index: dict[tuple[str, str], str], local_functions: list[str]) -> str | None:
        if callee in aliases:
            target = aliases[callee]
            target_module, _, target_name = target.rpartition(".")
            return index.get((target_module, target_name)) or index.get((target_module, callee))
        if "." in callee:
            prefix, name = callee.rsplit(".", 1)
            imported_module = aliases.get(prefix, prefix)
            return index.get((imported_module, name))
        local = [node for node in local_functions if node.rsplit("::", 1)[-1] == callee or node.rsplit("::", 1)[-1].endswith(f".{callee}")]
        return local[0] if len(local) == 1 else None