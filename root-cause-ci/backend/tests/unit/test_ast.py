import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from app.services.ast.parser import ASTParser

def test_ast_parser_extracts_functions_and_calls():
    parser = ASTParser()
    
    code = """
class MyService:
    def process_data(self):
        self.validate()
        save_db()

def validate():
    pass

def save_db():
    pass
"""
    result = parser.parse_code(code)
    
    func_names = [f["name"] for f in result["functions"]]
    assert "process_data" in func_names
    assert "validate" in func_names
    assert "save_db" in func_names
    
    class_names = [c["name"] for c in result["classes"]]
    assert "MyService" in class_names
    
    call_names = [c["name"] for c in result["calls"]]
    assert "validate" in call_names
    assert "save_db" in call_names
    assert any(call["caller"] == "MyService.process_data" for call in result["calls"] if call["name"] == "validate")


def test_ast_parser_extracts_imports_and_ranges():
    result = ASTParser().parse_code("import os\n\ndef run():\n    os.getcwd()\n")
    assert result["imports"][0]["name"] == "import os"
    assert result["functions"][0]["start_line"] == 3
    assert result["calls"][0]["callee"] == "os.getcwd"

