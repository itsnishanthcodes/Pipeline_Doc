from app.services.analysis.log_analysis import StackFrame
from app.services.attribution.scorer import AttributionScorer
from app.services.attribution.signals import (
    CandidateCommit,
    CommitFile,
    SignalInputs,
    changed_new_lines,
    module_matches_path,
    score_signals,
)
from app.services.evidence.generator import EvidenceGenerator

CALC_PATCH = "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a + b\n+    return a + b + 1\n"


def test_changed_new_lines_reads_hunks():
    assert changed_new_lines(CALC_PATCH) == {2}
    assert changed_new_lines("@@ -10,3 +10,4 @@\n a\n+b\n c\n+d\n") == {11, 13}
    assert changed_new_lines(None) == set()


def test_module_matches_path():
    assert module_matches_path("src.calc", "src/calc.py")
    assert module_matches_path("calc", "src/calc.py")
    assert module_matches_path("pkg", "pkg/__init__.py")
    assert not module_matches_path("calc", "src/calculator.py")


def test_culprit_is_not_simply_the_latest_commit():
    candidates = [
        CandidateCommit(sha="c1" * 20, message="docs: readme", files=[CommitFile("README.md", "@@ -1 +1 @@\n-a\n+b\n")]),
        CandidateCommit(sha="c2" * 20, message="tweak add", files=[CommitFile("src/calc.py", CALC_PATCH)]),
        CandidateCommit(sha="c3" * 20, message="other test", files=[CommitFile("tests/test_other.py", "@@ -1 +1 @@\n-x\n+y\n")]),
    ]
    inputs = SignalInputs(
        frames=[StackFrame("tests/test_calc.py", 4)],
        log_text="E assert 6 == 5\nE  +  where 6 = add(2, 3)\nFAILED tests/test_calc.py::test_add",
        functions_by_file={"src/calc.py": [{"name": "add", "start_line": 1, "end_line": 2}]},
        test_sources={"tests/test_calc.py": "from src.calc import add\n"},
        newly_failing=True,
    )
    scored = AttributionScorer().score_candidates(score_signals(candidates, inputs))
    best = scored[0]
    assert best["commit_sha"].startswith("c2")
    assert best["signals"]["function_overlap"] == 1.0
    assert best["signals"]["dependency_relationship"] == 1.0
    chain = EvidenceGenerator().generate_chain(best)
    text = " ".join(e["explanation"] for e in chain)
    assert "add" in text and "src/calc.py" in text


def test_stack_trace_line_hit_and_blame():
    candidates = [CandidateCommit(sha="abcdef1234", files=[CommitFile("src/calc.py", CALC_PATCH)])]
    hit = score_signals(candidates, SignalInputs(frames=[StackFrame("src/calc.py", 2)], log_text="",
                                                 functions_by_file={}, test_sources={}))
    assert hit[0]["signals"]["stack_trace_overlap"] == 1.0
    assert hit[0]["signals"]["file_overlap"] == 1.0
    blamed = score_signals(candidates, SignalInputs(frames=[], log_text="", functions_by_file={},
                                                    test_sources={}, blame_sha="abcdef1"))
    assert blamed[0]["signals"]["stack_trace_overlap"] == 1.0
