from __future__ import annotations

import re
from typing import Iterable

from app.schemas.ingestion import ErrorSignature
from app.schemas.localization import FailureLocalization, StackFrame

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

EXCEPTION_PATTERN = re.compile(r"(?m)^\s*(?P<type>[A-Za-z_][\w.]*(?:Error|Exception|Failure))(?::\s*(?P<message>.*))?$")

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


def extract_stack_frames(log_text: str | None) -> list[StackFrame]:
    if not log_text:
        return []
    frames: list[StackFrame] = []
    for line in log_text.splitlines():
        for pattern in STACK_TRACE_PATTERNS:
            match = pattern.search(line)
            if match:
                frames.append(
                    StackFrame(
                        file_path=match.group("file"),
                        line_number=int(match.group("line")),
                        function=match.groupdict().get("context"),
                        raw=line.strip(),
                    )
                )
                break
    return frames


def localize_failure(log_text: str | None) -> FailureLocalization:
    text = log_text or ""
    exception = next((match for match in EXCEPTION_PATTERN.finditer(text)), None)
    frames = extract_stack_frames(text)
    test_name = extract_failed_test_name(text)
    if not frames and not exception and not test_name:
        return FailureLocalization(status="PARTIAL", reason="No usable stack trace or failure marker.")
    return FailureLocalization(
        status="COMPLETE" if frames else "PARTIAL",
        reason=None if frames else "No usable stack trace; only test or exception markers were found.",
        exception_type=exception.group("type") if exception else None,
        exception_message=exception.group("message") if exception else None,
        failed_test=test_name,
        frames=frames,
    )


def first_non_empty(values: Iterable[str | None]) -> str | None:
    for value in values:
        if value:
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None
