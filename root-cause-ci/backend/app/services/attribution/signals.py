"""Pure computation of attribution signals for candidate commits.

The analyzer gathers the data from GitHub (commit files, patches, file contents, blame) and passes it
here; this module only does deterministic arithmetic so it can be unit-tested and evaluated offline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.analysis.log_analysis import StackFrame, is_test_path

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*(?:from\s+(?P<from>[\w.]+)\s+import|import\s+(?P<imp>[\w.]+))", re.MULTILINE)


@dataclass(slots=True)
class CommitFile:
    path: str
    patch: str | None = None
    status: str = "modified"


@dataclass(slots=True)
class CandidateCommit:
    sha: str
    message: str = ""
    author: str | None = None
    date: str | None = None
    files: list[CommitFile] = field(default_factory=list)


def changed_new_lines(patch: str | None) -> set[int]:
    """Line numbers on the new side of a unified-diff patch that were added or modified."""
    lines: set[int] = set()
    if not patch:
        return lines
    current = None
    for raw in patch.splitlines():
        header = HUNK_HEADER.match(raw)
        if header:
            current = int(header.group("start"))
            continue
        if current is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            lines.add(current)
            current += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            # a deletion affects the line that now sits at this position
            lines.add(current)
        else:
            current += 1
    return lines


def functions_touched(changed_lines: set[int], functions: list[dict]) -> list[str]:
    names = []
    for fn in functions:
        start, end = fn.get("start_line", 0), fn.get("end_line", 0)
        if any(start <= ln <= end for ln in changed_lines) and fn["name"] not in names:
            names.append(fn["name"])
    return names


def imported_modules(source: str | None) -> set[str]:
    mods: set[str] = set()
    for m in IMPORT_RE.finditer(source or ""):
        mod = m.group("from") or m.group("imp")
        if mod:
            mods.add(mod)
    return mods


def module_matches_path(module: str, path: str) -> bool:
    """True when `import module` would plausibly resolve to repository file `path`."""
    if not path.endswith(".py"):
        return False
    mod_path = module.replace(".", "/")
    stem = path[:-3]
    if stem.endswith("/__init__"):
        stem = stem[: -len("/__init__")]
    return stem == mod_path or stem.endswith("/" + mod_path)


@dataclass(slots=True)
class SignalInputs:
    frames: list[StackFrame]                       # repo-relative frames from the failing log
    log_text: str                                  # cleaned log (key lines are enough)
    functions_by_file: dict[str, list[dict]]       # AST functions of files at the failing commit
    test_sources: dict[str, str]                   # failing test file path -> source
    blame_sha: str | None = None                   # commit that last touched the primary frame line
    newly_failing: bool = False                    # previous run of this workflow on the branch passed


def score_signals(candidates: list[CandidateCommit], inputs: SignalInputs) -> list[dict]:
    """Return one dict per candidate with raw signals in [0, 1] and human-readable reasons."""
    n = len(candidates)
    frame_files = {f.file for f in inputs.frames}
    frame_lines: dict[str, set[int]] = {}
    for f in inputs.frames:
        frame_lines.setdefault(f.file, set()).add(f.line)
    log_lower = inputs.log_text.lower()
    test_imports: set[str] = set()
    for src in inputs.test_sources.values():
        test_imports |= imported_modules(src)

    results = []
    for idx, commit in enumerate(candidates):
        reasons: dict[str, str] = {}
        paths = [cf.path for cf in commit.files]

        # temporal proximity: candidates are ordered oldest -> newest
        temporal = round((idx + 1) / n, 3) if n > 1 else 1.0
        reasons["temporal_proximity"] = (
            f"Commit is {n - idx} of {n} in the range between the last green run and the failure"
            if n > 1 else "Only commit between the last green run and the failure"
        )

        # file overlap: files touched by the commit that appear in stack frames (strong) or by name in the log (weak)
        in_frames = [p for p in paths if p in frame_files]
        # whole-name match only: "calc.py" must not match inside "test_calc.py"
        by_name = [p for p in paths if p not in in_frames and re.search(
            rf"(?<![\w.-]){re.escape(p.rsplit('/', 1)[-1].lower())}(?![\w-])", log_lower)]
        file_overlap = 1.0 if in_frames else (0.5 if by_name else 0.0)
        if in_frames:
            reasons["file_overlap"] = f"Modified {', '.join(in_frames[:3])}, which appears in the failure stack trace"
        elif by_name:
            reasons["file_overlap"] = f"Modified {', '.join(by_name[:3])}, which is named in the failure log"

        # stack trace overlap: changed lines hit by a frame, or blame of the primary frame points here
        hit = []
        for cf in commit.files:
            touched = changed_new_lines(cf.patch)
            for line in sorted(frame_lines.get(cf.path, set())):
                if line in touched:
                    hit.append(f"{cf.path}:{line}")
        blamed = bool(inputs.blame_sha) and (
            commit.sha.startswith(inputs.blame_sha) or inputs.blame_sha.startswith(commit.sha)
        )
        stack_overlap = 1.0 if (hit or blamed) else 0.0
        if hit:
            reasons["stack_trace_overlap"] = f"Changed line(s) {', '.join(hit[:3])} appear in the stack trace"
        elif blamed:
            reasons["stack_trace_overlap"] = "Git blame of the failing line points to this commit"

        # function overlap: functions changed by the commit whose names appear in the log
        changed_funcs: list[str] = []
        for cf in commit.files:
            changed_funcs += functions_touched(changed_new_lines(cf.patch), inputs.functions_by_file.get(cf.path, []))
        named = [fn for fn in changed_funcs if re.search(rf"\b{re.escape(fn)}\b", inputs.log_text)]
        function_overlap = 1.0 if named else 0.0
        if named:
            reasons["function_overlap"] = f"Changed function(s) {', '.join(named[:3])} appear in the failure output"

        # dependency relationship: the failing test imports a module this commit changed
        deps = [p for p in paths if not is_test_path(p) and any(module_matches_path(m, p) for m in test_imports)]
        dependency = 1.0 if deps else 0.0
        if deps:
            reasons["dependency_relationship"] = f"The failing test imports {', '.join(deps[:3])}, modified by this commit"

        historical = 1.0 if inputs.newly_failing else 0.0
        if historical:
            reasons["historical_evidence"] = "The previous run of this workflow on the branch passed, so the failure is new"

        results.append({
            "commit_sha": commit.sha,
            "message": commit.message.splitlines()[0][:120] if commit.message else "",
            "author": commit.author,
            "date": commit.date,
            "changed_files": paths,
            "changed_functions": changed_funcs,
            "signals": {
                "temporal_proximity": temporal,
                "file_overlap": file_overlap,
                "stack_trace_overlap": stack_overlap,
                "function_overlap": function_overlap,
                "dependency_relationship": dependency,
                "historical_evidence": historical,
            },
            "reasons": reasons,
        })
    return results
