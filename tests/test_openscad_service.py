"""Unit tests for openscad service pure functions."""
import pytest
from types import SimpleNamespace
from unittest.mock import patch


# ---------------------------------------------------------------------------
# get_phase_from_line
# ---------------------------------------------------------------------------
class TestGetPhaseFromLine:
    """Tests for phase detection from OpenSCAD output lines."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from services.openscad import get_phase_from_line
        self.get_phase = get_phase_from_line

    @pytest.mark.parametrize(
        "line, expected",
        [
            ("Compiling design", "compiling"),
            ("Parsing design", "compiling"),
            ("Geometries in cache", "geometry"),
            ("CGAL operations", "cgal"),
            ("Rendering polygon mesh", "rendering"),
            ("Total rendering time", "rendering"),
            ("Simple: 1234", "done"),
            ("Vertices: 500", "done"),
            ("random line", None),
            ("", None),
        ],
    )
    def test_phase_detection(self, line, expected):
        assert self.get_phase(line) == expected


# ---------------------------------------------------------------------------
# validate_params
# ---------------------------------------------------------------------------
class TestValidateParams:
    """Tests for parameter validation against a mock manifest."""

    @pytest.fixture(autouse=True)
    def _mock_manifest(self):
        mock_manifest = SimpleNamespace(
            parameters=[
                {"id": "size", "type": "slider", "min": 10, "max": 50},
                {"id": "label", "type": "text", "maxlength": 20},
                {"id": "show_base", "type": "checkbox"},
            ]
        )
        with patch("services.openscad.get_manifest", return_value=mock_manifest):
            from services.openscad import validate_params
            self.validate = validate_params
            yield

    def test_slider_clamps_below_min(self):
        result = self.validate({"size": 5})
        assert result["size"] == 10.0

    def test_slider_clamps_above_max(self):
        result = self.validate({"size": 999})
        assert result["size"] == 50.0

    def test_slider_accepts_valid(self):
        result = self.validate({"size": 25})
        assert result["size"] == 25.0

    def test_text_rejects_unsafe(self):
        result = self.validate({"label": "<script>alert(1)</script>"})
        assert "label" not in result

    def test_text_accepts_safe(self):
        result = self.validate({"label": "Hello World"})
        assert result["label"] == "Hello World"

    def test_checkbox_coerces_true_string(self):
        result = self.validate({"show_base": "true"})
        assert result["show_base"] is True

    def test_checkbox_coerces_false_string(self):
        result = self.validate({"show_base": "false"})
        assert result["show_base"] is False

    def test_checkbox_accepts_bool(self):
        result = self.validate({"show_base": True})
        assert result["show_base"] is True

    def test_unknown_key_rejected(self):
        result = self.validate({"nonexistent": 42})
        assert "nonexistent" not in result

    def test_pass_through_keys_ignored(self):
        result = self.validate({"mode": "full", "scad_file": "main.scad", "size": 20})
        assert "mode" not in result
        assert "scad_file" not in result
        assert result["size"] == 20.0


# ---------------------------------------------------------------------------
# build_openscad_command
# ---------------------------------------------------------------------------
class TestBuildOpenscadCommand:
    """Tests for OpenSCAD CLI command construction."""

    @pytest.fixture(autouse=True)
    def _patch_config(self, monkeypatch):
        monkeypatch.setattr("config.Config.OPENSCAD_PATH", "openscad")
        from services.openscad import build_openscad_command
        self.build_cmd = build_openscad_command

    def test_bool_param(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {"flag": True})
        assert "-D" in cmd
        assert "flag=true" in cmd

    def test_int_param(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {"count": 42})
        assert "count=42" in cmd

    def test_float_param(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {"ratio": 3.14})
        assert "ratio=3.14" in cmd

    def test_string_param(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {"name": "hello"})
        assert 'name="hello"' in cmd

    def test_mode_id_zero_no_render_mode(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {}, mode_id=0)
        assert "render_mode=0" not in " ".join(cmd)

    def test_mode_id_nonzero_adds_render_mode(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {}, mode_id=2)
        assert "render_mode=2" in cmd

    def test_scad_file_key_excluded(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {"scad_file": "main.scad", "size": 10})
        d_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-D"]
        for arg in d_args:
            assert not arg.startswith("scad_file=")

    def test_output_and_source_in_cmd(self):
        cmd = self.build_cmd("/out.stl", "/in.scad", {})
        assert cmd[0] == "openscad"
        assert cmd[1] == "-o"
        assert cmd[2] == "/out.stl"
        assert cmd[-1] == "/in.scad"
