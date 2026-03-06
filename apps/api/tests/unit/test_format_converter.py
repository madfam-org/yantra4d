"""Unit tests for mesh format converter."""
from unittest.mock import patch, MagicMock

from services.engine.format_converter import stl_to_glb, convert_mesh, TRIMESH_EXPORT_FORMATS


class TestStlToGlb:
    """Tests for backward-compatible stl_to_glb wrapper."""

    @patch("services.engine.format_converter.trimesh")
    def test_stl_to_glb_success(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        result = stl_to_glb("/tmp/input.stl", "/tmp/output.glb")

        assert result is True
        mock_trimesh.load.assert_called_once_with("/tmp/input.stl", file_type="stl")
        mock_mesh.export.assert_called_once_with("/tmp/output.glb", file_type="glb")

    @patch("services.engine.format_converter.trimesh")
    def test_stl_to_glb_failure_returns_false(self, mock_trimesh):
        mock_trimesh.load.side_effect = Exception("File not found")

        result = stl_to_glb("/tmp/missing.stl", "/tmp/output.glb")

        assert result is False


class TestConvertMesh:
    """Tests for the generalized convert_mesh function."""

    @patch("services.engine.format_converter.trimesh")
    def test_stl_to_obj_success(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        result = convert_mesh("/tmp/model.stl", "/tmp/model.obj")

        assert result is True
        mock_trimesh.load.assert_called_once_with("/tmp/model.stl", file_type="stl")
        mock_mesh.export.assert_called_once_with("/tmp/model.obj", file_type="obj")

    @patch("services.engine.format_converter.trimesh")
    def test_stl_to_3mf_success(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        result = convert_mesh("/tmp/model.stl", "/tmp/model.3mf")

        assert result is True
        mock_trimesh.load.assert_called_once_with("/tmp/model.stl", file_type="stl")
        mock_mesh.export.assert_called_once_with("/tmp/model.3mf", file_type="3mf")

    @patch("services.engine.format_converter.trimesh")
    def test_glb_to_stl_reverse_conversion(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        result = convert_mesh("/tmp/model.glb", "/tmp/model.stl")

        assert result is True
        mock_trimesh.load.assert_called_once_with("/tmp/model.glb", file_type="glb")
        mock_mesh.export.assert_called_once_with("/tmp/model.stl", file_type="stl")

    def test_unsupported_output_format_returns_false(self):
        result = convert_mesh("/tmp/model.stl", "/tmp/model.step")

        assert result is False

    @patch("services.engine.format_converter.trimesh")
    def test_explicit_type_overrides(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_trimesh.load.return_value = mock_mesh

        result = convert_mesh("/tmp/model.bin", "/tmp/output.bin",
                              input_type="stl", output_type="obj")

        assert result is True
        mock_trimesh.load.assert_called_once_with("/tmp/model.bin", file_type="stl")
        mock_mesh.export.assert_called_once_with("/tmp/output.bin", file_type="obj")

    @patch("services.engine.format_converter.trimesh")
    def test_load_failure_returns_false(self, mock_trimesh):
        mock_trimesh.load.side_effect = Exception("corrupt file")

        result = convert_mesh("/tmp/bad.stl", "/tmp/out.obj")

        assert result is False

    @patch("services.engine.format_converter.trimesh")
    def test_export_failure_returns_false(self, mock_trimesh):
        mock_mesh = MagicMock()
        mock_mesh.export.side_effect = Exception("export error")
        mock_trimesh.load.return_value = mock_mesh

        result = convert_mesh("/tmp/model.stl", "/tmp/out.obj")

        assert result is False


class TestTrimeshExportFormats:
    """Tests for the TRIMESH_EXPORT_FORMATS constant."""

    def test_contains_common_mesh_formats(self):
        for fmt in ('stl', 'glb', 'gltf', '3mf', 'off', 'obj', 'ply'):
            assert fmt in TRIMESH_EXPORT_FORMATS

    def test_step_not_in_trimesh_formats(self):
        assert 'step' not in TRIMESH_EXPORT_FORMATS
