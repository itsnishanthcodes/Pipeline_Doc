from pathlib import Path

from app.services.ast.project import PythonProjectAnalyzer


def test_project_analysis_resolves_from_import_across_files(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests" / "test_checkout.py").write_text(
        "from src.service import checkout\n\ndef test_checkout_total():\n    checkout()\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "service.py").write_text(
        "from src.analytics import calculate_total\n\ndef checkout():\n    return calculate_total()\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "analytics.py").write_text(
        "def calculate_total():\n    return 8\n",
        encoding="utf-8",
    )

    result = PythonProjectAnalyzer(tmp_path).analyze(
        ["tests/test_checkout.py", "src/service.py", "src/analytics.py"],
        test_file="tests/test_checkout.py",
        test_name="test_checkout_total",
    )

    assert result.status == "RESOLVED"
    assert result.unresolved == []
    assert any(
        path[-1] == "src.analytics::calculate_total"
        for path in result.paths
        if len(path) >= 3
    )


def test_project_analysis_reports_unresolved_call(tmp_path: Path) -> None:
    source = tmp_path / "test_sample.py"
    source.write_text("def test_sample():\n    missing_function()\n", encoding="utf-8")

    result = PythonProjectAnalyzer(tmp_path).analyze(["test_sample.py"], "test_sample.py", "test_sample")

    assert result.status == "PARTIAL"
    assert result.unresolved[0]["callee"] == "missing_function"


def test_project_analysis_expands_only_imported_source(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text(
        "from src.analytics import calculate_total\n\ndef checkout():\n    return calculate_total()\n", encoding="utf-8"
    )
    (tmp_path / "src" / "analytics.py").write_text("def calculate_total():\n    return 1\n", encoding="utf-8")
    (tmp_path / "src" / "unrelated.py").write_text("def unrelated():\n    return 2\n", encoding="utf-8")

    result = PythonProjectAnalyzer(tmp_path).analyze(["src/service.py"], max_files=3, max_import_expansion=1)

    assert "src/analytics.py" in result.expanded_files
    assert "src/unrelated.py" not in result.files_analyzed
    assert result.unresolved_imports == []


def test_project_analysis_marks_import_limit_partial(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("import src.missing\n\ndef checkout():\n    return 1\n", encoding="utf-8")

    result = PythonProjectAnalyzer(tmp_path).analyze(["src/service.py"], max_import_expansion=0)

    assert result.status == "PARTIAL"