from app.services.ingestion.log_parser import localize_failure


def test_localization_extracts_exception_test_and_all_frames() -> None:
    result = localize_failure(
        'Traceback (most recent call last):\n'
        '  File "tests/test_checkout.py", line 42, in test_checkout_total\n'
        '  File "src/service.py", line 87, in checkout\n'
        'AssertionError: expected 10 but got 8\n'
        'FAILED tests/test_checkout.py::test_checkout_total'
    )

    assert result.status == "COMPLETE"
    assert result.exception_type == "AssertionError"
    assert result.failed_test == "tests/test_checkout.py::test_checkout_total"
    assert [(frame.file_path, frame.line_number) for frame in result.frames] == [
        ("tests/test_checkout.py", 42),
        ("src/service.py", 87),
    ]


def test_localization_reports_partial_without_stack() -> None:
    result = localize_failure("FAILED tests/test_checkout.py::test_checkout_total")
    assert result.status == "PARTIAL"
    assert result.reason is not None
    assert result.frames == []