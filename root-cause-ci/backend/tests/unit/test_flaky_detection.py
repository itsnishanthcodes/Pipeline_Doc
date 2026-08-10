from app.services.flaky.detector import FlakyTestDetector


def test_flaky_detector_scores_intermittent_history_as_flaky() -> None:
    detector = FlakyTestDetector()
    test_name = "tests/test_auth.py::test_invalid_token"

    for outcome in ["PASS", "FAIL", "PASS", "FAIL", "PASS"]:
        detector.record_run(test_name, outcome=outcome, commit_sha="abc123")

    analysis = detector.analyze(test_name)

    assert analysis.flaky_probability >= 0.7
    assert analysis.classification == "LIKELY_FLAKY"
    assert analysis.historical_runs == ["PASS", "FAIL", "PASS", "FAIL", "PASS"]
    assert any(item.signal == "pass_fail_interleaving" for item in analysis.evidence)
