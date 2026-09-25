from app.services.analysis.log_analysis import analyze_log, clean_log, is_test_path, resolve_repo_path

PYTEST_LOG = """2026-09-25T10:00:01.1234567Z ##[group]Run pytest -q
2026-09-25T10:00:02.0000000Z \x1b[31mF\x1b[0m
2026-09-25T10:00:02.1000000Z =================================== FAILURES ===================================
2026-09-25T10:00:02.2000000Z ___________________________________ test_add ___________________________________
2026-09-25T10:00:02.3000000Z     def test_add():
2026-09-25T10:00:02.4000000Z >       assert add(2, 3) == 5
2026-09-25T10:00:02.5000000Z E       assert 6 == 5
2026-09-25T10:00:02.6000000Z E        +  where 6 = add(2, 3)
2026-09-25T10:00:02.7000000Z tests/test_calc.py:4: AssertionError
2026-09-25T10:00:02.8000000Z FAILED tests/test_calc.py::test_add - assert 6 == 5
2026-09-25T10:00:03.0000000Z ##[error]Process completed with exit code 1.
"""

TRACEBACK_LOG = """Traceback (most recent call last):
  File "/home/runner/work/app/app/src/service.py", line 12, in handle
    return parse(value)
  File "/opt/hostedtoolcache/Python/3.12/x64/lib/python3.12/json/__init__.py", line 346, in loads
ValueError: invalid literal
"""


def test_clean_log_strips_timestamps_and_ansi():
    text = clean_log(PYTEST_LOG)
    assert "2026-09-25T" not in text
    assert "\x1b[" not in text


def test_analyze_log_extracts_failed_test_frames_and_error():
    result = analyze_log(PYTEST_LOG)
    assert result.failed_tests == ["tests/test_calc.py::test_add"]
    assert any(f.file == "tests/test_calc.py" and f.line == 4 for f in result.frames)
    assert result.error_message == "assert 6 == 5"
    assert any(s["name"] == "assertion_failure" for s in result.error_signatures)


def test_traceback_frames_are_repo_relative_and_skip_external_files():
    result = analyze_log(TRACEBACK_LOG)
    files = [f.file for f in result.frames]
    assert "src/service.py" in files
    assert not any("hostedtoolcache" in f for f in files)
    assert result.error_message == "ValueError: invalid literal"


def test_error_message_keeps_leading_letter_e():
    result = analyze_log("EOFError: unexpected end of input\n")
    assert result.error_message == "EOFError: unexpected end of input"


def test_resolve_repo_path_matches_suffixes():
    tree = ["src/app/service.py", "tests/test_service.py", "README.md"]
    assert resolve_repo_path("app/service.py", tree) == "src/app/service.py"
    assert resolve_repo_path("/home/runner/work/x/x/tests/test_service.py", tree) == "tests/test_service.py"
    assert resolve_repo_path("missing.py", tree) is None


def test_is_test_path():
    assert is_test_path("tests/test_calc.py")
    assert is_test_path("pkg/calc_test.py")
    assert not is_test_path("src/calc.py")
