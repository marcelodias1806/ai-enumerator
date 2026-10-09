from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]

def test_core_pages_exist():
    for name in ["dashboard.html","exposure.html","assessment.html","intelligence.html"]:
        assert (ROOT/"app/static"/name).exists()

def test_core_python_syntax():
    for p in ROOT.rglob("*.py"):
        if "__pycache__" not in p.parts:
            ast.parse(p.read_text(), filename=str(p))

def test_public_governance_files():
    for name in ["LICENSE.md","TRADEMARKS.md","CONTRIBUTING.md","SECURITY.md","CHANGELOG.md"]:
        assert (ROOT/name).exists()
