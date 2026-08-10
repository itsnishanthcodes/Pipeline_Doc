from __future__ import annotations

import re
from typing import Iterable

from app.schemas.ingestion import ErrorSignature

ERROR_SIGNATURES: tuple[tuple[str, str], ...] = (
    ("assertion_failure", r"AssertionError|assert .* failed|expected .* but got .*"),
    ("traceback", r"Traceback \(most recent call last\):"),
    ("missing_env", r"(?:Missing|Required) environment variable|environment variable .* not set"),
    ("docker_unavailable", r"Docker daemon|Cannot connect to the Docker daemon|docker: command not found"),
    ("dependency_failure", r"Could not find a version that satisfies|No matching distribution found|ModuleNotFoundError"),
    ("timeout", r"timed out after|TimeoutError|exceeded the timeout"),
)

STACK_TRACE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<context>[^\n]+)'),
    re.compile(r'(?P<file>[\w./\\-]+\.(?:py|js|ts|tsx|jsx)):(?P<line>\d+)'),
)

FAILED_TEST_PATTERN = re.compile(r"(?:FAILED|FAIL):?\s+(?P<test>[A-Za-z0-9_./:-]+)")


def extract_error_signatures(log_text: str | None) -> list[ErrorSignature]:
    if not log_text:
        return []

    signatures: list[ErrorSignature] = []
    for name, pattern in ERROR_SIGNATURES:
        match = re.search(pattern, log_text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            signatures.append(ErrorSignature(name=name, pattern=pattern, matched_text=match.group(0)))
    return signatures


def extract_failed_test_name(log_text: str | None) -> str | None:
    if not log_text:
        return None
    match = FAILED_TEST_PATTERN.search(log_text)
    if match:
        return match.group("test")
    return None


def extract_stack_trace(log_text: str | None) -> tuple[str | None, str | None, int | None]:
    if not log_text:
        return None, None, None

    for pattern in STACK_TRACE_PATTERNS:
        match = pattern.search(log_text)
        if match:
            file_path = match.groupdict().get("file")
            line_number = match.groupdict().get("line")
            return log_text, file_path, int(line_number) if line_number else None
    return log_text, None, None


def first_non_empty(values: Iterable[str | None]) -> str | None:
    for value in values:
        if value:
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None
