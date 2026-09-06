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

