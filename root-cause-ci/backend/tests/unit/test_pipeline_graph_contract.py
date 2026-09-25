from app.services.ast.project import PythonProjectAnalyzer


def test_bounded_project_analysis_reports_analysis_size(tmp_path):
    source = tmp_path / "src" / "service.py"
    source.parent.mkdir()
    source.write_text("def checkout():\n    return 1\n", encoding="utf-8")

    result = PythonProjectAnalyzer(tmp_path).analyze(["src/service.py"])

    assert result.files_analyzed == ["src/service.py"]
    assert result.functions_analyzed == 1