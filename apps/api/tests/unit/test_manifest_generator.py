"""Tests for manifest generator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.manifest_generator import generate_manifest


def _write_scad(tmpdir, name, content):
    p = Path(tmpdir) / name
    p.write_text(content)
    return p


class TestManifestGeneration:
    def test_basic_project(self, tmp_path):
        _write_scad(tmp_path, "main.scad", """
size = 20;
thick = 2.5;
show_base = true;
render_mode = 0;
if (render_mode == 0 || render_mode == 1) cube(size);
if (render_mode == 0 || render_mode == 2) sphere(size);
""")
        result = generate_manifest(tmp_path, slug="test")
        manifest = result["manifest"]

        assert manifest["project"]["slug"] == "test"
        assert len(manifest["modes"]) >= 1
        assert len(manifest["parts"]) >= 1

        # Check parameters were extracted
        param_ids = [p["id"] for p in manifest["parameters"]]
        assert "size" in param_ids
        assert "thick" in param_ids
        assert "show_base" in param_ids

        # Check slider params have ranges
        size_param = next(p for p in manifest["parameters"] if p["id"] == "size")
        assert size_param["type"] == "slider"
        assert size_param["min"] == 10.0
        assert size_param["max"] == 40.0

        # Check bool param
        base_param = next(p for p in manifest["parameters"] if p["id"] == "show_base")
        assert base_param["type"] == "checkbox"
        assert base_param["default"] is True

    def test_warnings_generated(self, tmp_path):
        _write_scad(tmp_path, "simple.scad", "cube(10);\n")
        result = generate_manifest(tmp_path, slug="simple")
        assert len(result["warnings"]) > 0

    def test_multi_file(self, tmp_path):
        _write_scad(tmp_path, "lib.scad", "module helper() { cube(1); }\n")
        _write_scad(tmp_path, "main.scad", """
include <lib.scad>
render_mode = 0;
if (render_mode == 1) helper();
""")
        result = generate_manifest(tmp_path, slug="multi")
        manifest = result["manifest"]
        # main.scad should be an entry point mode
        mode_ids = [m["id"] for m in manifest["modes"]]
        assert "main" in mode_ids

    def test_no_render_mode_warning(self, tmp_path):
        _write_scad(tmp_path, "plain.scad", "x = 5;\ncube(x);\n")
        result = generate_manifest(tmp_path)
        warnings = result["warnings"]
        assert any("render_mode" in w.lower() or "render_mode" in w for w in warnings)

    def test_string_parameter(self, tmp_path):
        _write_scad(tmp_path, "test.scad", 'letter = "A";\nrender_mode = 0;\n')
        result = generate_manifest(tmp_path)
        param = next(p for p in result["manifest"]["parameters"] if p["id"] == "letter")
        assert param["type"] == "text"
        assert param["default"] == "A"
