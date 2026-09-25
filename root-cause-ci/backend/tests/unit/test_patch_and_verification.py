from app.services.analysis.log_analysis import StackFrame
from app.services.patch.patch_service import choose_target_file, unified_diff, validate_patch
from app.services.verification import verification_from_runs

ORIGINAL = "def add(a, b):\n    return a + b + 1\n"
FIXED = "def add(a, b):\n    return a + b\n"


def test_target_prefers_deepest_source_frame():
    frames = [StackFrame("tests/test_calc.py", 4), StackFrame("src/calc.py", 2)]
    assert choose_target_file(frames, None) == "src/calc.py"


def test_target_uses_imported_changed_file_when_trace_only_has_tests():
    frames = [StackFrame("tests/test_calc.py", 4)]
    best = {"changed_files": ["tests/test_other.py", "src/calc.py"]}
    assert choose_target_file(frames, best, ["src/calc.py"]) == "src/calc.py"
    assert choose_target_file(frames, best) == "src/calc.py"
    assert choose_target_file([], None) is None


def test_validate_patch_accepts_scoped_valid_change():
    content, reason = validate_patch("src/calc.py", ORIGINAL, {"file_path": "src/calc.py", "new_content": FIXED},
                                     {"src/calc.py"})
    assert reason is None and content == FIXED


def test_validate_patch_rejects_out_of_scope_identical_and_broken_code():
    _, reason = validate_patch("src/calc.py", ORIGINAL, {"file_path": "tests/test_calc.py", "new_content": FIXED},
                               {"src/calc.py"})
    assert "outside the allowed scope" in reason
    _, reason = validate_patch("src/calc.py", ORIGINAL, {"file_path": "src/calc.py", "new_content": ORIGINAL},
                               {"src/calc.py"})
    assert "identical" in reason
    _, reason = validate_patch("src/calc.py", ORIGINAL, {"file_path": "src/calc.py", "new_content": "def add(:\n"},
                               {"src/calc.py"})
    assert "syntax" in reason


def test_unified_diff_shows_change():
    diff = unified_diff("src/calc.py", ORIGINAL, FIXED)
    assert "-    return a + b + 1" in diff and "+    return a + b" in diff


def test_verification_states():
    sha = "fix123"
    assert verification_from_runs([], sha)["status"] == "pending"
    assert verification_from_runs([{"head_sha": "other", "status": "completed", "conclusion": "success"}], sha)[
        "status"] == "pending"
    running = [{"head_sha": sha, "status": "in_progress", "conclusion": None}]
    assert verification_from_runs(running, sha)["status"] == "running"
    ok = [{"head_sha": sha, "status": "completed", "conclusion": "success"}]
    assert verification_from_runs(ok, sha)["status"] == "verified"
    bad = ok + [{"head_sha": sha, "status": "completed", "conclusion": "failure", "name": "CI"}]
    assert verification_from_runs(bad, sha)["status"] == "failed"
