"""Tests for SCAD analyzer."""
import sys
import tempfile
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scad_analyzer import analyze_file, analyze_directory


def _write_scad(tmpdir, name, content):
    p = Path(tmpdir) / name
    p.write_text(content)
    return p


class TestVariableExtraction:
    def test_numeric_int(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "rows = 8;\n")
        result = analyze_file(f)
        assert len(result["variables"]) == 1
        v = result["variables"][0]
        assert v["name"] == "rows"
        assert v["type"] == "number"
        assert v["value"] == 8

    def test_numeric_float(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "thick = 2.5;\n")
        result = analyze_file(f)
        v = result["variables"][0]
        assert v["type"] == "number"
        assert v["value"] == 2.5

    def test_bool(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "show_base = true;\n")
        result = analyze_file(f)
        v = result["variables"][0]
        assert v["type"] == "bool"
        assert v["value"] is True

    def test_string(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", 'letter = "V";\n')
        result = analyze_file(f)
        v = result["variables"][0]
        assert v["type"] == "string"
        assert v["value"] == "V"

    def test_comment(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "gap = 2; // Gap in mm\n")
        result = analyze_file(f)
        v = result["variables"][0]
        assert v["comment"] == "Gap in mm"

    def test_expression(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "total = rows * size;\n")
        result = analyze_file(f)
        v = result["variables"][0]
        assert v["type"] == "expression"


class TestModuleExtraction:
    def test_simple_module(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "module box(size=10) {\n  cube(size);\n}\n")
        result = analyze_file(f)
        assert len(result["modules"]) == 1
        m = result["modules"][0]
        assert m["name"] == "box"
        assert len(m["parameters"]) == 1
        assert m["parameters"][0]["name"] == "size"
        assert m["parameters"][0]["default"] == "10"

    def test_no_default(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "module foo(x, y) {\n}\n")
        result = analyze_file(f)
        m = result["modules"][0]
        assert m["parameters"][0]["default"] is None
        assert m["parameters"][1]["name"] == "y"


class TestIncludesUses:
    def test_include(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "include <lib.scad>\n")
        result = analyze_file(f)
        assert result["includes"] == ["lib.scad"]

    def test_use(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "use <utils.scad>\n")
        result = analyze_file(f)
        assert result["uses"] == ["utils.scad"]


class TestRenderModes:
    def test_detect(self, tmp_path):
        content = """
render_mode = 0;
if (render_mode == 0 || render_mode == 1) cube(10);
if (render_mode == 0 || render_mode == 2) sphere(5);
"""
        f = _write_scad(tmp_path, "test.scad", content)
        result = analyze_file(f)
        assert result["render_modes"] == [0, 1, 2]

    def test_no_render_mode(self, tmp_path):
        f = _write_scad(tmp_path, "test.scad", "cube(10);\n")
        result = analyze_file(f)
        assert result["render_modes"] == []


class TestDirectoryAnalysis:
    def test_dependency_graph(self, tmp_path):
        _write_scad(tmp_path, "lib.scad", "module helper() { cube(1); }\n")
        _write_scad(tmp_path, "main.scad", "include <lib.scad>\nhelper();\n")
        result = analyze_directory(tmp_path)
        assert "lib.scad" in result["dependency_graph"]["main.scad"]
        assert "main.scad" in result["entry_points"]

    def test_entry_points(self, tmp_path):
        _write_scad(tmp_path, "entry.scad", "render_mode = 0;\nif (render_mode == 1) cube(1);\n")
        _write_scad(tmp_path, "lib.scad", "module foo() { sphere(1); }\n")
        result = analyze_directory(tmp_path)
        assert "entry.scad" in result["entry_points"]
