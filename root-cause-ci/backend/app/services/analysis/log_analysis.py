"""Deterministic parsing of GitHub Actions job logs.

Everything here is pure (no I/O) so it can be unit-tested and reused by the offline evaluation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.ingestion.log_parser import ERROR_SIGNATURES

TIMESTAMP_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ?", re.MULTILINE)
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
GROUP_MARKER = re.compile(r"^##\[(?:group|endgroup)\].*$", re.MULTILINE)

# Python traceback frame, pytest "file:line: in func" frames and generic "file.ext:line" references.
PY_FRAME = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+)(?:, in (?P<func>[\w<>.]+))?')
PYTEST_FRAME = re.compile(r"^(?P<file>[\w./\\-]+\.py):(?P<line>\d+):(?: in (?P<func>[\w<>.]+)| \w+)?", re.MULTILINE)
GENERIC_FRAME = re.compile(r"(?P<file>[\w./\\-]+\.(?:py|js|jsx|ts|tsx|java|go|rb)):(?P<line>\d+)")
FAILED_TEST = re.compile(r"^(?:FAILED|ERROR)\s+(?P<test>[\w./\\-]+(?:::[\w\[\]\-.]+)+)", re.MULTILINE)
RUNNER_PREFIX = re.compile(r"^.*?/(?:work|workspace)/[^/]+/[^/]+/")
EXTERNAL_PATH_HINTS = ("site-packages", "dist-packages", "/usr/lib/", "/opt/hostedtoolcache", "<frozen", "node_modules")

KEY_LINE_WORDS = (
    "error", "exception", "failed", "failure", "assert", "traceback", "no module",
    "exit code", "not found", "not set", "denied", "timed out", "cannot",
)


@dataclass(slots=True)
class StackFrame:
    file: str
    line: int
    function: str | None = None


@dataclass(slots=True)
class LogAnalysis:
    clean_log: str
    key_lines: list[str] = field(default_factory=list)
    error_signatures: list[dict] = field(default_factory=list)
    failed_tests: list[str] = field(default_factory=list)
    frames: list[StackFrame] = field(default_factory=list)
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "key_lines": self.key_lines,
            "error_signatures": self.error_signatures,
            "failed_tests": self.failed_tests,
            "frames": [{"file": f.file, "line": f.line, "function": f.function} for f in self.frames],
            "error_message": self.error_message,
        }


def clean_log(raw: str) -> str:
    text = ANSI_ESCAPE.sub("", raw or "")
    text = TIMESTAMP_PREFIX.sub("", text)
    return GROUP_MARKER.sub("", text)


def normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    path = RUNNER_PREFIX.sub("", path)
    return path.lstrip("./")


def is_external(path: str) -> bool:
    return any(hint in path for hint in EXTERNAL_PATH_HINTS) or path.startswith("/usr/")


def extract_frames(text: str) -> list[StackFrame]:
    frames: list[StackFrame] = []
    seen: set[tuple[str, int]] = set()
    for pattern in (PY_FRAME, PYTEST_FRAME, GENERIC_FRAME):
        for m in pattern.finditer(text):
            raw_file = m.group("file")
            if is_external(raw_file):
                continue
            file = normalize_path(raw_file)
            line = int(m.group("line"))
            if (file, line) in seen:
                continue
            seen.add((file, line))
            func = m.groupdict().get("func")
            frames.append(StackFrame(file=file, line=line, function=func if func and func != "<module>" else None))
    return frames


def extract_key_lines(text: str, limit: int = 30) -> list[str]:
    lines = [ln.rstrip() for ln in text.splitlines()]
    picked: list[str] = []
    for ln in lines:
        low = ln.lower()
        if not ln.strip() or low.startswith(("##[debug]", "shell:", "env:")):
            continue
        if any(w in low for w in KEY_LINE_WORDS) or PY_FRAME.search(ln) or ln.lstrip().startswith(("E ", ">")):
            picked.append(ln.strip())
    if not picked:
        picked = [ln.strip() for ln in lines if ln.strip()][-limit:]
    # keep the tail: the decisive error is usually close to the end of the log
    return picked[-limit:]


EXCEPTION_LINE = re.compile(r"^(?:[\w.]+\.)?\w*(?:Error|Exception)\b:?")
PYTEST_E_LINE = re.compile(r"^E\s+")


def extract_error_message(key_lines: list[str]) -> str | None:
    """The single most informative error line."""
    # 1. a Python exception line such as "ValueError: invalid literal"
    for ln in reversed(key_lines):
        if EXCEPTION_LINE.match(ln):
            return ln.strip()
    # 2. pytest assertion detail: first line of the last block of "E  ..." lines
    idx = None
    for i in range(len(key_lines) - 1, -1, -1):
        if PYTEST_E_LINE.match(key_lines[i]):
            idx = i
            while idx > 0 and PYTEST_E_LINE.match(key_lines[idx - 1]):
                idx -= 1
            break
    if idx is not None:
        return PYTEST_E_LINE.sub("", key_lines[idx]).strip()
    # 3. an explicit error annotation from the runner, other than the generic exit-code line
    for ln in reversed(key_lines):
        low = ln.lower()
        if "error" in low and "process completed with exit code" not in low:
            return ln.replace("##[error]", "").strip()
    return key_lines[-1] if key_lines else None


def analyze_log(raw_log: str) -> LogAnalysis:
    text = clean_log(raw_log)
    key_lines = extract_key_lines(text)
    signatures = []
    for name, pattern in ERROR_SIGNATURES:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            signatures.append({"name": name, "matched_text": m.group(0)[:200]})
    failed = []
    for m in FAILED_TEST.finditer(text):
        t = normalize_path(m.group("test"))
        if t not in failed:
            failed.append(t)
    return LogAnalysis(
        clean_log=text,
        key_lines=key_lines,
        error_signatures=signatures,
        failed_tests=failed,
        frames=extract_frames(text),
        error_message=extract_error_message(key_lines),
    )


def resolve_repo_path(path: str, tree_paths: list[str] | set[str]) -> str | None:
    """Map a path seen in a log (possibly absolute or partial) onto a file that exists in the repository."""
    if not path:
        return None
    tree = set(tree_paths)
    norm = normalize_path(path)
    if norm in tree:
        return norm
    matches = [p for p in tree if p.endswith("/" + norm) or norm.endswith("/" + p)]
    if len(matches) == 1:
        return matches[0]
    if matches:
        return min(matches, key=len)
    return None


def is_test_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return "/tests/" in f"/{path}" or "/test/" in f"/{path}" or name.startswith("test_") or name.endswith(
        ("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js")
    )
